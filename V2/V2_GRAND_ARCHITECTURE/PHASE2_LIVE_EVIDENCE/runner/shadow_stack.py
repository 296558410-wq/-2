"""Per-cycle Live Shadow Evidence Stream runner.

Reads the SAME PIT inputs as production (local FXTM tick archive, the router's
local fallback source) and runs the Phase-1 stack in SHADOW only:

    Strategy Factory -> Strategy Registry -> Strategy Brain -> Competition -> Evolution

Writes ONLY to PHASE2_LIVE_EVIDENCE/. Idempotent per (cycle_id, strategy_id):
re-running never rewrites history, it skips cycles already present.

PIT discipline: a 15m bar LABELLED t (pandas resample left-label) aggregates
[t, t+15m); it is only complete at t+15m. Therefore the shadow decision_ts is
bar_label + 15m and its own close is the last price strictly before decision_ts.
Outcomes are computed from raw ticks in (decision_ts, decision_ts + H], so
decision_ts < future_data_ts always holds.

CLI:
    python runner/shadow_stack.py --mode seed     # replay verifiable history
    python runner/shadow_stack.py --mode live     # one cycle at current time
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths as PP  # noqa: E402

from common import data as D, eval as E, cost as C, hashing  # noqa: E402
from strategy_factory import factory as F  # noqa: E402
from strategy_brain import brain as BRAIN  # noqa: E402

SHADOW_STATE = "SHADOW"
BAR_MIN = 15


# --------------------------------------------------------------------------
# cached dataset
# --------------------------------------------------------------------------
_CACHE = {}


def dataset():
    if "df15" in _CACHE:
        return _CACHE["df15"], _CACHE["man"], _CACHE["ticks"]
    df15, man = D.load_research_dataset("15min")
    # decision timestamp = left label + 15m (bar completion)
    lab = pd.to_datetime(df15["bar_end_utc"], utc=True)
    df15 = df15.copy()
    df15["decision_ts"] = lab + pd.Timedelta(minutes=BAR_MIN)
    ticks = D.load_ticks()[["ts_utc", "mid", "bid", "ask", "spread"]]
    _CACHE.update(df15=df15, man=man, ticks=ticks)
    return df15, man, ticks


# --------------------------------------------------------------------------
# per-spec PIT-safe calibration (past outcomes only)
# --------------------------------------------------------------------------
def spec_arrays(df15, specs, cost):
    mid = df15["close"].to_numpy(dtype=np.float64)
    n = len(df15)
    out = {}
    for s in specs:
        sig = F.run_mechanism(df15, s)
        idx = E.entry_indices(sig)
        nets = []
        keep = []
        for j in idx:
            if j + PP.CALIB_BARS >= n:
                continue
            sg = np.sign(sig[j])
            g = sg * (mid[j + PP.CALIB_BARS] - mid[j])
            nets.append(g - cost)
            keep.append(j)
        out[s.strategy_id] = {
            "sig": sig,
            "ent_idx": np.asarray(keep, dtype=np.int64),
            "calib_net": np.asarray(nets, dtype=np.float64),
        }
    return out


def calib_at(arr, i, calib_bars):
    """PIT-safe confidence/stability using only entries whose outcome bar
    (j + calib_bars) is strictly before cycle i."""
    ent = arr["ent_idx"]
    net = arr["calib_net"]
    hi = int(np.searchsorted(ent, i - calib_bars))  # entries with j < i-calib
    lo = max(0, hi - PP.CALIB_WINDOW)
    w = net[lo:hi]
    w = w[np.isfinite(w)]
    if w.size < 5:
        return 0.5, 0.5, 0
    prec = float((w > 0).mean())
    conf = float(min(0.95, max(0.30, prec)))
    blocks = np.array_split(w, 4)
    means = np.array([b.mean() for b in blocks])
    overall = w.mean()
    stab = float((np.sign(means) == np.sign(overall)).mean()) if overall != 0 else 0.5
    return conf, stab, int(w.size)


# --------------------------------------------------------------------------
# per-cycle shadow stack
# --------------------------------------------------------------------------
def run_cycle(df15, i, specs, arrs, cost, prod_map, mode):
    r = df15.iloc[i]
    ts = pd.Timestamp(r["decision_ts"])
    cycle_id = "SHC-" + ts.strftime("%Y%m%dT%H%M%S") + "Z"
    regime = str(r["regime"])
    # PIT input window hash (bars <= i only)
    lo = max(0, i - 199)
    win = df15.iloc[lo:i + 1][["bar_end_utc", "close", "high", "low", "spread", "regime"]].copy()
    win["bar_end_utc"] = pd.to_datetime(win["bar_end_utc"], utc=True).astype(str)
    win_recs = json.loads(win.to_json(orient="records"))
    input_hash = hashing.sha256_json(
        {"dataset_hash": _CACHE["man"]["dataset_hash"], "rows": win_recs}
    )
    data_ok = bool(np.isfinite(r.get("ma60", np.nan)) and np.isfinite(r.get("atr14", np.nan)))
    data_quality = "OK" if data_ok else "DATA_GAP"

    # votes
    votes = []
    per = {}
    for s in specs:
        a = arrs[s.strategy_id]
        sigv = float(a["sig"][i])
        conf, stab, nwin = calib_at(a, i, PP.CALIB_BARS)
        fit = 1.0 if regime in s.applicable_regime else 0.35
        per[s.strategy_id] = {"signal": int(np.sign(sigv)), "confidence": round(conf, 4),
                              "regime_fit": fit, "recent_stability": round(stab, 4),
                              "calib_n": nwin}
        if sigv != 0:
            votes.append(BRAIN.vote_from_signal(s.strategy_id, s.mechanism, sigv, conf, regime,
                                                s.applicable_regime, stab))
    bd = BRAIN.decide(votes, data_ok=data_ok, risk_allows=True, min_votes=2, min_confidence=0.55)
    final = bd.final_decision

    output_hash = hashing.sha256_json(
        {"cycle_id": cycle_id, "final": final, "conflict": bd.conflict_state,
         "direction": int(bd.direction), "signals": {k: v["signal"] for k, v in per.items()}}
    )

    # production reference for this window
    wkey = ts.strftime("%Y-%m-%dT%H:%MZ")
    pr = prod_map.get(wkey)
    if pr is None:
        prod_decision = "MARKET_CLOSED" if mode == "live" else "PRE_RUN_OR_NO_DECISION"
        prod_status, prod_side = None, None
    else:
        prod_status = pr.get("status")
        prod_side = pr.get("side")
        prod_decision = f"{pr.get('status')}" + (f":{pr.get('side')}" if pr.get("side") else "")

    rows = []
    emit_any = False
    for s in specs:
        p = per[s.strategy_id]
        if p["signal"] == 0:
            continue
        emit_any = True
        if p["signal"] == int(bd.direction) and bd.direction != 0:
            ev = [x for x in bd.evidence if x.startswith(s.strategy_id)]
            if not ev:
                ev = [f"agrees with final {final}"]
            ce = []
        elif bd.direction != 0 and p["signal"] == -int(bd.direction):
            ev = [f"standalone signal {p['signal']}"]
            ce = [f"opposes final {final}"]
        else:
            ev = [f"standalone signal {p['signal']}"]
            ce = []
        rows.append(_row(cycle_id, ts, r, s, regime, p, final, bd, prod_decision, prod_side,
                         prod_status, wkey, input_hash, output_hash, data_quality, mode, ev, ce))
    if not emit_any:
        rows.append(_null_row(cycle_id, ts, r, regime, bd, prod_decision, prod_side, prod_status,
                              wkey, input_hash, output_hash, data_quality, mode))
    return rows


def _base(cycle_id, ts, r, regime, bd, prod_decision, prod_side, prod_status, wkey,
          input_hash, output_hash, data_quality, mode):
    return {
        "cycle_id": cycle_id,
        "decision_ts": ts.isoformat(),
        "data_asof": pd.Timestamp(r["bar_end_utc"]).isoformat(),
        "regime": regime,
        "final_shadow_decision": bd.final_decision,
        "shadow_direction": int(bd.direction),
        "shadow_confidence": float(bd.confidence),
        "conflict_state": bd.conflict_state,
        "n_votes": len(bd.strategy_candidates),
        "production_decision": prod_decision,
        "production_status": prod_status,
        "production_side": prod_side,
        "production_window": wkey,
        "input_hash": input_hash,
        "output_hash": output_hash,
        "data_quality": data_quality,
        "mode": mode,
        "cycle_kind": "SEED/REPLAY" if mode == "seed" else "LIVE",
        "atr14": float(r["atr14"]) if pd.notna(r.get("atr14", np.nan)) else None,
        "close_ref": float(r["close"]),
    }


def _row(cycle_id, ts, r, s, regime, p, final, bd, prod_decision, prod_side, prod_status, wkey,
         input_hash, output_hash, data_quality, mode, ev, ce):
    row = _base(cycle_id, ts, r, regime, bd, prod_decision, prod_side, prod_status, wkey,
                input_hash, output_hash, data_quality, mode)
    row.update({
        "strategy_id": s.strategy_id,
        "strategy_version": s.config_hash[:12],
        "mechanism": s.mechanism,
        "signal": p["signal"],
        "confidence": p["confidence"],
        "regime_fit": p["regime_fit"],
        "recent_stability": p["recent_stability"],
        "evidence": ev,
        "counter_evidence": ce,
        "strategy_state": SHADOW_STATE,
    })
    return row


def _null_row(cycle_id, ts, r, regime, bd, prod_decision, prod_side, prod_status, wkey,
              input_hash, output_hash, data_quality, mode):
    row = _base(cycle_id, ts, r, regime, bd, prod_decision, prod_side, prod_status, wkey,
                input_hash, output_hash, data_quality, mode)
    row.update({
        "strategy_id": "NONE",
        "strategy_version": None,
        "mechanism": None,
        "signal": 0,
        "confidence": None,
        "regime_fit": None,
        "recent_stability": None,
        "evidence": [],
        "counter_evidence": [],
        "strategy_state": SHADOW_STATE,
    })
    return row


# --------------------------------------------------------------------------
# drivers
# --------------------------------------------------------------------------
def run_seed(limit: int | None = None) -> int:
    PP.ensure_dirs()
    df15, man, _ = dataset()
    specs = F.generate_specs()
    cost = C.round_trip_cost_price(df15["spread"].to_numpy())
    arrs = spec_arrays(df15, specs, cost)
    active = PP.read_active_run()
    run_id = active.get("run_id")
    prod_map = PP.production_decisions(run_id) if run_id else {}
    existing = PP.jl_keys(PP.STREAM, lambda r: (r["cycle_id"], r["strategy_id"]))
    n_new = 0
    cycles = range(len(df15)) if not limit else range(max(0, len(df15) - limit), len(df15))
    for i in cycles:
        ts = pd.Timestamp(df15["decision_ts"].iloc[i])
        cid = "SHC-" + ts.strftime("%Y%m%dT%H%M%S") + "Z"
        if all((cid, s.strategy_id) in existing for s in specs):
            continue
        rows = run_cycle(df15, i, specs, arrs, cost, prod_map, "seed")
        rows = [r for r in rows if (r["cycle_id"], r["strategy_id"]) not in existing]
        n_new += PP.jl_append(PP.STREAM, rows)
    PP.log_event("seed", {"rows": n_new, "run_id": run_id, "dataset_hash": man["dataset_hash"]})
    return n_new


def run_live(force_open: bool = False) -> int:
    """One live cycle. When the market is closed this creates NO new sample:
    it returns 0 and the caller (build.py) records a light heartbeat instead.
    ``force_open`` is a weekend self-test hook for the MARKET_OPEN branch."""
    PP.ensure_dirs()
    health = PP.read_health()
    df15, man, _ = dataset()
    specs = F.generate_specs()
    cost = C.round_trip_cost_price(df15["spread"].to_numpy())
    arrs = spec_arrays(df15, specs, cost)
    active = PP.read_active_run()
    run_id = active.get("run_id")
    prod_map = PP.production_decisions(run_id) if run_id else {}
    existing = PP.jl_keys(PP.STREAM, lambda r: (r["cycle_id"], r["strategy_id"]))

    market_open = bool(health.get("market_open")) or force_open
    i = len(df15) - 1  # most recent completed bar in the archive
    ts = pd.Timestamp(df15["decision_ts"].iloc[i])
    cid = "SHC-" + ts.strftime("%Y%m%dT%H%M%S") + "Z"
    if not market_open:
        # C1: do not invent activity, do not grow the stream. A light heartbeat is
        # recorded by build.py/run_closed; this path only writes a log line.
        PP.log_event("live", {"result": "MARKET_CLOSED_HEARTBEAT_ONLY", "cycle_id": cid})
        return 0
    rows = run_cycle(df15, i, specs, arrs, cost, prod_map, "live")
    rows = [r for r in rows if (r["cycle_id"], r["strategy_id"]) not in existing]
    n = PP.jl_append(PP.STREAM, rows)
    PP.log_event("live", {"result": "CYCLE", "cycle_id": cid, "rows": n})
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["seed", "live"], default="seed")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    if args.mode == "seed":
        n = run_seed(limit=args.limit)
    else:
        n = run_live()
    print(f"[shadow_stack] mode={args.mode} appended_rows={n}")


if __name__ == "__main__":
    main()
