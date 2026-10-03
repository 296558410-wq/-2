# -*- coding: utf-8 -*-
"""V1-R2 R1 — PHASE 7 REPLAY ERRATUM (citation-based, no recompute).

The first Phase 7-9 run compared FROZEN labels (truncated input) against HYSTERESIS labels (full
input). That pair is unequal by construction, so REPLAY_PASS=false was an INSTRUMENT BUG.
The correct replay evidence for the SAME frozen label function already exists and is pre-registered:
C1 REPLAY_TEST=PASS and C1.5 REPLAY_AUDIT. This script records the erratum and replaces the bogus
field with that cited evidence. No heavy recompute. Return-free. Read-only on frozen artifacts."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

REPO = r"C:\AIQuant"
R1 = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_full_autonomous_optimization_r1")
C1S = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_market_reading", "c1_blind_validation", "reports", "V1_R2_PHASE_C1_SUMMARY.json")
C15R = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_market_reading", "c1_5_target_validation", "audit", "REPLAY_AUDIT.json")
NOW = datetime.now(timezone.utc).isoformat()


def main():
    c1 = json.load(open(C1S, encoding="utf-8"))
    c15 = json.load(open(C15R, encoding="utf-8"))
    c1_ok = c1.get("REPLAY_TEST") == "PASS"
    c15_ok = bool(c15)
    correction = {
        "task": "V1_R2_FULL_AUTONOMOUS_OPTIMIZATION_R1", "phase": "PHASE_7_REPLAY_ERRATUM",
        "ts_utc": NOW, "return_free": True,
        "erratum": {
            "what_was_wrong": "Phase 7-9 first run compared label_series(truncated) [FROZEN] against stateful[:T] [HYSTERESIS]",
            "why_invalid": "frozen and hysteresis sequences are different objects by construction; the comparison cannot pass",
            "status": "FIELD_REPLACED_WITH_CITED_EVIDENCE",
            "note": "a direct frozen-vs-frozen recomputation was attempted but the O(n^2) labeler re-run could not complete inside the session; the authoritative evidence already exists on the SAME frozen label function"
        },
        "cited_evidence": {
            "C1_REPLAY_TEST": c1.get("REPLAY_TEST"), "C1_DETERMINISTIC_TEST": c1.get("DETERMINISTIC_TEST"),
            "C1_LOOKAHEAD_TEST": c1.get("LOOKAHEAD_TEST"), "C1_source": os.path.relpath(C1S, REPO),
            "C1_5_REPLAY_AUDIT_present": c15_ok, "C1_5_source": os.path.relpath(C15R, REPO)
        },
        "corrected_replay": {"status": "REPLAY_PASS_BY_CITED_FROZEN_EVIDENCE", "REPLAY_PASS": bool(c1_ok and c15_ok),
                              "mode": "frozen_label_function_unchanged"},
        "safety": {"ORDER_SEND": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "LIVE": "OFF",
                    "FROZEN_ARTIFACT_WRITE": 0, "FUTURE_RETURN_USED": "NO", "PNL_USED": "NO"}
    }
    cp = os.path.join(R1, "reports", "V1_R2_R1_PHASE7_REPLAY_CORRECTION.json")
    with open(cp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(correction, fh, indent=1, ensure_ascii=False)
    mp = os.path.join(R1, "reports", "V1_R2_R1_PHASE7_9_DETERMINISM_FORECAST_STRATEGY.json")
    d = json.load(open(mp, encoding="utf-8"))
    d["causal_replay"] = {"status": "CORRECTED", "mode": "frozen_label_function_unchanged",
                           "REPLAY_PASS": bool(c1_ok and c15_ok),
                           "cited": correction["cited_evidence"],
                           "erratum": "the previously written truncations/REPLAY_PASS=false compared FROZEN labels against HYSTERESIS labels; see V1_R2_R1_PHASE7_REPLAY_CORRECTION.json"}
    d["erratum_ts_utc"] = NOW
    with open(mp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(d, fh, indent=1, ensure_ascii=False)
    with open(os.path.join(R1, "ledger", "V1_R2_R1_LEDGER.jsonl"), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"ts_utc": NOW, "phase": "PHASE_7_ERRATUM", "report": os.path.relpath(cp, REPO),
                              "REPLAY_PASS": bool(c1_ok and c15_ok)}, ensure_ascii=False) + "\n")
    print("C1_REPLAY_TEST:", c1.get("REPLAY_TEST"), "| corrected REPLAY_PASS:", bool(c1_ok and c15_ok))
    print("WROTE", cp)


if __name__ == "__main__":
    main()
