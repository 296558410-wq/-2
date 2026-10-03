# -*- coding: utf-8 -*-
"""RULING A: verify FREEZE_HASH by CONTENT EQUALITY under its own recorded v1 serialization.

Re-hashing the frozen registry with a different serializer was MY gate bug, not a change to the frozen layer.
The gate now distinguishes:
  * content change            -> FAIL (freeze registry content no longer matches the recorded constant)
  * serializer difference     -> not a failure; the recorded rule is documented and applied
Also emits the final HASH_GATE and builds WORKTREE_TEST_BASELINE.json (task section 13).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
RE = os.path.dirname(os.path.dirname(HERE))
AIQ = os.path.dirname(RE)
V3 = os.path.join(AIQ, "research", "hermes", "trader_v3")
NOW = datetime.now(timezone.utc).isoformat()
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FREEZE_EXPECTED = "7da599cdb6858ac624f9929d427c634187d257f8adb91d300b9fe33300aecb2f"
INPUT_EXPECTED = "704e1cfa8960cee881c5efccb1f23fe9679fa262da5770e82fe99d7338f9ac53"
OUTPUT_EXPECTED = "20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624"
CANON_PAYLOAD = os.path.join(HERE, "canonical_output_payload.json")
ART = ["opportunity_pool_hf_r2.json", "run_summary_hf_r2.json", "hf_env_audit.json",
        "canonical_output_payload.json", "canonical_hash_spec.json", "r2_superseded_outputs.json",
        "high_frequency_priority_registry.json", "v3_high_frequency_opportunity_r2_frozen_registry.json",
        "WORKTREE_BASELINE_MANIFEST.json", os.path.join("ledger", "hf_r2_ledger.jsonl")]
WATCH = {"trader_v1": os.path.join(AIQ, "research", "hermes", "trader_v1"),
          "trader_v2": os.path.join(AIQ, "research", "hermes", "trader_v2"),
          "trader_v3_strategy": os.path.join(AIQ, "research", "hermes", "trader_v3", "strategy")}


def sh(*a):
    r = subprocess.run(list(a), cwd=AIQ, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return ((r.stdout or "") + (r.stderr or "")).strip()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def v1_sha(o):
    """the ORIGINAL freeze-step serialization (default separators) - recorded rule for FREEZE_HASH"""
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def canonical_sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def main():
    # ---------- FREEZE_HASH by content equality under its own recorded rule ----------
    regf = json.load(open(os.path.join(HERE, "v3_high_frequency_opportunity_r2_frozen_registry.json"),
                           encoding="utf-8"))
    stored = regf.pop("FREEZE_HASH")
    regf.pop("frozen_at_utc", None)
    freeze_recomputed_v1 = v1_sha(regf)
    freeze_compact = canonical_sha_bytes(json.dumps(regf, sort_keys=True, ensure_ascii=False,
                                                     separators=(",", ":")).encode("utf-8"))
    freeze_content_ok = (freeze_recomputed_v1 == stored == FREEZE_EXPECTED)

    # ---------- INPUT / canonical payload / OUTPUT ----------
    summary = json.load(open(os.path.join(HERE, "run_summary_hf_r2.json"), encoding="utf-8"))
    input_ok = (summary["INPUT_HASH"] == INPUT_EXPECTED)
    payload_bytes = open(CANON_PAYLOAD, "rb").read()
    H1 = canonical_sha_bytes(payload_bytes)
    H2 = canonical_sha_bytes(open(CANON_PAYLOAD, "rb").read())
    spec = json.load(open(os.path.join(HERE, "canonical_hash_spec.json"), encoding="utf-8"))
    output_ok = (H1 == H2 == OUTPUT_EXPECTED == summary.get("OUTPUT_HASH") == spec["OUTPUT_HASH"])
    spec_ver_ok = (spec["HASH_SPEC_VERSION"] == 1 and summary.get("HASH_SPEC_VERSION") == 1)
    payload_reproducible = bool(spec["cross_run_check"]["H1_eq_H2_eq_H3"])
    excludes_ok = ("ts_utc" in spec["excluded_fields"] and "runtime_seconds" in spec["excluded_fields"])
    superseded = json.load(open(os.path.join(HERE, "r2_superseded_outputs.json"), encoding="utf-8"))
    superseded_ok = (len(superseded["SUPERSEDED_OUTPUT_HASHES"]) == 2
                      and all("TIMESTAMP_CONTAMINATION" in v for v in superseded["reasons"].values()))

    gate = {
        "FREEZE_HASH__content_equality_v1": freeze_content_ok,
        "FREEZE_HASH__serializer_note_recorded": True,
        "INPUT_HASH__expected": input_ok,
        "HASH_SPEC_VERSION__1": spec_ver_ok,
        "CANONICAL_PAYLOAD_REPRODUCIBLE": payload_reproducible,
        "OUTPUT_HASH_REPRODUCIBLE": output_ok,
        "EXCLUDES__dynamic_fields_including_ts_utc": excludes_ok,
        "SUPERSEDED__recorded_with_reason": superseded_ok,
    }
    gate["HASH_GATE"] = "PASS" if all(v for k, v in gate.items() if k != "HASH_GATE") else "FAIL"

    # ---------- section 13: WORKTREE_TEST_BASELINE ----------
    porcelain = [l for l in sh("git", "status", "--porcelain").splitlines() if l.strip()]
    r2_scope = [e for e in ({"path": l[3:].strip().strip('"'), "git": l[:2]} for l in porcelain)
                 if e["path"].replace("\\", "/").startswith("research/v3_opportunity_engine/high_frequency_r2")]
    artifacts = {f: {"sha256": sha_file(os.path.join(HERE, f)),
                       "size": os.path.getsize(os.path.join(HERE, f))} for f in ART
                  if os.path.exists(os.path.join(HERE, f))}
    ck = os.path.join(HERE, "test_checkpoints")
    cache_state = ({f: sha_file(os.path.join(ck, f)) for f in sorted(os.listdir(ck))} if os.path.isdir(ck) else {})
    led = os.path.join(HERE, "ledger", "hf_r2_ledger.jsonl")
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "mechanism_validation_r2"))
    import importlib
    mv2 = importlib.import_module("mechanism_validation_r2")
    ledger_state = {"sha256": sha_file(led), "chain": mv2.mv.MechanismLedger.verify(led)}
    watch = {}
    for name, root in WATCH.items():
        files = {}
        for r, _, fs in os.walk(root):
            if "__pycache__" in r:
                continue
            for f in fs:
                if f.lower().endswith((".py", ".yaml", ".yml")):
                    p = os.path.join(r, f)
                    files[os.path.relpath(p, AIQ).replace("\\", "/")] = sha_file(p)
        watch[name] = {"source_files": len(files), "digest": canonical_sha_bytes(
            json.dumps(files, sort_keys=True).encode("utf-8")), "files": files}

    semantics_lock = {
        "F3_COUNT": "NOT_COMPUTABLE", "F3_STATUS": "INSUFFICIENT_DATA", "VOLUME_ALL_ZERO_INPUT": True,
        "DURATION_MEASUREMENT_STATUS": "TRUNCATION_SENSITIVE", "OVERLAP_MERGE_CANDIDATES": [],
        "OVERLAP_AUDIT": "INFORMATIVE", "CANDIDATE_RESEARCH": 0, "ORDER_SEND": 0,
        "V3_FORWARD": "OFF", "V3_SHADOW": "OFF", "V3_LIVE": "OFF",
        "TOTAL_OPPORTUNITIES": 38367, "INDEPENDENT_EVENTS": 7792, "CLUSTERS": 12994,
        "INDEPENDENT_EVENTS_PER_WEEK": 86.3925, "HIGH_FREQUENCY_COUNT": 4, "MEDIUM_FREQUENCY_COUNT": 1,
        "LOW_FREQUENCY_COUNT": 0, "MEDIAN_DURATION": 47, "HERMES_INVESTIGATIONS": 300,
        "FREEZE_HASH": FREEZE_EXPECTED, "INPUT_HASH": INPUT_EXPECTED, "OUTPUT_HASH": OUTPUT_EXPECTED,
        "conclusions_locked": ["F3 cannot be computed from this input (volume identically zero)",
                                "duration measurement is truncation-sensitive",
                                "no detector-pair merge candidates under correct set math",
                                "discovery only; never an alpha / profitability / execution claim"],
    }
    baseline = {"schema": "v3_r2_worktree_test_baseline/1", "ts_utc": NOW, "head": sh("git", "rev-parse", "HEAD"),
                 "head_short": sh("git", "rev-parse", "--short", "HEAD"),
                 "pre_test_porcelain_lines": len(porcelain),
                 "r2_scope_entries": r2_scope, "r2_artifact_hashes": artifacts,
                 "cache_state": cache_state, "ledger_state": ledger_state, "semantics_lock": semantics_lock,
                 "isolation_watch": {k: {"source_files": v["source_files"], "digest": v["digest"]}
                                       for k, v in watch.items()},
                 "isolation_watch_full": watch,
                 "hash_gate": gate,
                 "rule": {"r2_scope_prefix": "research/v3_opportunity_engine/high_frequency_r2/",
                           "isolation_paths": list(WATCH.keys()),
                           "historical_dirty_policy": "recorded, never cleaned / never staged"},
                 "pre_test_test_result_file_exists": os.path.exists(os.path.join(HERE, "r2_19_test_results.json"))}
    json.dump(baseline, open(os.path.join(HERE, "WORKTREE_TEST_BASELINE.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)

    # record the serializer note in the spec doc + machine spec
    spec["freeze_hash_serialization_note"] = {
        "FREEZE_HASH": FREEZE_EXPECTED, "serialization": "UTF8_JSON_SORTED_KEYS_DEFAULT_SEPARATORS (v1 freeze step)",
        "recomputed_with_v1_rule": freeze_recomputed_v1, "content_equality": freeze_content_ok,
        "if_recomputed_with_canonical_compact_separators": freeze_compact,
        "explanation": ("the frozen registry content is unchanged; only the serializer differs. Re-hashing with a "
                         "different serializer is a gate bug, not a freeze change (ruling A).")}
    json.dump(spec, open(os.path.join(HERE, "canonical_hash_spec.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    p = os.path.join(V3, "reports", "V3_R2_CANONICAL_HASH_SPEC.md")
    if os.path.exists(p):
        t = open(p, encoding="utf-8").read()
        t += ("\n## FREEZE_HASH serialization (ruling A)\n\n```text\n"
               f"FREEZE_HASH = {FREEZE_EXPECTED}\n"
               "recorded_rule = UTF8_JSON_SORTED_KEYS_DEFAULT_SEPARATORS (v1 freeze step)\n"
               f"recomputed_with_recorded_rule = {freeze_recomputed_v1}\n"
               f"content_equality = {freeze_content_ok}\n"
               f"if_recomputed_with_compact_separators = {freeze_compact}  (differs -> gate must NOT use this)\n"
               "```\n\nThe frozen registry content is unchanged. The gate verifies content equality under the "
               "rule that produced the hash; it does not re-serialize with a different rule. OUTPUT_HASH uses the "
               "canonical compact serialization; FREEZE_HASH keeps its v1 rule. Both rules are recorded.\n")
        open(p, "w", encoding="utf-8", newline="\n").write(t)

    print("FREEZE_HASH content check (ruling A):")
    print("  recorded            =", FREEZE_EXPECTED)
    print("  recomputed (v1 rule)=", freeze_recomputed_v1, "| content_equal =", freeze_content_ok)
    print("  compact-separator   =", freeze_compact, "(deliberately NOT used by the gate)")
    print("HASH_GATE =", json.dumps(gate, ensure_ascii=False))
    print("WORKTREE_TEST_BASELINE =", json.dumps({"head": baseline["head_short"],
                                                    "porcelain_lines": len(porcelain),
                                                    "r2_scope_entries": len(r2_scope),
                                                    "artifacts": len(artifacts), "cache_files": len(cache_state),
                                                    "ledger_rows": ledger_state["chain"]["rows"],
                                                    "isolation_watch": list(WATCH.keys()),
                                                    "test_results_present": baseline["pre_test_test_result_file_exists"]},
                                                   ensure_ascii=False))
    print("SEMANTICS_LOCK =", json.dumps({k: semantics_lock[k] for k in ("F3_STATUS", "DURATION_MEASUREMENT_STATUS",
                                                                          "OVERLAP_MERGE_CANDIDATES", "CANDIDATE_RESEARCH",
                                                                          "TOTAL_OPPORTUNITIES", "INDEPENDENT_EVENTS",
                                                                          "CLUSTERS", "INDEPENDENT_EVENTS_PER_WEEK")},
                                          ensure_ascii=False))
    print("NEXT: 19 test stages (readonly -> replay -> deterministic -> audit -> finalize). NOT started in this run.")


if __name__ == "__main__":
    main()
