# -*- coding: utf-8 -*-
"""build.py — V2 full-state audit: TRADE_HISTORY.csv + EVIDENCE_MANIFEST.json + aggregates (READ-ONLY)."""
from __future__ import annotations
import csv, collections, datetime as dt, hashlib, json, os, subprocess
REPO = r"C:\AIQuant"; V2 = os.path.join(REPO, "research", "hermes", "trader_v2")
OUT = os.path.join(V2, "audit", "V2_FULL_STATE_SNAPSHOT"); os.makedirs(OUT, exist_ok=True)
def jl(p): return [json.loads(l) for l in open(p, encoding="utf-8", errors="replace") if l.strip()]
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None
def git(*a):
    r = subprocess.run(["git", "-C", REPO, *a], capture_output=True)
    return (r.stdout or b"").decode("utf-8", "replace")

mem = jl(os.path.join(V2, "state", "hermes_memory.jsonl"))
opp = jl(os.path.join(V2, "state", "opportunity_ledger.jsonl"))
pex = jl(os.path.join(V2, "state", "paper_executions.jsonl"))
v2l = jl(os.path.join(V2, "ledger", "hermes_v2_ledger.jsonl"))
dec = [r for r in opp if r.get("decision")]
opps = [r for r in opp if not r.get("decision")]

rows = []
for r in mem:
    rows.append({"record_type": "decision", "ts": r.get("ts"), "id": r.get("context_id"),
                 "decision": r.get("decision"), "chosen": r.get("chosen"), "reason": r.get("reason"),
                 "direction": None, "qty": None, "price": None, "net_pnl": None, "r_multiple": None,
                 "executed": False, "broker_trade": False, "regime_tags": "|".join(r.get("regime_tags") or [])})
for r in pex:
    rows.append({"record_type": "paper_execution", "ts": r.get("ts"), "id": r.get("position_id"),
                 "decision": r.get("status"), "chosen": r.get("plan_id"), "reason": r.get("reason"),
                 "direction": r.get("direction"), "qty": r.get("qty_lots"), "price": r.get("fill_price") or r.get("exit_price"),
                 "net_pnl": r.get("net_usd"), "r_multiple": None, "executed": True, "broker_trade": False, "regime_tags": ""})
for r in v2l:
    rows.append({"record_type": "v2_ledger_event", "ts": r.get("timestamp_utc"), "id": r.get("event_id"),
                 "decision": r.get("event_type"), "chosen": r.get("strategy_id"), "reason": r.get("reject_reason") or r.get("reason"),
                 "direction": r.get("direction"), "qty": r.get("qty_lots"), "price": r.get("price"),
                 "net_pnl": r.get("pnl_usd") or r.get("net_usd"), "r_multiple": None,
                 "executed": r.get("event_type") in ("EXECUTION_REQUEST", "ORDER_FILLED"), "broker_trade": False, "regime_tags": ""})
rows.append({"record_type": "broker_trade", "ts": None, "id": "V2_BROKER_MAGIC_NOT_FOUND", "decision": "NONE",
             "chosen": None, "reason": "no MT5 magic mapped to V2; broker magics present: 0/90001/90002/90011",
             "direction": None, "qty": None, "price": None, "net_pnl": 0.0, "r_multiple": None,
             "executed": False, "broker_trade": True, "regime_tags": ""})
