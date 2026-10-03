# -*- coding: utf-8 -*-
"""V3 step B: event-window measurement — Jin10 calendar events vs FXTM 1m XAUUSD.

DESCRIPTIVE measurement only (feasibility + baselines). No trade claim, no candidate, no hypothesis.
pub_time is Beijing (UTC+8) — verified in step A; converted to UTC here.
"""
from __future__ import annotations

import glob
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\surface\.openclaw\workspace\v1_reset_001")
from v3_jin10_mcp import MCPClient, sc  # noqa: E402

AIQ = r"C:\AIQuant"
LIVE = os.path.join(AIQ, "data", "live_fxtm")
OUT = r"C:\Users\surface\.openclaw\workspace\v1_reset_001"
DAYS = ["20260921", "20260922", "20260923", "20260924", "20260925"]


def load_bars():
    frames = []
    for d in DAYS:
        p = os.path.join(LIVE, f"ticks_{d}.parquet")
        if os.path.exists(p):
            try:
                frames.append(pd.read_parquet(p, columns=["ts_utc", "bid", "ask"]))
            except Exception:  # noqa: BLE001
                try:
                    frames.append(pd.read_parquet(p))
                except Exception:  # noqa: BLE001
                    pass
    if not frames:
        return pd.DataFrame()
    t = pd.concat(frames, ignore_index=True)
    # ts may be epoch (live_fxtm uses 'time'/time_msc) or timestamp
    col = "ts_utc" if "ts_utc" in t.columns else ("time" if "time" in t.columns else None)
    if col is None:
        return pd.DataFrame()
    v = t[col]
    if pd.api.types.is_numeric_dtype(v):
        t["dt"] = pd.to_datetime(v, unit="s", utc=True)
    else:
        t["dt"] = pd.to_datetime(v, utc=True, errors="coerce")
    t = t.dropna(subset=["dt"])
    t["mid"] = (t["bid"] + t["ask"]) / 2.0
    g = t.set_index("dt").resample("1min").agg(mid=("mid", "last"), n=("mid", "size"))
    return g.dropna()


def main():
    cli = MCPClient(); cli.initialize(); cli.initialized()
    r = cli.tools_call("list_calendar", {})
    p = sc({"result": r.get("result")}) or {}
    d = p.get("data")
    arr = d if isinstance(d, list) else (d or {}).get("items") or []

    bars = load_bars()
    rep = {"ts_utc": datetime.now(timezone.utc).isoformat(),
            "bars": {"rows": int(len(bars)),
                      "from": bars.index.min().isoformat() if len(bars) else None,
                      "to": bars.index.max().isoformat() if len(bars) else None},
            "timezone_rule": "pub_time is Asia/Shanghai (UTC+8) -> UTC = pub_time - 8h",
            "window_defs_minutes": [-5, 0, 1, 5, 15, 30]}

    def bar_at(ts, mode="before"):
        if not len(bars):
            return None
        if mode == "before":
            s = bars.loc[:ts]
            return float(s["mid"].iloc[-1]) if len(s) else None
        s = bars.loc[ts:]
        return float(s["mid"].iloc[0]) if len(s) else None

    rows = []
    for e in arr:
        pt = e.get("pub_time")
        if not pt:
            continue
        try:
            t_utc = datetime.strptime(str(pt), "%Y-%m-%d %H:%M").replace(tzinfo=timezone(timedelta(hours=8))).astimezone(timezone.utc)
        except Exception:  # noqa: BLE001
            continue
        if t_utc.date().isoformat() not in {"2026-09-21", "2026-09-22", "2026-09-23", "2026-09-24", "2026-09-25"}:
            continue
        base = bar_at(t_utc, "before")
        if base is None:
            continue
        rec = {"title": (e.get("title") or "")[:40], "pub_time_bj": pt, "t_utc": t_utc.isoformat(),
                "star": e.get("star"), "actual": e.get("actual"), "consensus": e.get("consensus"),
                "previous": e.get("previous"), "revised": e.get("revised")}
        ok = True
        for m in (-5, 0, 1, 5, 15, 30):
            v = bar_at(t_utc + timedelta(minutes=m), "before" if m <= 0 else "after")
            if v is None:
                ok = False
                break
            rec[f"bp_{m}"] = round((v - base) / base * 1e4, 3)
        rec["usable"] = ok
        # surprise flags
        try:
            a = float(e.get("actual")); c = float(e.get("consensus"))
            rec["surprise"] = round(a - c, 4)
            rec["surprise_sign"] = 1 if a > c else (-1 if a < c else 0)
        except Exception:  # noqa: BLE001
            rec["surprise"] = None
            rec["surprise_sign"] = None
        rows.append(rec)

    rep["events_in_window"] = len(rows)
    rep["usable_events"] = sum(1 for x in rows if x["usable"])
    us = [x for x in rows if x["usable"]]
    def agg(sel, key):
        v = [x.get(key) for x in sel if x.get(key) is not None]
        if not v:
            return None
        a = np.array(v, float)
        return {"n": len(a), "mean_bp": round(float(a.mean()), 3), "median_bp": round(float(np.median(a)), 3),
                 "p25": round(float(np.percentile(a, 25)), 3), "p75": round(float(np.percentile(a, 75)), 3),
                 "abs_mean_bp": round(float(np.abs(a).mean()), 3),
                 "hit_up": round(float((a > 0).mean()), 3)}
    tiers = {}
    for s in (1, 2, 3):
        sel = [x for x in us if x.get("star") == s]
        tiers[f"star{s}"] = {"n": len(sel),
                               "d0_1m": agg(sel, "bp_1"), "d0_5m": agg(sel, "bp_5"),
                               "d0_15m": agg(sel, "bp_15"), "d0_30m": agg(sel, "bp_30"),
                               "pre_5m": agg(sel, "bp_-5")}
    rep["by_star"] = tiers
    rep["by_surprise_sign"] = {
        "positive": {"n": len([x for x in us if x.get("surprise_sign") == 1]),
                       "d0_5m": agg([x for x in us if x.get("surprise_sign") == 1], "bp_5")},
        "negative": {"n": len([x for x in us if x.get("surprise_sign") == -1]),
                       "d0_5m": agg([x for x in us if x.get("surprise_sign") == -1], "bp_5")},
    }
    rep["all_events"] = {"d0_1m": agg(us, "bp_1"), "d0_5m": agg(us, "bp_5"), "d0_15m": agg(us, "bp_15"),
                           "d0_30m": agg(us, "bp_30")}
    rep["discipline_note"] = ("DESCRIPTIVE ONLY. No hypothesis was pre-registered, so these numbers must NOT be "
                               "read as an edge. Any tradable claim requires a NEW frozen hypothesis id + the full "
                               "cost/OOS/FDR protocol.")
    rep["events"] = rows
    json.dump(rep, open(os.path.join(OUT, "v3_eventwin_stepB.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    print(json.dumps({"bars": rep["bars"], "events_in_window": rep["events_in_window"],
                       "usable": rep["usable_events"], "by_star": tiers,
                       "by_surprise": rep["by_surprise_sign"], "all": rep["all_events"]},
                      indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
