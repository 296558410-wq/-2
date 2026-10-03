# -*- coding: utf-8 -*-
"""v1up_regression_suite.py — permanent RiskGuard / replay regression suite (READ-ONLY, order_send=0).

Turns the V1 risk-guard findings into an automated check. Any failure => CI/AUDIT FAIL (exit 1).
Run:  C:\\AIQuant\\.venv\\Scripts\\python.exe research\\hermes\\trader_v1\\audit\\v1_full_reaudit\\v1up_regression_suite.py
"""
from __future__ import annotations
import datetime as dt, hashlib, json, os, sys

BASE = r"C:\AIQuant\research\hermes\trader_v1"
ROOT = os.path.join(BASE, "v1_upgrade")
AUDIT = os.path.join(BASE, "audit", "v1_full_reaudit")
LEDGER = os.path.join(ROOT, "ledger", "v1_upgrade_ledger.jsonl")
sys.path.insert(0, ROOT)
import gates  # noqa: E402

results = []


def chk(name, cond, detail):
    results.append({"name": name, "verdict": "PASS" if cond else "FAIL", "detail": str(detail)[:200]})


def fresh(**kw):
    d = {"spread_bps": 1.0, "slippage_bps": 5.0, "data_age_seconds": 120}
    d.update(kw)
    return d


def rg_with(day="2026-10-02", losses=0, pnl=0.0):
    r = gates.RiskGuard(); r.roll_day(day)
    for _ in range(losses):
        r.note_close(pnl)
    return r


# A) each declared rule can actually block -----------------------------------
chk("daily_loss_blocks", not rg_with(losses=3, pnl=-7.0).evaluate({"order_id": "x"}, fresh(), 0)[0]
    and "MAX_DAILY_LOSS" in rg_with(losses=3, pnl=-7.0).evaluate({"order_id": "x"}, fresh(), 0)[1], "daily=-21 deny")
chk("consecutive_loss_blocks", not rg_with(losses=3, pnl=-7.0).evaluate({"order_id": "x"}, fresh(), 0)[0], "cons=3 deny")
chk("consecutive_allows_2", rg_with(losses=2, pnl=-7.0).evaluate({"order_id": "x"}, fresh(), 0)[0], "cons=2 allow")
chk("position_blocks", not gates.RiskGuard().evaluate({"order_id": "x"}, fresh(), 1)[0], "pos=1 deny")
chk("stale_blocks", not gates.RiskGuard().evaluate({"order_id": "x"}, fresh(data_age_seconds=1000), 0)[0]
    and "STALE_DATA" in gates.RiskGuard().evaluate({"order_id": "x"}, fresh(data_age_seconds=1000), 0)[1], "age=1000 deny")
chk("slippage_blocks", not gates.RiskGuard().evaluate({"order_id": "x"}, fresh(slippage_bps=20), 0)[0], "20bps deny")
chk("normal_allows", gates.RiskGuard().evaluate({"order_id": "x"}, fresh(), 0)[0], "clean allow")
# B) rebuild / restart recovery ----------------------------------------------
ev = [{"event": "PNL", "pnl": -7.0, "commission": -0.2, "swap": 0, "broker_time_utc": "2026-10-02T08:00:00+00:00"}
      for _ in range(3)]
rr = gates.rebuild_risk_state(gates.RiskGuard(), ev, "2026-10-02")
chk("restart_rebuild_blocks", not rr.evaluate({"order_id": "x"}, fresh(), 0)[0] and rr.consecutive_losses == 3,
    f"rebuilt cons={rr.consecutive_losses} daily={round(rr.daily_loss,2)}")
chk("rebuild_idempotent", (lambda a, b: a.consecutive_losses == b.consecutive_losses and a.daily_loss == b.daily_loss)(
    gates.rebuild_risk_state(gates.RiskGuard(), ev, "2026-10-02"),
    gates.rebuild_risk_state(gates.RiskGuard(), ev, "2026-10-02")), "same ledger -> same state")
# C) data anomaly => safe state ----------------------------------------------
chk("stale_none_failclosed", not gates.RiskGuard().evaluate({"order_id": "x"}, fresh(data_age_seconds=None), 0)[0], "None age deny")
chk("age_same_source", gates.data_age_seconds(10500, [{"time": 9000}, {"time": 9940}, {"time": 10540}]) == 500.0, "server-frame age")
# D) ledger chain + replay determinism ---------------------------------------
lg = gates.Ledger(LEDGER)
ok, n, bad = lg.verify()
rl = lg.replay()
chk("ledger_chain", ok, f"ok={ok} entries={n} bad={bad}")
chk("replay_deterministic", lg.replay() == lg.replay(), f"realized={rl['realized_pnl']} sends={rl['sends']}")
chk("ledger_seq_gap_free",
    (lambda s: s == list(range(s[0], s[0] + len(s))))([json.loads(l)["seq"] for l in open(LEDGER, encoding="utf-8") if l.strip()]),
    "seq contiguous")

npass = sum(1 for r in results if r["verdict"] == "PASS")
doc = {"generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "suite": "V1 RiskGuard/Replay regression",
       "pass": npass, "total": len(results), "verdict": "CI_PASS" if npass == len(results) else "CI_FAIL",
       "results": results}
os.makedirs(AUDIT, exist_ok=True)
json.dump(doc, open(os.path.join(AUDIT, "V1_REGRESSION_SUITE_RESULT.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
for r in results:
    print(f"  {r['verdict']:<4} {r['name']}  {r['detail']}")
print(f"{npass}/{len(results)} -> {doc['verdict']}")
sys.exit(0 if npass == len(results) else 1)
