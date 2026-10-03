# -*- coding: utf-8 -*-
"""V1-R5.1 — PARENT-AUTHORITATIVE PERSISTENCE PROTOCOL (§3, §4, §5, §6, §7).

The parent (not the child) is the writer of record:
  SUBAGENT -> RETURN PAYLOAD -> SCHEMA VALIDATION -> ATOMIC WRITE (.tmp+fsync+os.replace)
  -> READ-BACK -> SHA256 -> LEDGER (dedup by sample_id)

Usage:  python _r51_persist.py <staging_json>
Staging JSON = [{"run_id","sample_id","agent_role","prompt_hash","context_hash","raw_text","attempt"}, ...]
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
ROOT = os.path.join(BASE, "v1_r5_1_subagent_persistence")
LEDGER = os.path.join(ROOT, "ledger", "persistence_ledger.jsonl")
PAYLOADS = os.path.join(ROOT, "payloads")
NOW = datetime.now(timezone.utc).isoformat()
REQUIRED_CHECKS = ["RETURN", "SCHEMA", "WRITE", "READBACK", "HASH"]
MIN_PROBE_FIELDS = ["sample_id", "agent_role"]


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def ledger_last():
    prev, seq = "0" * 64, 0
    if os.path.exists(LEDGER):
        for line in open(LEDGER, encoding="utf-8"):
            line = line.strip()
            if line:
                prev = json.loads(line)["current_hash"]; seq += 1
    return prev, seq


def ledger_append(entries):
    prev, seq = ledger_last()
    with open(LEDGER, "a", encoding="utf-8", newline="\n") as fh:
        for e in entries:
            seq += 1
            rec = {"seq": seq, "ts_utc": NOW, **e, "previous_hash": prev}
            rec["current_hash"] = sha_obj({k: v for k, v in rec.items() if k != "current_hash"})
            prev = rec["current_hash"]
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return seq


def accepted_sample_ids():
    s = set()
    if os.path.exists(LEDGER):
        for line in open(LEDGER, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
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
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)          # atomic rename
    return sha_obj(obj)            # CANONICAL payload hash (same basis as verification)


def persist(records, tag="batch"):
    accepted = accepted_sample_ids()
    results, ledger_entries = [], []
    for r in records:
        sid = r.get("sample_id") or "UNKNOWN"
        step = {"sample_id": sid, "run_id": r.get("run_id"), "agent_role": r.get("agent_role"),
                 "attempt": r.get("attempt", 1), "checks": {k: False for k in REQUIRED_CHECKS},
                 "error_type": None, "error_detail": None,
                 "prompt_hash": r.get("prompt_hash"), "context_hash": r.get("context_hash"),
                 "created_at": NOW, "raw_returned": isinstance(r.get("raw_text"), str) and len(r["raw_text"].strip()) > 0}
        # RETURN
        step["checks"]["RETURN"] = bool(step["raw_returned"])
        payload, err = extract_json(r.get("raw_text"))
        # SCHEMA
        if payload is not None and isinstance(payload, dict) and all(k in payload for k in MIN_PROBE_FIELDS):
            step["checks"]["SCHEMA"] = True
        elif payload is not None:
            err = err or "SCHEMA_MISSING_FIELDS"
        if not step["checks"]["RETURN"]:
            step["error_type"] = "SUBAGENT_PERSISTENCE_FAILURE"; step["error_detail"] = "RETURN_FAILED"
        elif not step["checks"]["SCHEMA"]:
            step["error_type"] = "SUBAGENT_PERSISTENCE_FAILURE"; step["error_detail"] = err or "SCHEMA_FAILED"
        payload_hash = sha_obj(payload) if payload is not None else None
        step["payload_hash"] = payload_hash
        # DUPLICATE CHECK (§7)
        duplicate = sid in accepted
        if duplicate:
            step["duplicate"] = True
            step["accepted"] = False
            step["error_type"] = "DUPLICATE_REJECTED"
            step["error_detail"] = "sample_id already ACCEPTED; not chained again"
            results.append(step)
            ledger_entries.append({"event": "duplicate_rejected", "sample_id": sid, "run_id": r.get("run_id"),
                                    "attempt": step["attempt"], "payload_hash": payload_hash})
            continue
        # WRITE (parent atomic write) + READBACK + HASH
        if step["checks"]["RETURN"] and step["checks"]["SCHEMA"]:
            path = os.path.join(PAYLOADS, f"{sid}.json")
            try:
                wh = atomic_write(path, payload)
                step["checks"]["WRITE"] = True
            except Exception as e:  # noqa: BLE001
                wh = None
                step["error_type"] = "SUBAGENT_PERSISTENCE_FAILURE"; step["error_detail"] = f"WRITE_FAILED:{str(e)[:60]}"
            if step["checks"]["WRITE"]:
                try:
                    back = json.load(open(path, encoding="utf-8"))
                    step["checks"]["READBACK"] = (back == payload)
                except Exception as e:  # noqa: BLE001
                    back = None
                    step["checks"]["READBACK"] = False
                    step["error_detail"] = f"READBACK_FAILED:{str(e)[:60]}"
                step["checks"]["HASH"] = bool(step["checks"]["READBACK"] and back is not None and wh == sha_obj(back))
            step["accepted"] = all(step["checks"][k] for k in REQUIRED_CHECKS)
            if not step["accepted"] and not step["error_type"]:
                failed = [k for k in REQUIRED_CHECKS if not step["checks"][k]]
                step["error_type"] = "SUBAGENT_PERSISTENCE_FAILURE"
                step["error_detail"] = "CHECKS_FAILED:" + ",".join(failed)
        else:
            step["accepted"] = False
            if not step["error_type"]:
                failed = [k for k in REQUIRED_CHECKS if not step["checks"][k]]
                step["error_type"] = "SUBAGENT_PERSISTENCE_FAILURE"
                step["error_detail"] = "CHECKS_FAILED:" + ",".join(failed)
        if step.get("accepted"):
            accepted.add(sid)
            ledger_entries.append({"event": "accepted", "sample_id": sid, "run_id": r.get("run_id"),
                                    "agent_role": step["agent_role"], "attempt": step["attempt"],
                                    "prompt_hash": step["prompt_hash"], "context_hash": step["context_hash"],
                                    "payload_hash": step["payload_hash"]})
        else:
            ledger_entries.append({"event": "failure", "sample_id": sid, "run_id": r.get("run_id"),
                                    "attempt": step["attempt"], "error_type": step["error_type"],
                                    "error_detail": step["error_detail"]})
        results.append(step)
    n = ledger_append(ledger_entries)
    return results, n


def main():
    staging = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "staging", "batch.json")
    records = json.load(open(staging, encoding="utf-8"))
    results, ledger_n = persist(records, tag=os.path.basename(staging))
    ok = sum(1 for r in results if r.get("accepted"))
    fails = [r for r in results if not r.get("accepted")]
    out = {"ts_utc": NOW, "staging": os.path.basename(staging), "n": len(results), "accepted": ok,
            "failed": len(fails), "ledger_entries_total": ledger_n, "results": results}
    p = os.path.join(ROOT, "audit", f"persist_{os.path.basename(staging).replace('.json','')}.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(out, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps({"n": len(results), "accepted": ok, "failed": len(fails), "ledger": ledger_n}, ensure_ascii=False))
    for r in fails:
        print("FAIL:", r["sample_id"], r["error_type"], r["error_detail"])


if __name__ == "__main__":
    main()
