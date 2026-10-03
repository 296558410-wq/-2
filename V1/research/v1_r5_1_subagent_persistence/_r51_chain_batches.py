# -*- coding: utf-8 -*-
"""V1-R5.1 — chain-test batches. Payloads are RETURNED by the subagents and persisted by the PARENT.

Run:  python _r51_chain_batches.py <batch_id>
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

ROOT = r"C:\AIQuant\research\hermes\trader_v1\v1_r5_1_subagent_persistence"
PY = r"C:\AIQuant\.venv\Scripts\python.exe"
CHAIN_PROMPT_HASH = hashlib.sha256(b"v1r5.1-chain:return-only-tiny-json").hexdigest()


def rec(run_id, sid, role, ctx, note):
    payload = {"sample_id": sid, "agent_role": role, "context_hash": ctx, "note": note,
                "confidence": 0.4, "schema_version": "v1r5.1-chain"}
    return {"run_id": run_id, "sample_id": sid, "agent_role": role, "context_hash": ctx, "attempt": 1,
             "prompt_hash": CHAIN_PROMPT_HASH, "raw_text": json.dumps(payload, ensure_ascii=False)}


BATCHES = {
    "chain1": [
        rec("755d1802-e9dd-4c02-99ff-69de22ba3ada", "C01", "HERMES_A", "CTX_20260720T120000Z", "COMPRESSION, ACCEPTANCE, XAUUSD 4025.185"),
        rec("6f5c111a-9670-4517-925b-360c7f290c82", "C02", "HERMES_A", "CTX_20260726T120000Z", "XAUUSD COMPRESSION ACCEPTANCE"),
        rec("efbdd06b-fd05-4305-b536-e9fbacc691d6", "C03", "HERMES_B", "CTX_20260801T120000Z", "XAUUSD ROTATION acceptance near swing low"),
        rec("e003542a-21b8-4a5f-8e78-45b473e337fd", "C04", "HERMES_B", "CTX_20260807T120000Z", "XAUUSD EXPANSION ACCEPTANCE swing high inside"),
        rec("8a4a05f4-4bbc-41fa-a91e-c94333db70ef", "C05", "POST_OUTCOME", "CTX_20260813T120000Z", "COMPRESSION state, VOL_CONTRACTION, swing low proximity"),
    ],
    "chain2": [
        rec("aff3d019-b735-42b6-82b3-256889b2ca4a", "C06", "POST_OUTCOME", "CTX_20260822T120000Z", "COMPRESSION state, VOL_CONTRACTION event, XAUUSD 4602"),
        rec("9c871d59-5605-4dda-90b3-754254faa476", "C07", "HERMES_A", "CTX_20260828T120000Z", "XAUUSD REJECTION at swing low, M1 range expanding"),
        rec("af95b328-790e-4f88-8477-c9a5954222ab", "C08", "HERMES_A", "CTX_20260903T120000Z", "ROTATION state, dwell 11 bars, level inside"),
        rec("5655ccd0-bb6c-4462-992e-a75c4cfa951c", "C09", "HERMES_B", "CTX_20260912T120000Z", "XAUUSD COMPRESSION, VOL_CONTRACTION, near swing high"),
        rec("4f04f9d8-f329-4f87-8ccb-0b6953d47e6c", "C10", "HERMES_B", "CTX_20260720T120000Z", "XAUUSD COMPRESSION ACCEPTANCE near swing low"),
    ],
    "chain3": [
        rec("d80a5c05-4c11-48c8-8184-e642dcab124a", "C11", "POST_OUTCOME", "CTX_20260726T120000Z", "COMPRESSION at swing low 4048.995 XAUUSD"),
        rec("4279b812-ad35-4982-800c-2a98a2a05c39", "C12", "HERMES_A", "CTX_20260801T120000Z", "XAUUSD ROTATION ACCEPTANCE M1 down"),
        rec("900b5cd7-fbfe-4ab1-b4af-3fd04de35d6c", "C13", "HERMES_B", "CTX_20260807T120000Z", "XAUUSD EXPANSION ACCEPTANCE M1-M15 bullish"),
        rec("2f0f4da0-0b08-45cb-a85e-953f609ae9d9", "C14", "HERMES_A", "CTX_20260813T120000Z", "XAUUSD COMPRESSION, VOL_CONTRACTION, price inside swing low"),
        rec("1456e91b-96c8-42a4-b251-13ff8ba42341", "C15", "HERMES_B", "CTX_20260822T120000Z", "XAUUSD COMPRESSION, price inside swing high, trend conflict"),
    ],
    "chain4": [
        rec("1f9eff70-f362-42e1-9db9-0c3f29b10157", "C16", "HERMES_A", "CTX_20260828T120000Z", "frozen REJECTION, NO_DEFINED_STATE, dwell 16"),
        rec("dbebb617-7105-4ea3-83af-be583937fdc2", "C17", "HERMES_B", "CTX_20260903T120000Z", "XAUUSD ROTATION dwell 11 bars"),
        rec("610402d4-26d3-4880-b340-cf08e06335bd", "C18", "POST_OUTCOME", "CTX_20260912T120000Z", "COMPRESSION state, VOL_CONTRACTION event, XAUUSD"),
        rec("97cacfd7-d92f-4252-b0ae-6c61da8613a3", "C19", "HERMES_B", "CTX_20260801T120000Z", "ROTATION ACCEPTANCE XAUUSD multi-timeframe conflict inside swing level"),
        rec("1cf9167b-3f99-46b3-ba43-218d56c13fa8", "C20", "HERMES_A", "CTX_20260813T120000Z", "XAUUSD COMPRESSION, VOL_CONTRACTION, level inside"),
    ],
}


def main():
    bid = sys.argv[1] if len(sys.argv) > 1 else "chain1"
    recs = BATCHES.get(bid)
    if not recs:
        print("no records for batch", bid, "| known:", [k for k, v in BATCHES.items() if v])
        return
    stage = os.path.join(ROOT, "staging", f"{bid}.json")
    os.makedirs(os.path.dirname(stage), exist_ok=True)
    json.dump(recs, open(stage, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    r = subprocess.run([PY, os.path.join(ROOT, "_r51_persist.py"), stage], capture_output=True, text=True)
    print(bid, r.stdout.strip())
    if r.returncode != 0:
        print("STDERR:", r.stderr[-600:])


if __name__ == "__main__":
    main()
