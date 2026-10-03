# -*- coding: utf-8 -*-
"""V1-R5.1 SUBAGENT PERSISTENCE REPAIR — SCAFFOLD + FREEZE + PROTOCOL REGISTRY.

Freezes R3/R4/R5 as IMMUTABLE, defines the parent-authoritative persistence protocol, and creates the
append-only sha256-chained persistence ledger. Adds ONLY v1_r5_1_subagent_persistence/.
No prediction research. No orders/broker.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

REPO = r"C:\AIQuant"
BASE = os.path.join(REPO, "research", "hermes", "trader_v1")
ROOT = os.path.join(BASE, "v1_r5_1_subagent_persistence")
FROZEN = {"R3": os.path.join(BASE, "v1_r3_hermes_market_forecast"),
           "R4": os.path.join(BASE, "v1_r4_hermes_audit"),
           "R5": os.path.join(BASE, "v1_r5_hermes_forecast_discipline")}
LEDGER = os.path.join(ROOT, "ledger", "persistence_ledger.jsonl")
NOW = datetime.now(timezone.utc).isoformat()
DIRS = ["registry", "reports", "tests", "audit", "ledger", "staging", "payloads", "raw", "fault_injection"]

REQUIRED_FIELDS = ["run_id", "sample_id", "agent_role", "prompt_hash", "context_hash", "created_at",
                    "payload", "payload_hash", "write_status", "readback_status"]
MAX_ATTEMPTS = 3
REQUIRED_CHECKS = ["RETURN", "SCHEMA", "WRITE", "READBACK", "HASH"]
INJECTIONS = ["empty_response", "malformed_response", "write_failure", "partial_write",
              "duplicate_response", "timeout", "retry", "late_response"]


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def wjson(rel, o):
    p = os.path.join(ROOT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, default=str)
    return p


def wtext(rel, s):
    p = os.path.join(ROOT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(s)
    return p


def ledger_append(entries):
    prev, seq = "0" * 64, 0
    if os.path.exists(LEDGER):
        for line in open(LEDGER, encoding="utf-8"):
            line = line.strip()
            if line:
                prev = json.loads(line)["current_hash"]; seq += 1
    with open(LEDGER, "a", encoding="utf-8", newline="\n") as fh:
        for e in entries:
            seq += 1
            rec = {"seq": seq, "ts_utc": NOW, **e, "previous_hash": prev}
            rec["current_hash"] = sha_obj({k: v for k, v in rec.items() if k != "current_hash"})
            prev = rec["current_hash"]
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def baseline(root):
    files = {}
    for dp, _, fs in os.walk(root):
        for f in fs:
            fp = os.path.join(dp, f)
            if os.path.isfile(fp):
                files[os.path.relpath(fp, root).replace("\\", "/")] = sha_file(fp)
    return {"file_count": len(files), "baseline_hash": sha_obj(files), "files": files}


def main():
    for d in DIRS:
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)
    frozen = {k: baseline(v) for k, v in FROZEN.items()}
    wjson("registry/FROZEN_BASELINES.json", {"ts_utc": NOW, "frozen": frozen,
                                              "note": "R3/R4/R5 must stay byte-identical during R5.1"})
    for k, v in frozen.items():
        wjson(f"registry/{k}_IMMUTABILITY_BASELINE.json", v)
    proto = {
        "task": "V1_R5_1_SUBAGENT_PERSISTENCE_REPAIR", "registry_id": "v1r5.1-persistence-registry-r1",
        "frozen": True, "frozen_at_utc": NOW,
        "principle": "A subagent writing a file is NOT the success condition. Success = the PARENT received the payload, validated the schema, wrote atomically, read back, hashed, and chained it.",
        "flow": ["SUBAGENT", "RETURN_PAYLOAD", "PARENT_VALIDATOR", "SCHEMA_VALIDATION", "ATOMIC_WRITE",
                  "READ_BACK", "SHA256", "LEDGER"],
        "required_fields": REQUIRED_FIELDS,
        "required_checks": REQUIRED_CHECKS,
        "max_attempts": MAX_ATTEMPTS,
        "atomic_write": {"steps": [".tmp write", "fsync", "os.replace (atomic rename)", "read-back", "sha256"],
                          "forbidden": ["direct overwrite of the final file", "silent skip on failure"]},
        "failure_record": {"error_type": "SUBAGENT_PERSISTENCE_FAILURE",
                            "must_keep": ["sample_id", "attempt", "error_type", "timestamp"],
                            "rule": "failed samples stay in the denominator; NEVER silently dropped"},
        "duplicate_policy": "each sample_id may have at most one ACCEPTED record; later duplicates are recorded as DUPLICATE_REJECTED and never chained twice",
        "completion_gate": {"consecutive_passes_required": 20,
                              "all_checks": REQUIRED_CHECKS,
                              "must_be_zero": ["DUPLICATE_ACCEPTED", "SILENT_DROP", "CORRUPTED_PAYLOAD"]},
        "replay": "same input must reproduce payload_hash, schema_result and persistence_result",
        "hard_safety": {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
                         "BOUNDARY_VIOLATION": 0, "MT5_CALLS": 0},
        "forbidden": ["modify R3", "modify R4", "modify R5", "re-evaluate prediction capability",
                        "modify Hermes prompts", "add samples then claim capability", "enter R6"],
    }
    proto["registry_hash"] = sha_obj({k: v for k, v in proto.items() if k != "registry_hash"})
    wjson("registry/v1_r5_1_registry.json", proto)
    ledger_append([{"event": "registry_frozen", "registry_hash": proto["registry_hash"],
                     "frozen_hashes": {k: v["baseline_hash"] for k, v in frozen.items()}}])
    print("ROOT:", ROOT)
    print("registry_hash:", proto["registry_hash"][:16])
    for k, v in frozen.items():
        print(f"  {k} frozen: {v['baseline_hash'][:16]} ({v['file_count']} files)")


if __name__ == "__main__":
    main()
