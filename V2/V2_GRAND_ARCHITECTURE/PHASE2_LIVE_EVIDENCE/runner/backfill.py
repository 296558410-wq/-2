"""Continuous Outcome backfill.

For every shadow (or production-reference) decision in the Live Evidence Stream,
compute 15m / 30m / 60m / 240m outcomes from the LOCAL raw tick archive:

  future_return, MFE, MAE, TP/SL first-touch, data_completeness, DATA_GAP

Strictness: futures are taken from ticks strictly AFTER decision_ts, so
decision_ts < future_data_ts always holds (no future leakage).

Re-runnable: idempotent per (cycle_id, strategy_id, horizon_min); new data only
appends. TP/SL are production levels for PRODUCTION rows and a documented
ATR-proxy (risk = 1.5*ATR14_15m, reward = 2R) for SHADOW rows.

CLI:  python runner/backfill.py
"""
from __future__ import annotations
import os
import sys
import json
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths as PP  # noqa: E402
from common import data as D, cost as C  # noqa: E402

_TICKS = {}


def ticks():
    if "ts" not in _TICKS:
        t = D.load_ticks()[["ts_utc", "mid"]].dropna()
        ts = (pd.to_datetime(t["ts_utc"], utc=True)
              .dt.tz_convert("UTC").dt.tz_localize(None))
        order = np.argsort(ts.to_numpy())
        _TICKS["ts"] = ts.to_numpy()[order]
        _TICKS["mid"] = t["mid"].to_numpy(dtype=np.float64)[order]
    return _TICKS["ts"], _TICKS["mid"]


def _first_touch(seg, entry, direction, sl, tp):
    """Return TP / SL / NONE based on the FIRST level crossed (tick order).
    Vectorized (argmax over crossing masks) so 240m windows stay fast."""
    seg = np.asarray(seg, dtype=np.float64)
    if seg.size == 0:
        return "NA"
    if sl is None and tp is None:
        return "NA"
    if direction > 0:
        sl_hit = (seg <= sl) if sl is not None else np.zeros(seg.size, bool)
        tp_hit = (seg >= tp) if tp is not None else np.zeros(seg.size, bool)
    else:
        sl_hit = (seg >= sl) if sl is not None else np.zeros(seg.size, bool)
        tp_hit = (seg <= tp) if tp is not None else np.zeros(seg.size, bool)
    big = 1 << 30
    i_sl = int(np.argmax(sl_hit)) if sl_hit.any() else big
    i_tp = int(np.argmax(tp_hit)) if tp_hit.any() else big
    if i_sl == big and i_tp == big:
        return "NONE"
    return "SL" if i_sl <= i_tp else "TP"


def outcome_for(entry_ts, direction, horizon_min, atr, prod=None):
    ts, mid = ticks()
    if direction == 0:
        return None
    et = np.datetime64(pd.Timestamp(entry_ts).tz_convert("UTC").tz_localize(None))
    fut = et + np.timedelta64(horizon_min, "m")
    arch_max = ts[-1]
    i_entry = int(np.searchsorted(ts, et, side="right")) - 1
    if i_entry < 0:
        return {"data_gap": True, "data_completeness": 0.0}
    entry_px = float(mid[i_entry])
    i0 = int(np.searchsorted(ts, et, side="right"))
    if fut > arch_max:
        i1 = ts.size
        covered = (arch_max - et) / np.timedelta64(1, "m")
        seg = mid[i0:i1]
        rec = _outcome_fields(entry_px, direction, entry_ts, fut, horizon_min, seg,
                              data_gap=True, completeness=round(min(1.0, covered / horizon_min), 3))
        return rec
    i1 = int(np.searchsorted(ts, fut, side="right"))
    seg = mid[i0:i1]
    if seg.size < 5:
        return {"data_gap": True, "data_completeness": 0.0, "entry_price": entry_px}
    rec = _outcome_fields(entry_px, direction, entry_ts, fut, horizon_min, seg,
                          data_gap=False, completeness=1.0)
    # TP/SL
    if prod and prod.get("stop_loss") and prod.get("take_profit"):
        sl, tp = float(prod["stop_loss"]), float(prod["take_profit"])
    else:
        risk = 1.5 * float(atr) if atr and np.isfinite(atr) else None
        if risk:
            sl = entry_px - direction * risk
            tp = entry_px + direction * 2.0 * risk
        else:
            sl = tp = None
    rec["tp"] = tp
    rec["sl"] = sl
    rec["tp_sl_first_touch"] = _first_touch(seg, entry_px, direction, sl, tp)
    return rec


