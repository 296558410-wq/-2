# -*- coding: utf-8 -*-
"""V1-R6 — generic stager/persister.

Usage:
  python _r6_stage.py <batch_id> <role> <prefix> <ts:runid> [<ts:runid> ...]

role    : HERMES_A | HERMES_B_BLIND | HERMES_B_ADV | POST_OUTCOME
prefix  : child file prefix (e.g. R6_A, R6_BB, R6_BA)
Each ts is YYYYMMDD; the child file is <prefix>_<ts>.json under forecasts/ (read-back by the parent).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

BASE = r"C:\AIQuant\research\hermes\trader_v1"
ROOT = os.path.join(BASE, "v1_r6_hermes_validation")
PY = r"C:\AIQuant\.venv\Scripts\python.exe"
CHILD = os.path.join(ROOT, "forecasts")
PROMPT = {"HERMES_A": "hermes_a_r6.txt", "HERMES_B_BLIND": "hermes_b_blind_r6.txt", "HERMES_B_ADV": "hermes_b_adversarial_r6.txt",
           "POST_OUTCOME": "hermes_b_blind_r6.txt"}
PH = {k: hashlib.sha256(open(os.path.join(ROOT, "prompt", v), "rb").read()).hexdigest() for k, v in PROMPT.items()}
SID_PREFIX = {"HERMES_A": "A", "HERMES_B_BLIND": "BB", "HERMES_B_ADV": "BA", "POST_OUTCOME": "PO"}


def main():
    bid, role, prefix = sys.argv[1], sys.argv[2], sys.argv[3]
    pairs = sys.argv[4:]
    recs = []
    for p in pairs:
        ts, run_id = p.split(":")
        sid = f"{SID_PREFIX[role]}_{ts}"
        fp = os.path.join(CHILD, f"{prefix}_{ts}.json")
        raw = open(fp, encoding="utf-8").read() if os.path.exists(fp) else ""
        recs.append({"run_id": run_id, "sample_id": sid, "agent_role": role, "context_hash": f"CTX_{ts}T120000Z",
                      "attempt": 1, "prompt_hash": PH.get(role), "raw_text": raw})
    stage = os.path.join(ROOT, "staging", f"{bid}.json")
    os.makedirs(os.path.dirname(stage), exist_ok=True)
    json.dump(recs, open(stage, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    r = subprocess.run([PY, os.path.join(ROOT, "_r6_persist.py"), stage], capture_output=True, text=True)
    print(bid, r.stdout.strip())
    if r.returncode != 0:
        print("STDERR:", r.stderr[-600:])


if __name__ == "__main__":
    main()
