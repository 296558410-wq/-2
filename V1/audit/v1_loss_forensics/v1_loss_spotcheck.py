# -*- coding: utf-8 -*-
"""Spot-check pass: (1) MT5 raw M1 bars frame, (2) full win/loss tables for the report."""
import json, os
from datetime import datetime, timezone

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
print("now_utc:", datetime.now(timezone.utc).isoformat())

m1 = pd.read_parquet(os.path.join(HERE, "m1_bars_snapshot.parquet"))
print("m1 raw first:", m1.index[0], "| last:", m1.index[-1])
print("(raw 'time' from copy_rates_range; compare last vs now_utc to determine frame)")

R = [json.loads(l) for l in open(os.path.join(HERE, "TRADE_ERROR_DATABASE.jsonl"), encoding="utf-8") if l.strip()]
print()
print("== WINNERS (12) ==")
for r in [x for x in R if x["outcome"] == "WIN"]:
    o = r["decision"]["order_intent"] or {}
    print(f"  {r['trade_id']} {r['entry']['side']:<5} {r['entry']['ts_utc'][:19]} -> {r['exit']['ts_utc'][:19]} "
          f"dur={r['path']['duration_min']:>6}m R={r['R']} mfe={r['path']['mfe_r']} mae={r['path']['mae_r']} "
          f"net={r['net']} {r['session']} cause={r['primary_root_cause']}")
print()
print("== LOSSES (20) ==")
for r in [x for x in R if x["outcome"] == "LOSS"]:
    print(f"  {r['trade_id']} {r['entry']['side']:<5} {r['entry']['ts_utc'][:19]} -> {r['exit']['ts_utc'][:19]} "
          f"dur={r['path']['duration_min']:>6}m R={r['R']} mfe={r['path']['mfe_r']} mae={r['path']['mae_r']} "
          f"net={r['net']} {r['session']} blk={r['guard_cf']['block_price']} cause={r['primary_root_cause']}")

print()
for tid in ("V1T-2378322488", "V1T-2377943078"):
    r = next(x for x in R if x["trade_id"] == tid)
    s = r["structure"]
    print(f"== structure {tid} ==")
    for tf in ("15m", "60m"):
        f = s.get(tf) or {}
        print(f"  {tf}: dir_vs_ma20={f.get('dir_vs_ma20')} trend_strength_atr={f.get('trend_strength_atr')} "
              f"ret4_bps={f.get('ret4_bps')} vol14_bps={f.get('vol14_bps')} atr14={f.get('atr14')}")
