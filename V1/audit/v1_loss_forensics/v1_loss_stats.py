# -*- coding: utf-8 -*-
"""v1_loss_stats.py — final aggregates for the forensic report (read-only, prints to stdout)."""
import json, os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
R = [json.loads(l) for l in open(os.path.join(HERE, "TRADE_ERROR_DATABASE.jsonl"), encoding="utf-8") if l.strip()]
LOSS = [r for r in R if r["outcome"] == "LOSS"]; WIN = [r for r in R if r["outcome"] == "WIN"]

print("== counts ==")
print("total", len(R), "| wins", len(WIN), "| losses", len(LOSS))
print("by cause:", dict(Counter(r["primary_root_cause"] for r in LOSS)))
print("by side(loss):", dict(Counter(r["entry"]["side"] for r in LOSS)))
print("by session(loss):", dict(Counter(r["session"] for r in LOSS)))
print("by day(loss):", dict(Counter(r["entry"]["ts_utc"][:10] for r in LOSS)))
print()
print("== per cause detail ==")
for c in sorted({r["primary_root_cause"] for r in LOSS}):
    rows = [r for r in LOSS if r["primary_root_cause"] == c]
    print(f"-- {c} ({len(rows)})")
    for r in rows:
        print(f"   {r['trade_id']} {r['entry']['side']:<5} {r['entry']['ts_utc'][10:19]} R={r['R']} mfe={r['path']['mfe_r']} dur={r['path']['duration_min']}m {r['session']}")
print()
print("== loss aggregates ==")
import statistics as st
print("mfe>=0.5R among losses:", sum(1 for r in LOSS if (r["path"]["mfe_r"] or 0) >= 0.5), "/", len(LOSS))
print("mfe mean:", round(st.mean([r['path']['mfe_r'] for r in LOSS if r['path']['mfe_r'] is not None]), 3))
print("mae mean:", round(st.mean([r['path']['mae_r'] for r in LOSS if r['path']['mae_r'] is not None]), 3))
print("dur median (min):", st.median([r['path']['duration_min'] for r in LOSS]))
print("R list:", [r['R'] for r in LOSS])
print()
print("== blocked set detail ==")
blk = [r for r in R if r["guard_cf"]["block_price"] or r["guard_cf"]["block_net"]]
for r in blk:
    print(f"   {r['trade_id']} {r['outcome']} net={r['net']} cons_before={r['guard_cf']['state_price']['cons']} dayloss={r['guard_cf']['state_price']['daily']}")
print("blocked count:", len(blk), "| losses:", sum(1 for r in blk if r['outcome']=='LOSS'), "| wins:", sum(1 for r in blk if r['outcome']=='WIN'))
print()
print("== wins ==")
for r in WIN:
    print(f"   {r['trade_id']} {r['entry']['side']:<5} R={r['R']} mfe={r['path']['mfe_r']} dur={r['path']['duration_min']}m {r['session']} cause={r['primary_root_cause']}")
print()
print("== counterfactual summary (losses only) ==")
cf = [r["cf"] for r in LOSS]
t15 = [x.get("timing_15m") or {} for x in cf]; t30 = [x.get("timing_30m") or {} for x in cf]
op = [x.get("opposite") or {} for x in cf]
print("timing15 hit:", dict(Counter(x.get("hit") for x in t15)))
print("timing30 hit:", dict(Counter(x.get("hit") for x in t30)))
print("opposite hit:", dict(Counter(x.get("hit") for x in op)))
print("time_stop15:", [x.get("time_stop_15m") for x in cf])
print("time_stop60:", [x.get("time_stop_60m") for x in cf])
print("reversal30:", [x.get("reversal_after_exit_30m_r") for x in cf])
print("no_trade60:", [x.get("no_trade_move_60m_r") for x in cf])
print()
print("== totals ==")
wsum = sum(r["pnl_price"] for r in WIN); lsum = sum(r["pnl_price"] for r in LOSS)
print("win_sum:", round(wsum,2), "loss_sum:", round(lsum,2), "net_price:", round(wsum+lsum,2))
print("net incl costs:", round(sum(r["net"] for r in R), 2))
print("blocked counterfactual: avoided_loss", round(sum(r['pnl_price'] for r in blk if r['outcome']=='LOSS'),2),
      "foregone_win", round(sum(r['pnl_price'] for r in blk if r['outcome']=='WIN'),2))
