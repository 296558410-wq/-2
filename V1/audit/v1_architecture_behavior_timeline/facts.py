# -*- coding: utf-8 -*-
"""facts.py — exact trade list + ledger/ broker set comparison + post-change ledger actions."""
import json, os, collections, datetime as dt
REPO = r"C:\AIQuant"; BASE = os.path.join(REPO, "research", "hermes", "trader_v1"); UP = os.path.join(BASE, "v1_upgrade")
OUT = os.path.join(BASE, "audit", "v1_architecture_behavior_timeline")
import csv
rows = list(csv.DictReader(open(os.path.join(OUT, "trade_alignment.csv"), encoding="utf-8")))
print("n trades:", len(rows))
for r in rows:
    print(f"{r['trade_id']:<18} {r['side']:<5} in={r['entry_ts'][:19]} out={r['exit_ts'][:19]} {r['outcome']:<4} pnl={r['profit_price']:>7} net={r['net']:>7} epoch_in={r['entry_epoch']:<16} dec_seq={r['decision_seq']}")
print()
L = [json.loads(l) for l in open(os.path.join(UP,"ledger","v1_upgrade_ledger.jsonl"), encoding="utf-8") if l.strip()]
led_pos = sorted(str(e.get("order_id")) for e in L if e.get("event")=="POSITION")
brk_pos = sorted(r["position_id"] for r in rows)
print("ledger POSITION:", len(led_pos), "broker:", len(brk_pos))
print("ledger minus broker:", sorted(set(led_pos)-set(brk_pos)))
print("broker minus ledger:", sorted(set(brk_pos)-set(led_pos)))
print()
print("=== ledger events after 2026-10-02T04:00Z ===")
for e in L:
    if e.get("ts_utc","") >= "2026-10-02T04:00":
        act = e.get("action") or e.get("event")
        print(f"  seq{e.get('seq'):>4} {e.get('ts_utc')[:19]} {e.get('event'):<14} {str(act)[:70]} rr={e.get('risk_reasons')}")
