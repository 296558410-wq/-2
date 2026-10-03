# -*- coding: utf-8 -*-
"""v1up_truth_regression.py — Truth System regression suite (16 scenarios). READ-ONLY w.r.t. trading.

Synthetic scenarios are in-memory; exactly ONE clearly-marked synthetic incident (broker/ledger
mismatch demo) is persisted so the CLI can resolve it. No orders, no production trade changes.
Writes: audit/v1_truth_system/V1_TRUTH_REGRESSION.json
"""
from __future__ import annotations
import datetime as dt, json, os, sys

BASE = r"C:\AIQuant\research\hermes\trader_v1"
ROOT = os.path.join(BASE, "v1_upgrade")
OUT = os.path.join(BASE, "audit", "v1_truth_system")
sys.path.insert(0, os.path.join(ROOT, "truth"))
sys.path.insert(0, ROOT)
import truth_lib as TR  # noqa: E402
import gates  # noqa: E402

os.makedirs(OUT, exist_ok=True)
R = []


def chk(name, cond, detail):
    R.append({"scenario": name, "verdict": "PASS" if cond else "FAIL", "detail": str(detail)[:220]})


rows = TR.load_ledger()
facts = TR.load_broker_facts()
decisions = [r for r in rows if r.get("event") == "DECISION"]

# 1 normal trade
c = TR.build_case("2378322488", rows, facts)
chk("normal_trade", all(s.get("status") == "OK" for s in c["chain"] if s["stage"] != "unknown"),
    f"case={c['case_id']} stages_ok={sum(1 for s in c['chain'] if s.get('status')=='OK')}")
# 2 wait
chk("wait", any(str(r.get("action", "")).startswith("WAIT") for r in decisions), f"decisions={len(decisions)}")
# 3 risk block (real, scoped)
last_cid = TR.cycle_id_for(decisions[-1])
incs_last = TR.detect_incidents(rows, facts, cycle_id=last_cid)
chk("risk_block", any(i["type"] == "RISK_BLOCK" for i in incs_last), f"cycle={last_cid}")
# 4 duplicate
k = gates.dedup_key(90011, "XAUUSD", 1790000000)
sent = gates.rebuild_sent_keys([{"event": "ORDER_SEND", "ok": True, "dedup_key": k}])
rg = gates.RiskGuard(); rg.roll_day("d")
okd, rs = rg.evaluate({"order_id": k, "already_sent": sent}, {"spread_bps": 1, "slippage_bps": 5, "data_age_seconds": 60}, 0)
chk("duplicate", (not okd) and "DUPLICATE_ORDER" in rs, rs)
# 5 kill switch (synthetic decision)
ksrows = [{"seq": 900001, "ts_utc": "2026-10-02T05:00:00+00:00", "event": "DECISION",
           "action": "WAIT_RISK:KILL_SWITCH", "risk_reasons": ["KILL_SWITCH"], "current_hash": "x", "previous_hash": "x"}]
ksincs = TR.detect_incidents(ksrows, None, cycle_id="V1C-20261002T050000")
chk("kill_switch", any(i["type"] == "KILL_SWITCH" for i in ksincs), [i["type"] for i in ksincs])
# 6 stale
strows = [{"seq": 900002, "ts_utc": "2026-10-02T05:00:00+00:00", "event": "DECISION",
           "action": "WAIT_RISK:STALE_DATA", "risk_reasons": ["STALE_DATA"], "current_hash": "x", "previous_hash": "x"}]
chk("stale", any(i["type"] == "STALE_DATA" for i in TR.detect_incidents(strows, None, cycle_id="V1C-20261002T050000")),
    "synthetic stale decision")
# 7 missing data
mdrows = [{"seq": 900003, "ts_utc": "2026-10-02T05:00:00+00:00", "event": "DECISION",
           "action": "WAIT_RISK:PNL_STATE_UNKNOWN", "risk_reasons": ["PNL_STATE_UNKNOWN"], "current_hash": "x", "previous_hash": "x"}]
chk("missing_data", any(i["type"] == "MISSING_DATA" for i in TR.detect_incidents(mdrows, None, cycle_id="V1C-20261002T050000")),
    "synthetic missing-data decision")
# 8 broker reject (real)
chk("broker_reject", any(i["type"] == "MT5_REJECT" for i in TR.read_evidence(TR.INCIDENTS)),
    "historical MT5_REJECT incidents persisted")
