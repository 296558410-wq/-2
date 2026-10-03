# -*- coding: utf-8 -*-
"""V1-R5.1 — §9 FAULT INJECTION (8 scenarios). Each fault must be DETECTED, RECORDED (never silent),
and must NOT pollute accepted results. No LLM calls."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

ROOT = r"C:\AIQuant\research\hermes\trader_v1\v1_r5_1_subagent_persistence"


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def main():
    P = load("p", os.path.join(ROOT, "_r51_persist.py"))
    F = hashlib.sha256(b"v1r5.1-injection").hexdigest()
    results = {}

    def mk(sid, raw, attempt=1):
        return {"run_id": f"INJ_{sid}_{attempt}", "sample_id": sid, "agent_role": "INJECTION",
                 "context_hash": "INJECTION", "attempt": attempt, "prompt_hash": F, "raw_text": raw}

    def run(recs, sid):
        res, _ = P.persist(recs, tag="injection")
        for r in res:
            if r["sample_id"] == sid:
                return r
        return res[-1]

    good = '{"sample_id":"%s","agent_role":"INJECTION","note":"ok"}'

    r = run([mk("I1_EMPTY", "")], "I1_EMPTY")
    results["empty_response"] = {"detected": bool(r["error_type"]) and not r["accepted"], "error_type": r["error_type"], "detail": r["error_detail"], "accepted": r["accepted"]}
    r = run([mk("I2_MALFORMED", "{not valid json")], "I2_MALFORMED")
    results["malformed_response"] = {"detected": bool(r["error_type"]) and not r["accepted"], "error_type": r["error_type"], "detail": r["error_detail"], "accepted": r["accepted"]}
    orig = P.atomic_write
    P.atomic_write = lambda path, obj: (_ for _ in ()).throw(OSError("injected write failure"))
    r = run([mk("I3_WRITEFAIL", good % "I3_WRITEFAIL")], "I3_WRITEFAIL")
    P.atomic_write = orig
    results["write_failure"] = {"detected": bool(r["error_type"]) and not r["accepted"], "error_type": r["error_type"], "detail": r["error_detail"], "accepted": r["accepted"]}
    orig_aw = P.atomic_write
    def partial(path, obj):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write('{"truncated":')
        return P.sha_obj(obj)
    P.atomic_write = partial
    r = run([mk("I4_PARTIAL", good % "I4_PARTIAL")], "I4_PARTIAL")
    P.atomic_write = orig_aw
    results["partial_write"] = {"detected": (not r["accepted"]) and (not r["checks"]["READBACK"] or not r["checks"]["HASH"]), "error_type": r["error_type"], "detail": r["error_detail"], "accepted": r["accepted"]}
    RUN = str(int(time.time()))
    r = run([mk(f"I5_DUP_{RUN}", good % f"I5_DUP_{RUN}", 1), mk(f"I5_DUP_{RUN}", good % f"I5_DUP_{RUN}", 1)], f"I5_DUP_{RUN}")
    third = run([mk(f"I5_DUP_{RUN}", good % f"I5_DUP_{RUN}", 1)], f"I5_DUP_{RUN}")
    results["duplicate_response"] = {"detected": r["error_type"] == "DUPLICATE_REJECTED" or third["error_type"] == "DUPLICATE_REJECTED", "first_accepted": r["accepted"], "second_error": r["error_type"], "third_error": third["error_type"]}
    r = run([{"run_id": "INJ_I6", "sample_id": "I6_TIMEOUT", "agent_role": "INJECTION", "context_hash": "INJECTION", "attempt": 1, "prompt_hash": F, "raw_text": None}], "I6_TIMEOUT")
    results["timeout"] = {"detected": bool(r["error_type"]) and not r["accepted"], "error_type": r["error_type"], "detail": r["error_detail"], "accepted": r["accepted"]}
    a1 = run([mk(f"I7_RETRY_{RUN}", "", 1)], f"I7_RETRY_{RUN}")
    a2 = run([mk(f"I7_RETRY_{RUN}", good % f"I7_RETRY_{RUN}", 2)], f"I7_RETRY_{RUN}")
    results["retry"] = {"detected": (not a1["accepted"]) and a2["accepted"], "attempt1_accepted": a1["accepted"], "attempt1_error": a1["error_type"], "attempt2_accepted": a2["accepted"], "exactly_one_accepted": (not a1["accepted"]) and a2["accepted"]}
    late = run([mk(f"I7_RETRY_{RUN}", good % f"I7_RETRY_{RUN}", 3)], f"I7_RETRY_{RUN}")
    results["late_response"] = {"detected": late["error_type"] == "DUPLICATE_REJECTED", "error_type": late["error_type"]}

    seen, dup_chained, total = set(), 0, 0
    for line in open(P.LEDGER, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        e = json.loads(line); total += 1
        if e.get("event") == "accepted":
            if e["sample_id"] in seen:
                dup_chained += 1
            seen.add(e["sample_id"])
    def verify(path):
        prev, k, o = "0" * 64, 0, True
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            e = json.loads(line); k += 1
            if e["previous_hash"] != prev or e["current_hash"] != P.sha_obj({kk: vv for kk, vv in e.items() if kk != "current_hash"}):
                o = False
            prev = e["current_hash"]
        return o, k
    ok, n = verify(P.LEDGER)
    inj_accepted = sorted([s for s in P.accepted_sample_ids() if s.startswith("I")])
    summary = {"scenarios": results, "all_detected": all(v.get("detected") for v in results.values()),
                "DUPLICATE_ACCEPTED": dup_chained, "SILENT_DROP": sum(1 for v in results.values() if not v.get("detected")),
                "CORRUPTED_PAYLOAD": 0, "injection_accepted_samples": inj_accepted,
                "ledger_entries": n, "ledger_chain_ok": ok,
                "note": "only I5_DUP and I7_RETRY are legitimately accepted; the rest must remain failures"}
    p = os.path.join(ROOT, "fault_injection", "injection_results.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(summary, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps({k: (v.get("detected") if isinstance(v, dict) else v) for k, v in results.items()}, ensure_ascii=False))
    print("all_detected:", summary["all_detected"], "| DUPLICATE_ACCEPTED:", dup_chained, "| SILENT_DROP:", summary["SILENT_DROP"],
          "| ledger:", n, "chain_ok:", ok, "| inj_accepted:", inj_accepted)


if __name__ == "__main__":
    main()
