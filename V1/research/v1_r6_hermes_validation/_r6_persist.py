# -*- coding: utf-8 -*-
"""V1-R6 — self-contained parent-authoritative persistence (same protocol as R5.1, R6 schemas).

R5.1 is IMMUTABLE, so this is a separate implementation with role-specific schema validation.
  SUBAGENT -> RETURN PAYLOAD -> SCHEMA -> ATOMIC WRITE (.tmp+fsync+os.replace) -> READ-BACK -> SHA256 -> LEDGER
Failures are recorded and stay in the denominator. Duplicates are rejected, never chained twice.

Run:  python _r6_persist.py <staging_json>
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

BASE = r"C:\AIQuant\research\hermes\trader_v1"
ROOT = os.path.join(BASE, "v1_r6_hermes_validation")
LEDGER = os.path.join(ROOT, "ledger", "v1_r6_ledger.jsonl")
PAYLOADS = os.path.join(ROOT, "payloads")
NOW = datetime.now(timezone.utc).isoformat()
CHECKS = ["RETURN", "SCHEMA", "WRITE", "READBACK", "HASH"]

A_KEYS = ["sample_id", "observations", "what_i_know", "what_i_do_not_know", "evidence", "counter_evidence",
           "possible_mechanisms", "primary_scenario", "alternative_scenario", "expected_transition",
           "direction_bias", "time_horizon", "evidence_strength", "confidence", "uncertainty",
           "confidence_reason", "uncertainty_reason", "invalidation", "change_my_mind", "abstain", "questions"]
BLIND_KEYS = ["audit_id", "current_state", "structure", "mechanism", "primary_scenario", "alternative_scenario",
               "expected_transition", "direction", "horizon", "confidence", "counter_evidence", "invalidation"]
ADV_KEYS = ["audit_id", "overall_verdict", "focus_verdicts", "evidence"]
POST_KEYS = ["audit_id", "outcome_alignment_verdict"]
REQUIRED = {"HERMES_A": A_KEYS, "HERMES_B_BLIND": BLIND_KEYS, "HERMES_B_ADV": ADV_KEYS, "POST_OUTCOME": POST_KEYS}


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


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
    return seq


def accepted_ids():
    s = set()
    if os.path.exists(LEDGER):
        for line in open(LEDGER, encoding="utf-8"):
            line = line.strip()
            if line:
                e = json.loads(line)
                if e.get("event") == "accepted":
                    s.add(e.get("sample_id"))
    return s


def extract_json(raw):
    if not isinstance(raw, str) or not raw.strip():
        return None, "EMPTY_RESPONSE"
    t = raw.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    try:
        return json.loads(t), None
    except Exception:  # noqa: BLE001
        m = re.search(r"\{.*\}", t, re.S)
        if m:
            try:
                return json.loads(m.group(0)), None
            except Exception as e2:  # noqa: BLE001
                return None, f"MALFORMED_JSON:{str(e2)[:60]}"
        return None, "MALFORMED_JSON:no_object"


def atomic_write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    data = json.dumps(obj, indent=1, ensure_ascii=False).encode("utf-8")
    with open(tmp, "wb") as fh:
        fh.write(data); fh.flush(); os.fsync(fh.fileno())
    os.replace(tmp, path)
    return sha_obj(obj)


def persist(records, tag="batch"):
    acc = accepted_ids()
    results, entries = [], []
    for r in records:
        sid = r.get("sample_id") or "UNKNOWN"
        role = r.get("agent_role", "HERMES_A")
        req = r.get("schema_keys") or REQUIRED.get(role, A_KEYS)
        st = {"sample_id": sid, "run_id": r.get("run_id"), "agent_role": role, "attempt": r.get("attempt", 1),
               "checks": {k: False for k in CHECKS}, "error_type": None, "error_detail": None,
               "prompt_hash": r.get("prompt_hash"), "context_hash": r.get("context_hash"), "created_at": NOW}
        st["checks"]["RETURN"] = isinstance(r.get("raw_text"), str) and bool(r["raw_text"].strip())
        payload, err = extract_json(r.get("raw_text"))
        missing = [k for k in req if not isinstance(payload, dict) or k not in payload]
        st["checks"]["SCHEMA"] = bool(payload is not None and not missing)
        if not st["checks"]["RETURN"]:
            st["error_type"], st["error_detail"] = "SUBAGENT_PERSISTENCE_FAILURE", "RETURN_FAILED"
        elif not st["checks"]["SCHEMA"]:
            st["error_type"], st["error_detail"] = "SUBAGENT_PERSISTENCE_FAILURE", err or ("SCHEMA_MISSING:" + ",".join(missing[:5]))
        st["payload_hash"] = sha_obj(payload) if payload is not None else None
        if sid in acc:
            st["duplicate"] = True
            st["error_type"] = "DUPLICATE_REJECTED"
            st["error_detail"] = "already ACCEPTED"
            results.append(st)
            entries.append({"event": "duplicate_rejected", "sample_id": sid, "attempt": st["attempt"]})
            continue
        if st["checks"]["RETURN"] and st["checks"]["SCHEMA"]:
            path = os.path.join(PAYLOADS, f"{sid}.json")
            try:
                wh = atomic_write(path, payload); st["checks"]["WRITE"] = True
            except Exception as e:  # noqa: BLE001
                wh = None; st["error_type"], st["error_detail"] = "SUBAGENT_PERSISTENCE_FAILURE", f"WRITE_FAILED:{str(e)[:60]}"
            if st["checks"]["WRITE"]:
                try:
                    back = json.load(open(path, encoding="utf-8"))
                    st["checks"]["READBACK"] = (back == payload)
                except Exception as e:  # noqa: BLE001
                    back = None; st["checks"]["READBACK"] = False
                    st["error_detail"] = f"READBACK_FAILED:{str(e)[:60]}"
                st["checks"]["HASH"] = bool(st["checks"]["READBACK"] and back is not None and wh == sha_obj(back))
        st["accepted"] = all(st["checks"][k] for k in CHECKS)
        if not st["accepted"] and not st["error_type"]:
            failed = [k for k in CHECKS if not st["checks"][k]]
            st["error_type"], st["error_detail"] = "SUBAGENT_PERSISTENCE_FAILURE", "CHECKS_FAILED:" + ",".join(failed)
        if st["accepted"]:
            acc.add(sid)
            entries.append({"event": "accepted", "sample_id": sid, "agent_role": role, "attempt": st["attempt"],
                             "prompt_hash": st["prompt_hash"], "context_hash": st["context_hash"], "payload_hash": st["payload_hash"]})
        else:
            entries.append({"event": "failure", "sample_id": sid, "agent_role": role, "attempt": st["attempt"],
                             "error_type": st["error_type"], "error_detail": st["error_detail"]})
        results.append(st)
    n = ledger_append(entries)
    return results, n


def main():
    stage = sys.argv[1]
    records = json.load(open(stage, encoding="utf-8"))
    results, n = persist(records, tag=os.path.basename(stage))
    ok = sum(1 for r in results if r.get("accepted"))
    fails = [r for r in results if not r.get("accepted")]
    out = {"ts_utc": NOW, "staging": os.path.basename(stage), "n": len(results), "accepted": ok,
            "failed": len(fails), "ledger_entries_total": n, "results": results}
    p = os.path.join(ROOT, "audit", f"persist_{os.path.basename(stage).replace('.json','')}.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(out, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps({"batch": os.path.basename(stage), "n": len(results), "accepted": ok, "failed": len(fails), "ledger": n}, ensure_ascii=False))
    for r in fails:
        print("FAIL:", r["sample_id"], r["error_type"], r["error_detail"])


if __name__ == "__main__":
    main()