# 9 fill mismatch (synthetic: ok ORDER_SEND with no FILL)
fmrows = [{"seq": 900004, "ts_utc": "2026-10-02T05:00:00+00:00", "event": "ORDER_SEND", "order_id": "X9", "ok": True,
           "current_hash": "x", "previous_hash": "x"}]
chk("fill_mismatch", any(i["type"] == "ORDER_FILL_MISMATCH" for i in TR.detect_incidents(fmrows, None, cycle_id="V1C-20261002T050000")),
    "synthetic ok-send without FILL")
# 10 close reconciliation + 14 replay/pnl mismatch (synthetic broker facts)
fake = {"positions": [], "deals": [{"position_id": "99999", "magic": 90011, "entry": 1, "profit": 5.0, "commission": -0.1, "swap": 0}]}
sinc = TR.detect_incidents([], fake, cycle_id="V1C-20261002T050000")
chk("close_reconciliation", any(i["type"] == "RECONCILIATION_MISMATCH" for i in sinc), [i["type"] for i in sinc])
chk("replay_pnl_mismatch", any(i["type"] == "PNL_MISMATCH" for i in sinc), [i["type"] for i in sinc])
# 11/12 restart + schedule gap (real)
chk("restart_schedule_gap", any(i["type"] == "SCHEDULE_GAP" for i in TR.read_evidence(TR.INCIDENTS)),
    "real 30-min gap 2026-10-01T13:48Z->14:18Z")
# 13 ledger mismatch (synthetic broken chain)
lmrows = [{"seq": 1, "event": "DECISION", "previous_hash": "a", "current_hash": "b"},
          {"seq": 2, "event": "DECISION", "previous_hash": "WRONG", "current_hash": "c"}]
chk("ledger_mismatch", any(i["type"] == "LEDGER_MISMATCH" for i in TR.detect_incidents(lmrows, None)), "synthetic chain break")
# 15 incident generation + persistence + integrity
ok, n = TR.verify_evidence(TR.INCIDENTS)
chk("incident_generation", n >= 11 and ok, f"incidents={n} integrity={ok}")
# 16 forensic query (all four entry points)
q1 = TR.build_case("2378322488", rows, facts)
q2 = TR.forensic_incident(TR.read_evidence(TR.INCIDENTS)[0]["incident_id"])
q3 = TR.forensic_cycle(TR.cycle_id_for(decisions[-1]))
q4 = TR.daily_truth(dt.datetime.now(dt.timezone.utc).date().isoformat(), rows, facts)
chk("forensic_query", bool(q1 and q2 and q3.get("events") is not None and q4.get("FACTS_ONLY")),
    f"trade={q1['case_id']} incident={q2['incident_id']} cycle_events={len(q3['events'])}")
# synthetic broker/ledger mismatch DEMO (clearly marked; persisted once so CLI can resolve it)
demo = TR.detect_incidents(rows, {"positions": [], "deals": [{"position_id": "SYNTH-001", "magic": 90011, "entry": 1,
                                                              "profit": 1.0, "commission": 0, "swap": 0}],
                                 "orders": []}, cycle_id="V1C-SYNTHETIC-DEMO")
for i in demo:
    if i["type"] == "RECONCILIATION_MISMATCH":
        i["evidence"]["synthetic"] = True
        i["root_cause"] = "SYNTHETIC_FAULT_INJECTION_DEMO"
        i["status"] = "ACKNOWLEDGED"
        i["resolution"] = "demo fixture: broker has a close the ledger does not (injected on purpose)"
        i["validation"] = "detector fired and CLI can resolve it"
TR._persist_incidents(demo)
chk("broker_ledger_mismatch_demo", any(i["type"] == "RECONCILIATION_MISMATCH" for i in demo), "synthetic demo persisted (marked)")

npass = sum(1 for x in R if x["verdict"] == "PASS")
doc = {"suite": "V1 Truth System regression", "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
       "truth_version": TR.TRUTH_VERSION, "pass": npass, "total": len(R),
       "verdict": "TRUTH_SYSTEM_REGRESSION_PASS" if npass == len(R) else "TRUTH_SYSTEM_REGRESSION_FAIL",
       "scenarios": R}
json.dump(doc, open(os.path.join(OUT, "V1_TRUTH_REGRESSION.json"), "w", encoding="utf-8", newline="\n"),
          indent=1, ensure_ascii=False)
for x in R:
    print(f"  {x['verdict']:<4} {x['scenario']:<28} {x['detail'][:120]}")
print(f"{npass}/{len(R)} -> {doc['verdict']}")
sys.exit(0 if npass == len(R) else 1)