with open(os.path.join(OUT, "TRADE_HISTORY.csv"), "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader()
    for r in rows: w.writerow(r)

agg = {
 "decisions": {"n": len(mem), "by_decision": dict(collections.Counter(r.get("decision") for r in mem)),
               "chosen_top": dict(collections.Counter(r.get("chosen") for r in mem).most_common(8)),
               "with_outcome": sum(1 for r in mem if r.get("outcome")),
               "first": mem[0]["ts"] if mem else None, "last": mem[-1]["ts"] if mem else None},
 "opportunities": {"n": len(opps), "categories": dict(collections.Counter(
     (o.get("opportunity_id", "").split("_opp_")[-1].rsplit("_", 0)[0] if "_opp_" in o.get("opportunity_id", "") else o.get("opportunity_id")) for o in opps).most_common(10))},
 "paper_executions": {"n": len(pex)},
 "v2_ledger": {"n": len(v2l), "types": dict(collections.Counter(r.get("event_type") for r in v2l)),
               "first": v2l[0].get("timestamp_utc") if v2l else None, "last": v2l[-1].get("timestamp_utc") if v2l else None},
 "broker": {"magics_present": [0, 90001, 90002, 90011], "v2_magic": None, "v2_broker_trades": 0},
 "runs": {"active": json.load(open(os.path.join(V2, "state", "runs", "ACTIVE.json"), encoding="utf-8"))},
 "decision_contexts": len([1 for _ in os.scandir(os.path.join(V2, "state", "decision_contexts"))]) if os.path.isdir(os.path.join(V2, "state", "decision_contexts")) else 0,
 "snapshots": len([1 for _ in os.scandir(os.path.join(V2, "state", "snapshots"))]) if os.path.isdir(os.path.join(V2, "state", "snapshots")) else 0,
 "git": {"head": git("rev-parse", "HEAD").strip(), "branch": git("rev-parse", "--abbrev-ref", "HEAD").strip(),
         "v2_commits_all_refs": len([x for x in git("log", "--all", "--oneline", "--", "research/hermes/trader_v2").splitlines() if x.strip()]),
         "v2_dirty_files": len([x for x in git("status", "--porcelain", "research/hermes/trader_v2").splitlines() if x.strip()]),
         "v2_first_commit": git("log", "--all", "--date=short", "--pretty=format:%h|%ad|%s", "--diff-filter=A", "--", "research/hermes/trader_v2/V2_ARCHITECTURE.md").strip()[:120]},
}
json.dump(agg, open(os.path.join(OUT, "_aggregates.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)

srcs = [os.path.join(V2, "config", "v2_config.json"), os.path.join(V2, "state", "runs", "ACTIVE.json"),
        os.path.join(V2, "state", "v2_run_health.json"), os.path.join(V2, "state", "v2_scheduler_state.json"),
        os.path.join(V2, "state", "hermes_decision_latest.json"), os.path.join(V2, "state", "agent1_latest.json"),
        os.path.join(V2, "state", "agent2_latest.json"), os.path.join(V2, "state", "hermes_state.json"),
        os.path.join(V2, "state", "paper_account.json"), os.path.join(V2, "state", "paper_executions.jsonl"),
        os.path.join(V2, "ledger", "hermes_v2_ledger.jsonl"), os.path.join(V2, "state", "hermes_memory.jsonl"),
        os.path.join(V2, "state", "opportunity_ledger.jsonl"), os.path.join(V2, "state", "macro_releases.jsonl"),
        os.path.join(V2, "state", "V2_G3_FREEZE.json"), os.path.join(V2, "state", "V2_G3_EXECUTION_INCIDENT.json"),
        os.path.join(V2, "runtime", "v2_scheduled_cycle.py"), os.path.join(V2, "hermes", "hermes.py"),
        os.path.join(V2, "hermes", "discovery.py"), os.path.join(V2, "hermes", "context.py")]
man = {"schema": "v2_full_state_evidence/1", "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
       "mode": "READ-ONLY", "order_send": 0, "sources": [{"path": os.path.relpath(p, REPO), "sha256": sha(p), "bytes": os.path.getsize(p) if os.path.exists(p) else None} for p in srcs]}
json.dump(man, open(os.path.join(OUT, "EVIDENCE_MANIFEST.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
print(json.dumps(agg, ensure_ascii=False, indent=1)[:2600])
print("CSV rows:", len(rows), "| manifest sources:", len(man["sources"]))
