# -*- coding: utf-8 -*-
"""build_v2_db.py — V2 (paper) decision/trade database + PIT/vintage extraction. READ-ONLY.
Writes V2_HERMES_TRADE_DATABASE.jsonl, and prints PIT-relevant summaries.
"""
from __future__ import annotations
import json, os, glob, collections, datetime as dt

REPO = r"C:\AIQuant"
S = os.path.join(REPO, "research", "hermes", "trader_v2", "state")
OUT = os.path.join(REPO, "research", "hermes", "audit", "hermes_alpha_drift_pit")
os.makedirs(OUT, exist_ok=True)

def jl(p):
    if not os.path.exists(p): return []
    return [json.loads(l) for l in open(p, encoding="utf-8", errors="replace") if l.strip()]

opp = jl(os.path.join(S, "opportunity_ledger.jsonl"))
mem = jl(os.path.join(S, "hermes_memory.jsonl"))
pex = jl(os.path.join(S, "paper_executions.jsonl"))
print("opportunity_ledger:", len(opp), "hermes_memory:", len(mem), "paper_executions:", len(pex))

opp_kinds = collections.Counter(("DECISION" if r.get("decision") else "OPPORTUNITY") for r in opp)
print("opp kinds:", dict(opp_kinds))
dec = [r for r in opp if r.get("decision")]
print("decisions(opp):", collections.Counter(r.get("decision") for r in dec))
print("memory decisions:", collections.Counter(r.get("decision") for r in mem))
# regime tags overall
rt = collections.Counter()
for r in mem:
    for t in (r.get("regime_tags") or []): rt[t] += 1
print("top regime tags:", rt.most_common(10))
# outcomes recorded?
print("memory with outcome!=None:", sum(1 for r in mem if r.get("outcome")))
print("memory why_wrong!=None:", sum(1 for r in mem if r.get("why_wrong")))

# paper executions: real vs smoke
print("\npaper_executions rows:")
for r in pex:
    print("  ", {k: r.get(k) for k in ("plan_id","context_id","direction","status","position_id","net_usd","reason","ts")})

# paper account
pa = json.load(open(os.path.join(S, "paper_account.json"), encoding="utf-8"))
print("\npaper_account:", {k: pa.get(k) for k in ("initial_balance","balance","equity","realized_pnl","unrealized_pnl","drawdown")})
print("  positions:", [(p.get("position_id"), p.get("plan_id"), p.get("direction"), p.get("state")) for p in pa.get("positions", [])])

# ---- PIT: evidence_registry ----
er = jl(os.path.join(S, "evidence_registry.jsonl"))
print("\nevidence_registry rows:", len(er))
piv = collections.Counter(r.get("point_in_time_valid") for r in er)
print("point_in_time_valid:", dict(piv))
# published_at vs retrieved_at violations
def to_epoch(v):
    if isinstance(v, (int, float)): return float(v)
    if isinstance(v, str):
        s = v.strip()
        if s.isdigit(): return float(s)
        for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S GMT", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S%z"):
            try: return dt.datetime.strptime(s.replace("GMT","").strip(), fmt.replace(" %Z","").replace(" GMT","")).replace(tzinfo=dt.timezone.utc).timestamp()
            except Exception: pass
    return None
viol = 0; checked = 0
for r in er[:20000]:
    p = to_epoch(r.get("published_at")); q = to_epoch(r.get("retrieved_at"))
    if p is not None and q is not None:
        checked += 1
        if p > q: viol += 1
print(f"published_at>retrieved_at violations: {viol}/{checked}")
# version/revision presence
print("rows with version>1:", sum(1 for r in er if isinstance(r.get('version'),int) and r['version']>1))

# ---- macro vintage ----
mr = jl(os.path.join(S, "macro_releases.jsonl"))
print("\nmacro_releases rows:", len(mr))
print("release_timestamp_unknown:", collections.Counter(r.get("release_timestamp_unknown") for r in mr))
print("revision_changed:", collections.Counter(r.get("revision_changed") for r in mr))
print("pit_confidence:", collections.Counter(r.get("point_in_time_confidence") for r in mr))

# ---- emit V2 decision DB (memory) ----
rows = []
for r in mem:
    rows.append({"system": "V2_PAPER", "ts": r.get("ts"), "context_id": r.get("context_id"),
                 "regime_tags": r.get("regime_tags"), "n_candidates": r.get("n_candidates"),
                 "decision": r.get("decision"), "reason": r.get("reason"), "chosen": r.get("chosen"),
                 "counter_thesis": r.get("counter_thesis"), "outcome": r.get("outcome"), "why_wrong": r.get("why_wrong"),
                 "executed": False, "note": "paper ledger has no executed non-smoke trade"})
with open(os.path.join(OUT, "V2_HERMES_TRADE_DATABASE.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
    for r in rows: fh.write(json.dumps(r, ensure_ascii=False) + "\n")
print("\nwrote V2_HERMES_TRADE_DATABASE.jsonl rows:", len(rows))
# dir check
for d in ("runs", "snapshots", "decision_contexts"):
    p = os.path.join(S, d)
    print(d, "exists:", os.path.isdir(p), "files:", len(glob.glob(os.path.join(p, "**", "*"), recursive=True)) if os.path.isdir(p) else 0)
