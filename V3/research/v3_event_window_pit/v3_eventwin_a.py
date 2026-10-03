# -*- coding: utf-8 -*-
"""V3 back on track — step A: Jin10 calendar timezone calibration + FXTM tick overlap check.

Determines (a) the timezone of Jin10's calendar pub_time via known US release times,
(b) which days of Sep 21-26 have FXTM 1m tick coverage, (c) the feasible event-window set.
"""
from __future__ import annotations

import glob
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\surface\.openclaw\workspace\v1_reset_001")
from v3_jin10_mcp import MCPClient, sc  # noqa: E402

AIQ = r"C:\AIQuant"
LIVE = os.path.join(AIQ, "data", "live_fxtm")
STAGE = os.path.join(AIQ, "data", "staging_fxtm")
OUT = r"C:\Users\surface\.openclaw\workspace\v1_reset_001"


def main():
    cli = MCPClient(); cli.initialize(); cli.initialized()
    r = cli.tools_call("list_calendar", {})
    p = sc({"result": r.get("result")}) or {}
    d = p.get("data")
    arr = d if isinstance(d, list) else (d or {}).get("items") or []
    evs = []
    for x in arr:
        evs.append({"title": x.get("title"), "pub_time": x.get("pub_time"), "star": x.get("star"),
                     "actual": x.get("actual"), "consensus": x.get("consensus"),
                     "previous": x.get("previous"), "revised": x.get("revised")})
    rep = {"ts_utc": datetime.now(timezone.utc).isoformat(), "calendar_events": len(evs)}

    # --- timezone calibration: find US high-star events and reason about the offset ---
    us = [e for e in evs if e["title"] and e["title"].startswith("美国") and (e["star"] or 0) >= 2]
    rep["us_high_star_sample"] = us[:12]
    # NFP / CPI are 08:30 ET (= 12:30 UTC in DST). Jobless claims 08:30 ET Thu.
    KEY = ["非农", "失业率", "CPI", "核心", "初请", "零售", "GDP", "PCE", "PMI"]
    keyed = [e for e in us if any(k in (e["title"] or "") for k in KEY)]
    rep["us_key_events"] = keyed[:12]
    rep["timezone_inference"] = {
        "rule": "US 08:30 ET releases = 12:30 UTC = 20:30 Beijing (DST). Compare observed pub_time hours.",
        "observed_hours": sorted({(e["pub_time"] or "")[11:16] for e in keyed if e.get("pub_time")})[:12],
    }

    # --- FXTM tick coverage for the calendar window ---
    files = sorted(glob.glob(os.path.join(LIVE, "*.parquet"))) + sorted(glob.glob(os.path.join(STAGE, "*.parquet")))
    cov = {}
    for f in files:
        b = os.path.basename(f)
        if not b.startswith("ticks_"):
            continue
        day = b.replace("ticks_", "").replace(".parquet", "")
        cov[day] = os.path.getsize(f)
    rep["fxtm_tick_days"] = cov
    cal_days = sorted({(e["pub_time"] or "")[:10] for e in evs if e.get("pub_time")})
    rep["calendar_days"] = cal_days
    rep["calendar_day_event_counts"] = {d: sum(1 for e in evs if (e.get("pub_time") or "").startswith(d))
                                          for d in cal_days}
    rep["overlap_days_with_ticks"] = [d for d in cal_days if d.replace("-", "") in cov]

    json.dump(rep, open(os.path.join(OUT, "v3_eventwin_stepA.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    print(json.dumps({"calendar_events": len(evs), "us_high_star": len(us),
                       "us_key_events": [(e["title"][:22], e["pub_time"]) for e in keyed[:8]],
                       "observed_hours": rep["timezone_inference"]["observed_hours"],
                       "calendar_days": cal_days, "day_counts": rep["calendar_day_event_counts"],
                       "fxtm_tick_days": sorted(cov)[-12:],
                       "overlap_days_with_ticks": rep["overlap_days_with_ticks"]},
                      indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
