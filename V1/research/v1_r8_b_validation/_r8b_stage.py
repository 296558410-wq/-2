# -*- coding: utf-8 -*-
"""V1-R8-B — staging + parent-authoritative persistence (reuses the proven R6 protocol module).

Usage:
  python _r8b_stage.py <batch_id> <role> <prefix> <ts:runid> [<ts:runid> ...]

role: HERMES_A | HERMES_B_BLIND | HERMES_B_ADV | POST_OUTCOME
prefix: child file prefix (R8B_A, R8B_BB, R8B_BA, R8B_PO)
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys

BASE = r"C:\AIQuant\research\hermes\trader_v1"
ROOT = os.path.join(BASE, "v1_r8_b_validation")
R6 = os.path.join(BASE, "v1_r6_hermes_validation")
PY = r"C:\AIQuant\.venv\Scripts\python.exe"
FORECASTS = os.path.join(ROOT, "forecasts")

A_KEYS = ["sample_id", "scenario_family", "horizon", "observations", "what_i_know", "what_i_do_not_know",
           "evidence", "counter_evidence", "possible_mechanisms", "primary_scenario", "alternative_scenario",
           "evidence_strength", "confidence", "uncertainty", "invalidation", "change_my_mind", "abstain", "questions"]
BLIND_KEYS = ["audit_id", "current_state", "structure", "mechanism", "primary_scenario", "direction", "horizon",
               "confidence", "counter_evidence", "invalidation"]
ADV_KEYS = ["audit_id", "overall_verdict", "focus_verdicts", "evidence"]
POST_KEYS = ["audit_id", "outcome_alignment_verdict"]
REQUIRED = {"HERMES_A": A_KEYS, "HERMES_B_BLIND": BLIND_KEYS, "HERMES_B_ADV": ADV_KEYS, "POST_OUTCOME": POST_KEYS}
PROMPT = {"HERMES_A": "hermes_a_r5_prompt.txt", "HERMES_B_BLIND": "hermes_b_blind_r6.txt", "HERMES_B_ADV": "hermes_b_adversarial_r6.txt", "POST_OUTCOME": "hermes_b_adversarial_r6.txt"}
PROMPT_DIRS = {"HERMES_A": os.path.join(BASE, "v1_r5_hermes_forecast_discipline", "prompt"),
                "HERMES_B_BLIND": os.path.join(BASE, "v1_r6_hermes_validation", "prompt"),
                "HERMES_B_ADV": os.path.join(BASE, "v1_r6_hermes_validation", "prompt"),
                "POST_OUTCOME": os.path.join(BASE, "v1_r6_hermes_validation", "prompt")}
SID = {"HERMES_A": "A", "HERMES_B_BLIND": "BB", "HERMES_B_ADV": "BA", "POST_OUTCOME": "PO"}


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def main():
    bid, role, prefix = sys.argv[1], sys.argv[2], sys.argv[3]
    pairs = sys.argv[4:]
    ph = hashlib.sha256(open(os.path.join(PROMPT_DIRS[role], PROMPT[role]), "rb").read()).hexdigest()
    recs = []
    for p in pairs:
        ts, run_id = p.split(":")
        sid = f"{SID[role]}_{ts}"
        fp = os.path.join(FORECASTS, f"{prefix}_{ts}.json")
        raw = open(fp, encoding="utf-8").read() if os.path.exists(fp) else ""
        recs.append({"run_id": run_id, "sample_id": sid, "agent_role": role,
                      "context_hash": f"CTX_{ts}T000000Z", "attempt": 1, "prompt_hash": ph, "raw_text": raw})
    stage = os.path.join(ROOT, "staging", f"{bid}.json")
    os.makedirs(os.path.dirname(stage), exist_ok=True)
    json.dump(recs, open(stage, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    # retarget the proven persister at R8-B and swap in the R8-B schemas
    P = load("p6", os.path.join(R6, "_r6_persist.py"))
    P.ROOT = ROOT
    P.LEDGER = os.path.join(ROOT, "ledger", "v1_r8_b_ledger.jsonl")
    P.PAYLOADS = os.path.join(ROOT, "payloads")
    P.REQUIRED = REQUIRED
    os.makedirs(P.PAYLOADS, exist_ok=True)
    results, n = P.persist(recs, tag=bid)
    ok = sum(1 for r in results if r.get("accepted"))
    fails = [r for r in results if not r.get("accepted")]
    out = {"ts_utc": P.NOW, "batch": bid, "role": role, "n": len(results), "accepted": ok, "failed": len(fails),
            "ledger_entries_total": n, "results": results}
    json.dump(out, open(os.path.join(ROOT, "audit", f"persist_{bid}.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps({"batch": bid, "role": role, "n": len(results), "accepted": ok, "failed": len(fails), "ledger": n}, ensure_ascii=False))
    for r in fails:
        print("FAIL:", r["sample_id"], r["error_type"], r["error_detail"])


if __name__ == "__main__":
    main()
