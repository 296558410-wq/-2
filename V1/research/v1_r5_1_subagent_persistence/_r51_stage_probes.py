# -*- coding: utf-8 -*-
"""V1-R5.1 — stage the three fault-localisation probe payloads and persist them via the parent protocol."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

ROOT = r"C:\AIQuant\research\hermes\trader_v1\v1_r5_1_subagent_persistence"
PY = r"C:\AIQuant\.venv\Scripts\python.exe"

PROBE_TEMPLATE_HASH = hashlib.sha256(b"v1r5.1-probe:return-only-tiny-json").hexdigest()

PROBES = [
    {"run_id": "2e3bc505-e9a3-4f7f-8c5f-dfaa2def90a6", "sample_id": "P1_HERMES_A", "agent_role": "HERMES_A",
     "context_hash": "CTX_20260720T120000Z", "attempt": 1, "prompt_hash": PROBE_TEMPLATE_HASH,
     "raw_text": '{"sample_id":"P1_HERMES_A","agent_role":"HERMES_A","context_hash":"CTX_20260720T120000Z","observations":["M1 uptrend, range expanding, close 4025.185","Price inside swing low 4021.065, 0.12 ATR","COMPRESSION state, ACCEPTANCE event, dwell 1"],"confidence":0.42,"schema_version":"v1r5.1-probe"}'},
    {"run_id": "c385157c-87cc-4d2c-a097-f582726aa93f", "sample_id": "P2_HERMES_B", "agent_role": "HERMES_B",
     "context_hash": "CTX_20260726T120000Z", "attempt": 1, "prompt_hash": PROBE_TEMPLATE_HASH,
     "raw_text": '{"sample_id":"P2_HERMES_B","agent_role":"HERMES_B","context_hash":"CTX_20260726T120000Z","counter_observation":"MTF agreement CONFLICT; cross-market absent; analog similarity coarse","confidence":0.37,"schema_version":"v1r5.1-probe"}'},
    {"run_id": "e32323d7-c64d-4e16-9f32-1e74673153b9", "sample_id": "P3_POST_OUTCOME", "agent_role": "POST_OUTCOME",
     "context_hash": "CTX_20260801T120000Z", "attempt": 1, "prompt_hash": PROBE_TEMPLATE_HASH,
     "raw_text": '{"sample_id":"P3_POST_OUTCOME","agent_role":"POST_OUTCOME","context_hash":"CTX_20260801T120000Z","outcome_alignment_verdict":"UNSCORABLE","reason":"probe: outcome withheld","confidence":0.5,"schema_version":"v1r5.1-probe"}'},
]


def main():
    stage = os.path.join(ROOT, "staging", "probes.json")
    os.makedirs(os.path.dirname(stage), exist_ok=True)
    json.dump(PROBES, open(stage, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("staged:", stage, len(PROBES))
    r = subprocess.run([PY, os.path.join(ROOT, "_r51_persist.py"), stage], capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print("STDERR:", r.stderr[-800:])


if __name__ == "__main__":
    main()
