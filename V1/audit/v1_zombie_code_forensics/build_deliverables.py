# -*- coding: utf-8 -*-
"""build_deliverables.py — GIT_CLEANUP_TIMELINE.csv + DELETED_CODE_IMPACT.jsonl (READ-ONLY inputs)."""
from __future__ import annotations
import csv, json, os, re
REPO = r"C:\AIQuant"
OUT = os.path.join(REPO, "research", "hermes", "trader_v1", "audit", "v1_zombie_code_forensics")
V1 = "research/hermes/trader_v1/"
raw = json.load(open(os.path.join(OUT, "git_changes_raw.json"), encoding="utf-8"))
dels = json.load(open(os.path.join(OUT, "git_deletions_raw.json"), encoding="utf-8"))

def cls(p):
    p2 = p[len(V1):] if p.startswith(V1) else p
    if p2.endswith(".py") and ("/" not in p2 or p2.startswith("v1_upgrade/")):
        return "runtime_code"
    if "/v1_upgrade/registry/" in p2 or "/registry/" in p2 or p2.endswith(".json") and ("config" in p2 or "mapping" in p2):
        return "config"
    if p2.startswith("run_state/"): return "state"
    if re.match(r"v1_r\d", p2) or "prediction_route" in p2: return "research"
    if p2.startswith("audit/"): return "audit"
    if p2.startswith("tests/"): return "test"
    return "other"

# timeline csv (all V1-touching commits)
rows = []
for c in raw["commits"]:
    for ch in c["changes"]:
        if not ch["path"].startswith(V1): continue
        rows.append({"commit": c["hash"][:9], "date": c["date"][:10], "author": c["author"],
                     "subject": c["subject"], "status": ch["status"], "path": ch["path"][len(V1):],
                     "path_class": cls(ch["path"])})
with open(os.path.join(OUT, "GIT_CLEANUP_TIMELINE.csv"), "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["commit", "date", "author", "subject", "status", "path", "path_class"])
    w.writeheader()
    for r in rows: w.writerow(r)
print("GIT_CLEANUP_TIMELINE.csv rows:", len(rows))
print("by class:", {k: sum(1 for r in rows if r['path_class'] == k) for k in sorted({r['path_class'] for r in rows})})
print("by status:", {k: sum(1 for r in rows if r['status'][0] == k) for k in sorted({r['status'][0] for r in rows})})

# deleted-code impact
REF = {
 "run_state/decisions": {"runtime_referenced": True, "refs": ["engine.py:31 DEC_DIR = RUN/decisions",
    "metrics.py:130-133 decisions_recent() globs run_state/decisions/*.json", "opportunity.py:17 DEC_DIR = RUN/decisions"],
    "consumer_kind": "REPORTING+WRITE (dashboard metrics/opportunity frequency); engine also writes DEC_DIR each cycle"},
 "run_state/positions": {"runtime_referenced": True, "refs": ["position.py:23 STATE_DIR = HERE/run_state/positions",
    "position.py:360 open_positions()", "metrics.py:14 POS_DIR"], "consumer_kind": "POSITION_STATE_READ (state machine open_positions)"},
 "run_state/trader_summary.txt": {"runtime_referenced": False, "refs": [], "consumer_kind": "NONE_FOUND"},
}
imp = []
for c in dels["hits"]:
    for p in c["paths"]:
        if not p["path"].startswith(V1): continue
        rel = p["path"][len(V1):]
        key = next((k for k in REF if rel.startswith(k)), None)
        info = REF.get(key)
        imp.append({"commit": c["hash"][:9], "date": c["date"], "author": c["author"], "subject": c["subject"],
                    "status": p["status"], "path": rel, "path_class": cls(p["path"]),
                    "runtime_referenced": (info["runtime_referenced"] if info else False),
                    "runtime_refs": (info["refs"] if info else []),
                    "consumer_kind": (info["consumer_kind"] if info else "NONE_FOUND"),
                    "is_code": p["path"].endswith(".py")})
with open(os.path.join(OUT, "DELETED_CODE_IMPACT.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
    for r in imp: fh.write(json.dumps(r, ensure_ascii=False) + "\n")
print("DELETED_CODE_IMPACT.jsonl rows:", len(imp),
      "| code deletions:", sum(1 for r in imp if r["is_code"]),
      "| runtime_referenced:", sum(1 for r in imp if r["runtime_referenced"]))
from collections import Counter
print("deleted path_class:", dict(Counter(r["path_class"] for r in imp)))
print("deleted commit summaries:", sorted({(r['commit'], r['date'], len([x for x in imp if x['commit']==r['commit']])) for r in imp}))
