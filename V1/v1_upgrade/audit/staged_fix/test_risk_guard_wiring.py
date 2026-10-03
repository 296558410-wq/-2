# -*- coding: utf-8 -*-
"""test_risk_guard_wiring.py — STAGED regression tests for the V1 risk-guard wiring fix.

Run:  python audit/staged_fix/test_risk_guard_wiring.py
Read-only: imports the UNMODIFIED production gates.RiskGuard; touches no production file,
writes nothing, sends nothing. Proves the staged wiring logic before it is applied.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)                      # gates.py
sys.path.insert(0, HERE)                      # risk_state.py

from gates import RiskGuard                    # noqa: E402  (production, unmodified)
import risk_state as RS                        # noqa: E402

DAY = "2026-09-30"
FRESH = {"spread_bps": 1.0, "slippage_bps": 5.0, "data_age_seconds": 100}
INTENT = {"order_id": "o-test"}


def pnl_event(hhmm, pnl, commission=-0.2, swap=0.0, day=DAY):
    return {"event": "PNL", "pnl": pnl, "commission": commission, "swap": swap,
            "broker_time_utc": f"{day}T{hhmm}:00+00:00", "ts_utc": f"{day}T{hhmm}:30+00:00"}


def ev(events, market, positions=0):
    rg = RS.rebuild_risk_state(RiskGuard(), events, DAY)
    ok, reasons = rg.evaluate(dict(INTENT), market, positions)
    return ok, reasons, rg


results = []


def check(name, cond, detail):
    results.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}  {detail}")


# 1) max_consecutive_loss = 3 : the 4th entry must be rejected ------------------
ok3, r3, rg3 = ev([pnl_event("08:00", -7.0), pnl_event("09:00", -7.0), pnl_event("10:00", -8.0)], FRESH)
check("mcl_blocks_4th", (not ok3) and "MAX_CONSECUTIVE_LOSS" in r3, f"3 losses cons={rg3.consecutive_losses} -> {r3}")
ok2, r2, rg2 = ev([pnl_event("08:00", -7.0), pnl_event("09:00", -7.0)], FRESH)
check("mcl_allows_3rd", ok2, f"2 losses cons={rg2.consecutive_losses} -> allow={ok2} {r2}")

# 2) max_daily_loss = -20 : rejected once the day's realized loss reaches the limit
okd, rd, rgd = ev([pnl_event("08:00", -7.0), pnl_event("09:00", -7.0), pnl_event("10:00", -7.0)], FRESH)
check("mdl_blocks", (not okd) and "MAX_DAILY_LOSS" in rd, f"daily={round(rgd.daily_loss,2)} -> {rd}")
okd2, rd2, rgd2 = ev([pnl_event("08:00", -9.0)], FRESH)
check("mdl_below_not_blocked", okd2, f"daily={round(rgd2.daily_loss,2)} -> allow={okd2}")

# 3) stale data : rejected when real age exceeds 900s (same-source server frame)
oks, rs, _ = ev([], {"spread_bps": 1.0, "slippage_bps": 5.0, "data_age_seconds": 1000})
check("stale_blocks", (not oks) and "STALE_DATA" in rs, f"age=1000 -> {rs}")
okf, rf, _ = ev([], {"spread_bps": 1.0, "slippage_bps": 5.0, "data_age_seconds": 120})
check("fresh_allows", okf, f"age=120 -> {rf}")
# the old mixed-frame bug produced negative age; same-source now yields the true positive age
# 3 bars: newest (10540) may be the forming bar; bars[-2]=9940 is the last COMPLETED bar
age_ok = RS.data_age_seconds(10500, [{"time": 9000}, {"time": 9940}, {"time": 10540}])
check("age_same_source", age_ok == 500.0, f"tick(10500)-last_completed_close(9940+60)={age_ok}")
check("age_none_blocks", (lambda o: (not o[0]) and "STALE_DATA" in o[1])(ev([], {"spread_bps": 1, "slippage_bps": 0, "data_age_seconds": None})[:2]), "None age -> STALE_DATA (fail-closed)")

# 4) slippage : real realized slippage over the limit blocks
oksl, rsl, _ = ev([], {"spread_bps": 1.0, "slippage_bps": 20.0, "data_age_seconds": 100})
check("slippage_blocks", (not oksl) and "SLIPPAGE_LIMIT" in rsl, f"20 bps -> {rsl}")

# 5) normal path : nothing falsely rejected
okn, rn, rgn = ev([pnl_event("08:00", 12.0)], FRESH)
check("normal_allows", okn and rn == [], f"{rn}")

# 6) day isolation : yesterday's loss must not count today
oky, ry, rgy = ev([pnl_event("08:00", -19.0, day="2026-09-29")], FRESH)
check("day_isolation", oky and rgy.daily_loss == 0.0, f"daily={round(rgy.daily_loss,2)} -> allow={oky}")

# 7) offline defect reproduction over the REAL ledger (counterfactual per open) ----------
LEDGER = os.path.join(ROOT, "ledger", "v1_upgrade_ledger.jsonl")
rows = [json.loads(l) for l in open(LEDGER, encoding="utf-8") if l.strip()]
pnls = [e for e in rows if e["event"] == "PNL"]
opens = sorted((dt.datetime.fromisoformat(e["ts_utc"]), str(e.get("order_id")))
               for e in rows if e["event"] == "POSITION")
blocked = 0
by_day = {}
for ts, _oid in opens:
    known = [e for e in pnls if RS.realized_close_utc(e) <= ts]
    rg = RS.rebuild_risk_state(RiskGuard(), known, ts.date().isoformat())
    ok, reasons = rg.evaluate(dict(INTENT), FRESH, 0)
    if not ok:
        blocked += 1
        by_day[ts.date().isoformat()] = by_day.get(ts.date().isoformat(), 0) + 1
check("ledger_repro_should_reject", blocked >= 8, f"should-reject-but-allowed={blocked} (by day {by_day})")

n = len(results)
npass = sum(1 for _, c, _ in results if c)
print(f"\n{npass}/{n} PASS")
sys.exit(0 if npass == n else 1)
