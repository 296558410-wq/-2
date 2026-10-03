# -*- coding: utf-8 -*-
"""shadow_analyze.py — Shadow 统计 + reference↔生产 逐周期对齐 + 机会供给分析。只读。"""
from __future__ import annotations
import collections, glob, json, os, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
V2 = HERE.parent; STATE = V2 / "state"
_norm = lambda s: re.sub(r"[^0-9]", "", str(s or ""))   # 归一 cycle 格式 (20261002T1407Z == 2026-10-02T14:07Z)

rows = [json.loads(l) for l in open(HERE / "SHADOW_DECISIONS.jsonl", encoding="utf-8") if l.strip()]
ref = [r for r in rows if r["shadow_side"] == "reference"]; ag = [r for r in rows if r["shadow_side"] == "agent"]
by_cycle_ref = {_norm(r["cycle"]): r for r in ref}

# 生产记录的决策（按 context_id 关联冻结 ctx → cycle）
ctx_cycle = {}
for f in glob.glob(str(STATE / "decision_contexts" / "*.json")):
    try:
        c = json.loads(Path(f).read_text(encoding="utf-8"))
        if c.get("cycle"): ctx_cycle[c.get("context_id")] = _norm(c["cycle"])
    except Exception: pass
mem = [json.loads(l) for l in open(STATE / "hermes_memory.jsonl", encoding="utf-8") if l.strip()]
prod_by_cycle = {}
for m in mem:
    cyc = ctx_cycle.get(m.get("context_id"))
    if cyc: prod_by_cycle[cyc] = m
aligned = agree = 0; examples = []
for cyc, r in by_cycle_ref.items():
    p = prod_by_cycle.get(cyc)
    if not p: continue
    aligned += 1
    if p.get("decision") == r["decision"]: agree += 1
    elif len(examples) < 5: examples.append({"cycle": cyc, "shadow_ref": r["decision"], "prod": p.get("decision")})

stats = {
 "cycles": len(ref),
 "reference": dict(collections.Counter(r["decision"] for r in ref)),
 "agent": dict(collections.Counter(r["decision"] for r in ag)),
 "agent_llm": dict(collections.Counter(r.get("agent_llm") for r in ag)),
 "agreement_ref_vs_agent": sum(1 for a, b in zip(ref, ag) if a["decision"] == b["decision"]),
 "ref_vs_production": {"matched_cycles": aligned, "decision_agree": agree,
                       "agree_pct": round(100 * agree / aligned, 1) if aligned else None, "mismatch_examples": examples},
 "candidates_per_cycle": dict(collections.Counter(len(r["candidates"]) for r in ref)),
 "candidate_ids": dict(collections.Counter(cid for r in ref for cid in r["candidates"])),
 "health_dist": dict(collections.Counter(r.get("health_overall") for r in ref)),
 "a1_freshness_dist": dict(collections.Counter(r.get("a1_freshness") for r in ref)),
 "prod_by_cycle_n": len(prod_by_cycle), "backfill_cycles_n": len(by_cycle_ref),
}
json.dump(stats, open(HERE / "_backfill_stats.json", "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
print(json.dumps(stats, ensure_ascii=False, indent=1))
