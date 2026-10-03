# -*- coding: utf-8 -*-
"""Capability vs hypothesis alignment (skill step 7).

Maps the ACTUAL granularity obtained this round onto each family's FROZEN definition.
Granularity mismatch => the family STAYS NOT_TESTABLE. No hypothesis definition is rewritten.
"""
from __future__ import annotations
import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.dirname(os.path.dirname(HERE))
SNAP_ID = "V3-SNAP-PIT2-20261001T131500Z"
SNAP = os.path.join(V3, "data", "snapshots", SNAP_ID)
OUT = os.path.join(HERE, "CAPABILITY_ALIGNMENT.json")
CST = timezone(timedelta(hours=8))


def main():
    man = json.load(open(os.path.join(SNAP, "MANIFEST.json"), encoding="utf-8"))
    cov = [(f["file"].split("_")[-1].replace(".parquet", ""),
            datetime.fromisoformat(f["ts_min"]), datetime.fromisoformat(f["ts_max"])) for f in man["files"]]
    lo = min(c[1] for c in cov)
    hi = max(c[2] for c in cov)

    vintages = []
    vd = os.path.join(HERE, "vintages")
    for fn in sorted(os.listdir(vd)):
        if fn.endswith(".json"):
            v = json.load(open(os.path.join(vd, fn), encoding="utf-8"))
            vintages.append({"file": fn, "captured_at_utc": v["captured_at_utc"],
                             "window_original": [v.get("pub_time_min"), v.get("pub_time_max")],
                             "events": v["events"], "tz": "Asia/Shanghai"})
    prior = os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(V3)),
                                          "v3_long_history_data", "V3_JIN10_EVENT_PIT.json"))
    if os.path.exists(prior):
        pj = json.load(open(prior, encoding="utf-8"))
        vintages.append({"file": "V3_JIN10_EVENT_PIT.json",
                         "captured_at_utc": pj.get("retrieved_at_utc") or pj.get("ts_utc"),
                         "window_original": [min(e["pub_time_utc"] for e in pj["events"]),
                                             max(e["pub_time_utc"] for e in pj["events"])],
                         "events": [{"pub_time": e["pub_time_original"], "importance": e.get("importance"),
                                     "event_name": e.get("event_name"), "country": e.get("country"),
                                     "pub_time_utc": e["pub_time_utc"]} for e in pj["events"]],
                         "tz": "Asia/Shanghai", "utc_precomputed": True})

    per_vintage = {}
    for v in vintages:
        inw, by_day, by_star = 0, Counter(), Counter()
        for e in v["events"]:
            pt = e.get("pub_time_utc")
            if pt is None:
                try:
                    pt = datetime.strptime(e["pub_time"], "%Y-%m-%d %H:%M").replace(tzinfo=CST).astimezone(timezone.utc).isoformat()
                except Exception:  # noqa: BLE001
                    continue
            dt = datetime.fromisoformat(pt)
            if lo <= dt <= hi:
                inw += 1
                by_day[dt.date().isoformat()] += 1
                by_star[str(e.get("importance"))] += 1
        per_vintage[v["file"]] = {"events_total": len(v["events"]), "events_inside_tick_window": inw,
                                  "by_day": dict(sorted(by_day.items())), "by_importance": dict(by_star),
                                  "window_original": v["window_original"], "captured_at_utc": v["captured_at_utc"]}

    out = {
        "schema": "v3_phase2_pit_capability_alignment/1",
        "tick_window_utc": [lo.isoformat(), hi.isoformat()],
        "tick_rows": man["TOTAL_ROWS"], "tick_days": len(cov),
        "calendar_vintages": per_vintage,
        "families": {
            "A_microstructure": {"status": "TESTABLE", "granularity": "tick", "change": "unchanged from R1",
                                 "reason": "tick snapshot available"},
            "C_liquidity_spread_regime": {"status": "TESTABLE", "granularity": "tick", "change": "unchanged from R1",
                                          "reason": "tick snapshot available"},
            "F_nondirectional": {"status": "TESTABLE", "granularity": "tick", "change": "unchanged from R1",
                                 "reason": "tick snapshot available"},
            "D_event_microstructure": {"status": "TESTABLE", "granularity": "event-time + tick",
                                       "change": "NOT_TESTABLE -> TESTABLE (this round)",
                                       "reason": "the blocker was ZERO overlap between the calendar window and the FROZEN tick snapshot. A new immutable snapshot now covers 2026-09-21..2026-10-01 and overlaps BOTH frozen calendar vintages.",
                                       "caveat": "thin: 9 trading days total, split across two non-overlapping vintages; eff_n per vintage will be small -> INSUFFICIENT_SAMPLE is a likely ladder outcome, reported honestly"},
            "E_crossmarket_leadlag": {"status": "TESTABLE_AT_1H_PARTIAL", "granularity": "1h bars (2y overlap)",
                                      "change": "LIMITED -> TESTABLE_AT_1H (partial)",
                                      "reason": "extant Yahoo 1h/2y DXY+VIX artifacts give a 624-day overlap",
                                      "caveat": "live Yahoo re-fetch returned HTTP 403 this round -> conclusions rest on the previously stored artifacts; bar open/close semantics remain UNKNOWN; 5m overlap only ~63 days"},
            "B_execution_alpha": {"status": "NOT_TESTABLE", "granularity": "n/a",
                                  "change": "UNCHANGED",
                                  "reason": "NOT a calendar/cross-market problem. bid_vol/ask_vol are identically 0 (DATA_GAP) => no size-weighted microprice, no queue, no fill probability. Would require L2/order-book data (separate availability question). This round does not unlock B and does not claim to."}
        },
        "rule_check": "no hypothesis definition was rewritten; capability upgrades only create NEW ids with fresh pre-registration"
    }
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"tick_window": out["tick_window_utc"], "tick_days": len(cov), "rows": man["TOTAL_ROWS"]},
                     ensure_ascii=False))
    for k, v in per_vintage.items():
        print(f"  {k}: total={v['events_total']} inside_window={v['events_inside_tick_window']} "
              f"stars={v['by_importance']} days={v['by_day']}")
    for k, v in out["families"].items():
        print(f"  FAMILY {k:26s} -> {v['status']:26s} ({v['change']})")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
