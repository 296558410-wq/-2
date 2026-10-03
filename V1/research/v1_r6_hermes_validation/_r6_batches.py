# -*- coding: utf-8 -*-
"""V1-R6 — batch staging. Records are built from the child-written forecast files (parent read-back),
plus explicit FAILURE records for children that produced nothing usable (never silently dropped).

Run:  python _r6_batches.py <batch_id> [--persist]
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
PROMPT = {"HERMES_A": "hermes_a_r6.txt", "HERMES_B_BLIND": "hermes_b_blind_r6.txt", "HERMES_B_ADV": "hermes_b_adversarial_r6.txt"}
PH = {k: hashlib.sha256(open(os.path.join(ROOT, "prompt", v), "rb").read()).hexdigest() for k, v in PROMPT.items()}


def rec(sid, ts, run_id, role="HERMES_A", raw=None, prefix="R6_A"):
    if raw is None:
        p = os.path.join(CHILD, f"{prefix}_{ts}.json")
        if os.path.exists(p):
            raw = open(p, encoding="utf-8").read()
    return {"run_id": run_id, "sample_id": sid, "agent_role": role, "context_hash": f"CTX_{ts}T120000Z",
             "attempt": 1, "prompt_hash": PH.get(role), "raw_text": raw if raw is not None else ""}


BATCHES = {
    "a1": [
        rec("A_20260718", "20260718", "adf04fb2-8fbe-4fe6-b2f8-5b816d61cbe2", raw=""),
        rec("A_20260720", "20260720", "ab3b8c53-2da9-414b-92ca-9b7fb0c2f027"),
        rec("A_20260722", "20260722", "e84fd297-95f7-45c8-9e01-d23448a21d10", raw=""),
        rec("A_20260724", "20260724", "57efb97f-5368-4496-977b-8f361f14d1d2"),
        rec("A_20260726", "20260726", "8c6c440b-d69a-44db-a471-1c9c4fd7012b", raw=""),
    ],
    "a2": [
        rec("A_20260718", "20260718", "d9d79caa-eda7-438c-978a-77b1eef44738"),
        rec("A_20260722", "20260722", "0aac9077-de4f-4ec4-bea7-bfffc1d8168d"),
        rec("A_20260726", "20260726", "ff69854b-7335-4348-9293-04aaedefa3b1"),
        rec("A_20260728", "20260728", "189a3500-9e53-4d96-b9d3-8d14814266b9"),
        rec("A_20260730", "20260730", "0f056171-0436-4966-bc94-6903763c7df8"),
    ],
    "a3": [
        rec("A_20260801", "20260801", "3f7824e8-8819-4e3f-8636-19114f2a92ff"),
        rec("A_20260803", "20260803", "7a83314b-69b3-4a9e-be08-5866ed9ca81b"),
        rec("A_20260805", "20260805", "ee344ad1-24f5-4111-8ff0-c5835d8a5cba"),
        rec("A_20260807", "20260807", "14bd7ff3-4652-4879-8515-1d2dbb908fc9"),
        rec("A_20260809", "20260809", "be4b8776-fd6f-45e3-bd7c-70145018964b"),
    ],
}


def main():
    bid = sys.argv[1] if len(sys.argv) > 1 else "a1"
    recs = BATCHES.get(bid, [])
    stage = os.path.join(ROOT, "staging", f"{bid}.json")
    os.makedirs(os.path.dirname(stage), exist_ok=True)
    json.dump(recs, open(stage, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("staged", stage, len(recs))
    if "--persist" in sys.argv:
        r = subprocess.run([PY, os.path.join(ROOT, "_r6_persist.py"), stage], capture_output=True, text=True)
        print(r.stdout.strip())
        if r.returncode != 0:
            print("STDERR:", r.stderr[-600:])


if __name__ == "__main__":
    main()