def _outcome_fields(entry_px, direction, et, fut, h, seg, data_gap, completeness):
    seg = np.asarray(seg, dtype=np.float64)
    if seg.size:
        future_px = float(seg[-1])
        fut_ret = float(direction * (future_px - entry_px))
        if direction > 0:
            mfe = float(seg.max() - entry_px); mae = float(entry_px - seg.min())
        else:
            mfe = float(entry_px - seg.min()); mae = float(seg.max() - entry_px)
    else:
        future_px, fut_ret, mfe, mae = None, None, None, None
    return {
        "entry_price": entry_px, "future_price": future_px, "future_return": fut_ret,
        "mfe": mfe, "mae": mae, "data_gap": data_gap, "data_completeness": completeness,
    }


def run_backfill() -> int:
    PP.ensure_dirs()
    stream = PP.jl_read(PP.STREAM)
    if not stream:
        PP.log_event("backfill", {"result": "EMPTY_STREAM"})
        return 0
    # cycle summaries + production reference
    cycles: dict[str, dict] = {}
    for r in stream:
        cid = r["cycle_id"]
        c = cycles.setdefault(cid, {
            "decision_ts": r.get("decision_ts"),
            "regime": r.get("regime"),
            "atr14": r.get("atr14"),
            "production_window": r.get("production_window"),
            "production_status": r.get("production_status"),
            "production_side": r.get("production_side"),
            "mode": r.get("mode"),
        })
        if r.get("atr14") is not None:
            c["atr14"] = r["atr14"]
    active = PP.read_active_run()
    run_id = active.get("run_id")
    prod_map = PP.production_decisions(run_id) if run_id else {}

    existing = PP.jl_keys(PP.OUTCOMES, lambda r: (r["cycle_id"], r["strategy_id"], r["horizon_min"]))
    new_rows = []
    for r in stream:
        cid = r["cycle_id"]
        sid = r["strategy_id"]
        direction = int(r.get("signal") or 0)
        if sid == "NONE":
            continue
        # shadow rows
        for h in PP.HORIZONS_MIN:
            if (cid, sid, h) in existing:
                continue
            atr = cycles[cid].get("atr14")
            rec = outcome_for(cycles[cid]["decision_ts"], direction, h, atr, prod=None)
            if rec is None:
                continue
            new_rows.append(_row(cid, sid, h, cycles[cid]["decision_ts"], rec, r.get("mode"), "SHADOW"))
    # production reference rows for TRADE cycles (once per cycle)
    for cid, c in cycles.items():
        w = c.get("production_window")
        if not w or c.get("production_status") != "TRADE":
            continue
        p = prod_map.get(w)
        if not p:
            continue
        direction = 1 if p.get("side") == "BUY" else (-1 if p.get("side") == "SELL" else 0)
        if direction == 0:
            direction = 1 if (p.get("side") or "").upper() == "LONG" else (-1 if (p.get("side") or "").upper() == "SHORT" else 0)
        for h in PP.HORIZONS_MIN:
            if (cid, "PRODUCTION", h) in existing:
                continue
            if direction == 0:
                continue
            rec = outcome_for(c["decision_ts"], direction, h, None, prod=p)
            if rec is None:
                continue
            new_rows.append(_row(cid, "PRODUCTION", h, c["decision_ts"], rec, c.get("mode"), "PRODUCTION"))
    n = PP.jl_append(PP.OUTCOMES, new_rows)
    PP.log_event("backfill", {"rows": n})
    return n


def _row(cid, sid, h, decision_ts, rec, mode, source):
    et = pd.Timestamp(decision_ts)
    fut = (et + pd.Timedelta(minutes=h)).isoformat()
    return {
        "cycle_id": cid, "strategy_id": sid, "horizon_min": h,
        "decision_ts": et.isoformat(), "future_data_ts": fut,
        "future_return": rec.get("future_return"),
        "mfe": rec.get("mfe"), "mae": rec.get("mae"),
        "tp": rec.get("tp"), "sl": rec.get("sl"),
        "tp_sl_first_touch": rec.get("tp_sl_first_touch"),
        "entry_price": rec.get("entry_price"), "future_price": rec.get("future_price"),
        "data_completeness": rec.get("data_completeness"),
        "data_gap": bool(rec.get("data_gap")),
        "source": source, "mode": mode,
    }


def main():
    n = run_backfill()
    print(f"[backfill] appended_rows={n}")


if __name__ == "__main__":
    main()
