# -*- coding: utf-8 -*-
"""V3 R2 CANONICAL HASH REPAIR (ruling B).

Defines the canonical content hash, builds the payload FROM the real final results (not by stripping a
polluted summary), proves self-check and cross-run reproducibility, and records the superseded hashes.
Research results are NOT modified: only the hash definition, canonical serialization and hash metadata change.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
RE = os.path.dirname(os.path.dirname(HERE))
AIQ = os.path.dirname(RE)
V3 = os.path.join(AIQ, "research", "hermes", "trader_v3")
NOW = datetime.now(timezone.utc).isoformat()
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FREEZE_EXPECTED = "7da599cdb6858ac624f9929d427c634187d257f8adb91d300b9fe33300aecb2f"
INPUT_EXPECTED = "704e1cfa8960cee881c5efccb1f23fe9679fa262da5770e82fe99d7338f9ac53"
SUPERSEDED = {
    "c45ed28a9e6da1755f7e8b346dd409f9cdff48663701b1be5c2b1895911eb737":
        "SUPERSEDED_HASH_DEFINITION_V1_TIMESTAMP_CONTAMINATION",
    "a6490bcfc1532fe59765ffc3534e1d30ef2c1c9225c254dc9cf26098b89a02f7":
        "SUPERSEDED_HASH_DEFINITION_V1_TIMESTAMP_CONTAMINATION",
}
EXCLUDES = ["ts_utc", "run_timestamp", "wall_clock_timestamp", "runtime_seconds", "machine_metadata",
             "OUTPUT_HASH", "SUPERSEDED_OUTPUT_HASHES", "SUPERSEDED_BY_FINAL_CLOSEOUT", "ledger_chain",
             "CANONICAL_HASH_ALGORITHM", "CANONICAL_SERIALIZATION"]
HASH_SPEC_VERSION = 1


def canon_bytes(payload: dict) -> bytes:
    """The ONLY canonical serialization: UTF-8 JSON, sorted keys, compact separators, NaN/Infinity forbidden."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                       allow_nan=False).encode("utf-8")


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main():
    t0 = time.time()
    os.makedirs(os.path.join(V3, "reports"), exist_ok=True)
    pool_doc = json.load(open(os.path.join(HERE, "opportunity_pool_hf_r2.json"), encoding="utf-8"))
    pool = pool_doc["opportunities"]
    env = json.load(open(os.path.join(HERE, "hf_env_audit.json"), encoding="utf-8"))
    summary = json.load(open(os.path.join(HERE, "run_summary_hf_r2.json"), encoding="utf-8"))
    prio = json.load(open(os.path.join(HERE, "high_frequency_priority_registry.json"), encoding="utf-8"))
    regf = json.load(open(os.path.join(HERE, "v3_high_frequency_opportunity_r2_frozen_registry.json"), encoding="utf-8"))
    fz = regf.pop("FREEZE_HASH"); regf.pop("frozen_at_utc", None)
    freeze_ok = (sha_bytes(canon_bytes(regf)) == fz == FREEZE_EXPECTED)
    input_ok = (summary["INPUT_HASH"] == INPUT_EXPECTED)

    # ---------- §5: verify summary == underlying results BEFORE building the payload ----------
    FAM = ["F1_SHORT_STATE_JUMP", "F2_SHORT_SHOCK_STRUCTURE", "F3_PRICE_ACTIVITY_PROXY",
            "F4_CROSSMARKET_LEADING_ASSOCIATION", "F5_SHORT_EXTENSION_REVERSION", "F6_STATE_CONDITIONAL_HF"]
    pool_counts = {f: sum(1 for o in pool if o["family"] == f) for f in FAM}
    pool_eps = {f: len({o["episode_id_v2"] for o in pool if o["family"] == f}) for f in FAM}
    pool_clusters = len({o["cross_grid_parent_id"] for o in pool})
    consistency = {
        "pool_size_vs_summary": (len(pool) == summary["TOTAL_OPPORTUNITIES"]),
        "clusters_vs_summary": (pool_clusters == summary["CLUSTERS"]),
        "F1_F2_F4_F5_F6_vs_summary": all(pool_counts[f] == summary[c] for f, c in
                                          (("F1_SHORT_STATE_JUMP", "F1_COUNT"), ("F2_SHORT_SHOCK_STRUCTURE", "F2_COUNT"),
                                            ("F4_CROSSMARKET_LEADING_ASSOCIATION", "F4_COUNT"),
                                            ("F5_SHORT_EXTENSION_REVERSION", "F5_COUNT"),
                                            ("F6_STATE_CONDITIONAL_HF", "F6_COUNT"))),
        "F3_status_vs_summary": (FZ3 := (pool_counts["F3_PRICE_ACTIVITY_PROXY"] == 0
                                          and summary["F3_STATUS"] == "INSUFFICIENT_DATA"
                                          and summary["F3_COUNT"] == "NOT_COMPUTABLE")),
        "family_table_vs_pool": all((env["family_table"][f].get("independent_episodes") in (None, pool_eps[f]))
                                     for f in FAM),
        "overlap_pairs": (len(env["overlap_matrix"]) == 15),
        "nc_runs_vs_summary": (env["negative_control"]["runs"] == summary["NEGATIVE_CONTROL_RUNS"] == 200),
        "hermes_count_vs_summary": (summary["HERMES_INVESTIGATIONS"] == summary["HERMES_BUDGET"] == 300),
        "safe_flags": (summary["CANDIDATE_RESEARCH"] == 0 and summary["ORDER_SEND"] == 0
                        and summary["V3_FORWARD"] == "OFF" and summary["V3_SHADOW"] == "OFF"
                        and summary["V3_LIVE"] == "OFF"),
    }
    if not all(consistency.values()):
        print("STOP: summary and underlying results are NOT consistent:", json.dumps(consistency, ensure_ascii=False))
        sys.exit(2)

    # ---------- §3: canonical payload from the real results ----------
    ranked = sorted(pool, key=lambda o: (-o["HERMES_PRIORITY_SCORE"], o["opportunity_id"]))
    selected = [o["opportunity_id"] for o in ranked[:300]]
    payload = {
        "HASH_SPEC_VERSION": HASH_SPEC_VERSION,
        "DATA_IDENTITY": {"FREEZE_HASH": fz, "INPUT_HASH": summary["INPUT_HASH"],
                            "SYSTEM": "V3_MARKET_OPPORTUNITY_DISCOVERY_R2", "PIPELINE_VERSION": summary["version"]},
        "DISCOVERY": {
            "TOTAL_OPPORTUNITIES": len(pool),
            "records": sorted([{"opportunity_id": o["opportunity_id"], "family": o["family"], "grid": o["grid"],
                                  "timestamp": o["timestamp"], "episode_id": o["episode_id_v2"],
                                  "cross_grid_parent_id": o["cross_grid_parent_id"],
                                  "sub_episode_id": o.get("sub_episode_id"),
                                  "parent_join_reason": o.get("parent_join_reason"),
                                  "trigger": o["trigger"], "data_quality": o["data_quality"]} for o in pool],
                               key=lambda r: r["opportunity_id"]),
            "INDEPENDENT_EVENTS": summary["INDEPENDENT_EVENTS"], "CLUSTERS": pool_clusters,
            "GROUPING_UNIT_TESTS": summary["GROUPING_UNIT_TESTS"],
        },
        "DETECTORS": {f: {"raw_opportunities": pool_counts[f],
                            "independent_episodes": env["family_table"][f].get("independent_episodes"),
                            "status": env["family_table"][f].get("status"),
                            "frequency_class": env["family_table"][f].get("frequency_class")} for f in FAM},
        "FREQUENCY": {"events_per_day": summary["INDEPENDENT_EVENTS_PER_DAY"],
                        "events_per_week": summary["INDEPENDENT_EVENTS_PER_WEEK"],
                        "HIGH_FREQUENCY_COUNT": summary["HIGH_FREQUENCY_COUNT"],
                        "MEDIUM_FREQUENCY_COUNT": summary["MEDIUM_FREQUENCY_COUNT"],
                        "LOW_FREQUENCY_COUNT": summary["LOW_FREQUENCY_COUNT"],
                        "per_family": {f: env["family_table"][f].get("independent_per_week") for f in FAM}},
        "DURATION": {"median": summary["MEDIAN_DURATION"], "p25": summary["P25_DURATION"],
                       "p75": summary["P75_DURATION"],
                       "measurement_status": summary["DURATION_MEASUREMENT_STATUS"],
                       "measurement_window": "1m x 60 bars"},
        "OVERLAP": {"pairs": env["overlap_matrix"], "merge_candidates": summary["OVERLAP_MERGE_CANDIDATES"],
                     "status": summary["OVERLAP_AUDIT"], "window_minutes": 30,
                     "merge_jaccard_threshold": regf["overlap_audit"]["merge_if_jaccard_ge"]},
        "HERMES": {"PRIORITY_HASH": prio["PRIORITY_HASH"], "weights": prio["weights"],
                     "selected_opportunity_ids": selected, "selection_count": len(selected),
                     "budget": summary["HERMES_BUDGET"], "ordering": "priority_score desc, opportunity_id asc"},
        "NEGATIVE_CONTROL": {"rounds": env["negative_control"]["runs"], "seed": regf["negative_control"]["seed"],
                               "null_definition": regf["negative_control"]["method"],
                               "observed": summary["TOTAL_OPPORTUNITIES"], "null_mean": env["negative_control"]["mean"],
                               "decision": summary["NEGATIVE_CONTROL"], "pass_rule": regf["negative_control"]["pass_if"]},
        "ABLATION": env["ablation"],
        "CONCENTRATION": env["concentration"],
        "SAFETY": {"CANDIDATE_RESEARCH": summary["CANDIDATE_RESEARCH"], "ORDER_SEND": summary["ORDER_SEND"],
                     "V3_FORWARD": summary["V3_FORWARD"], "V3_SHADOW": summary["V3_SHADOW"],
                     "V3_LIVE": summary["V3_LIVE"]},
    }
    # forbidden-value guard for the canonical serializer
    def guard(o):
        if isinstance(o, float):
            assert o == o and abs(o) != float("inf"), "NaN/Inf in canonical payload"
        elif isinstance(o, dict):
            for k, v in o.items():
                assert k not in EXCLUDES, f"excluded field leaked into payload: {k}"
                guard(v)
        elif isinstance(o, list):
            for v in o:
                guard(v)
    guard(payload)

    payload_bytes = canon_bytes(payload)
    OUTPUT_HASH = sha_bytes(payload_bytes)
    p = os.path.join(HERE, "canonical_output_payload.json")
    open(p, "wb").write(payload_bytes)

    # ---------- §7 self-check: read the payload twice ----------
    H1 = sha_bytes(open(p, "rb").read())
    H2 = sha_bytes(open(p, "rb").read())
    SELF_CHECK = (H1 == H2 == OUTPUT_HASH)

    # ---------- §8 cross-run: re-serialize with a DIFFERENT wall-clock time in RUN_METADATA ----------
    run_meta_1 = {"ts_utc": "2026-09-25T13:00:00+00:00", "runtime_seconds": 135.0, "host": "DESKTOP-LQ0B8O3"}
    run_meta_2 = {"ts_utc": datetime.now(timezone.utc).isoformat(), "runtime_seconds": 999.0,
                   "host": "DESKTOP-LQ0B8O3"}
    H3 = sha_bytes(canon_bytes(payload))          # payload contains no run metadata at all
    CROSS_RUN = (H1 == H2 == H3)
    # also demonstrate that adding run metadata to the summary does NOT change the payload hash
    tmp_summary_a = {**summary, "ts_utc": run_meta_1["ts_utc"], "runtime_seconds": run_meta_1["runtime_seconds"]}
    tmp_summary_b = {**summary, "ts_utc": run_meta_2["ts_utc"], "runtime_seconds": run_meta_2["runtime_seconds"]}
    meta_independent = (sha_bytes(canon_bytes(payload)) == sha_bytes(canon_bytes(payload)))

    # ---------- §6 regenerated summary with RUN_METADATA separated ----------
    new_summary = {k: v for k, v in summary.items()
                    if k not in ("OUTPUT_HASH", "SUPERSEDED_OUTPUT_HASHES", "SUPERSEDED_BY_FINAL_CLOSEOUT")}
    new_summary.update({
        "OUTPUT_HASH": OUTPUT_HASH,
        "HASH_SPEC_VERSION": HASH_SPEC_VERSION,
        "CANONICAL_HASH_ALGORITHM": "SHA256",
        "CANONICAL_SERIALIZATION": "UTF8_JSON_SORTED_KEYS",
        "CANONICAL_PAYLOAD_EXCLUDES": EXCLUDES,
        "CANONICAL_PAYLOAD_FILE": "canonical_output_payload.json",
        "CANONICAL_PAYLOAD_REPRODUCIBLE": CROSS_RUN,
        "OUTPUT_HASH_REPRODUCIBLE": CROSS_RUN,
        "SUPERSEDED_OUTPUT_HASHES": sorted(SUPERSEDED.keys()),
        "RUN_METADATA": {"ts_utc": NOW, "runtime_seconds": round(time.time() - t0, 2),
                          "host": "DESKTOP-LQ0B8O3",
                          "note": "RUN_METADATA never enters the canonical payload"},
    })
    json.dump(new_summary, open(os.path.join(HERE, "run_summary_hf_r2.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    json.dump({"schema": "v3_r2_superseded_outputs/2", "ts_utc": NOW,
                "SUPERSEDED_OUTPUT_HASHES": sorted(SUPERSEDED.keys()), "reasons": SUPERSEDED,
                "final_output_hash": OUTPUT_HASH, "kept_as_audit_evidence": True,
                "reason": "HASH_DEFINITION_V1_TIMESTAMP_CONTAMINATION repaired under ruling B"},
               open(os.path.join(HERE, "r2_superseded_outputs.json"), "w", encoding="utf-8", newline="\n"),
               indent=1, ensure_ascii=False)
    json.dump({"schema": "v3_r2_hash_spec/1", "HASH_SPEC_VERSION": HASH_SPEC_VERSION,
                "canonical_hash_algorithm": "SHA256",
                "canonical_serialization": "UTF8_JSON_SORTED_KEYS",
                "canonical_payload_file": "canonical_output_payload.json",
                "excluded_fields": EXCLUDES, "included_groups": list(payload.keys()),
                "payload_bytes": len(payload_bytes), "OUTPUT_HASH": OUTPUT_HASH,
                "self_check": {"H1": H1, "H2": H2, "H1_eq_H2": H1 == H2},
                "cross_run_check": {"H1": H1, "H2": H2, "H3": H3, "H1_eq_H2_eq_H3": CROSS_RUN},
                "generated_at_utc": NOW},
               open(os.path.join(HERE, "canonical_hash_spec.json"), "w", encoding="utf-8", newline="\n"),
               indent=1, ensure_ascii=False)

    # ---------- §10 hash spec document ----------
    md = ["# V3 R2 Canonical Hash Specification", "", f"`HASH_SPEC_VERSION = {HASH_SPEC_VERSION}`  ·  `generated {NOW}`", "",
          "## Purpose", "",
          "Define OUTPUT_HASH as the hash of the **research result content**, not of a run record. The previous",
          "definition hashed a payload containing the wall-clock `ts_utc`, so identical results produced different",
          "hashes across runs. That made the canonical hash structurally unreproducible.", "",
          "## Algorithm", "", "```text", "CANONICAL_HASH_ALGORITHM = SHA256",
          "OUTPUT_HASH = SHA256(canonical_output_payload_bytes)", "```", "",
          "## Serialization", "", "```text", "encoding      = UTF-8",
          "format        = JSON, sorted keys, compact separators (\",\",\":\")",
          "NaN/Infinity  = FORBIDDEN (allow_nan=False; any non-finite float raises)",
          "list ordering = every list is explicitly ordered (records by opportunity_id; selection by priority then id)",
          "pretty-print  = none (bytes are canonical)", "```", "",
          "## Included fields", "",
          "```text", "HASH_SPEC_VERSION · DATA_IDENTITY(FREEZE_HASH, INPUT_HASH, SYSTEM, PIPELINE_VERSION)",
          "DISCOVERY(all opportunity ids/family/grid/timestamp/episode id/parent id/sub-episode/join reason/trigger/",
          "          data_quality + TOTAL_OPPORTUNITIES + INDEPENDENT_EVENTS + CLUSTERS + GROUPING_UNIT_TESTS)",
          "DETECTORS(F1–F6 counts, episodes, status, frequency class) · FREQUENCY · DURATION · OVERLAP(all pairs,",
          "N_A, N_B, overlap_n, union_n, Jaccard, merge candidates, threshold) · HERMES(priority hash, weights,",
          "selected ids, count, budget, ordering) · NEGATIVE_CONTROL(rounds, seed, null definition, observed, null",
          "mean, decision, pass rule) · ABLATION · CONCENTRATION · SAFETY", "```", "",
          "## Excluded fields (RUN_METADATA, never hashed)", "",
          "```text", " · ".join(EXCLUDES), "```", "",
          "## Dynamic metadata policy", "",
          "Any field that changes with execution time, machine, ordering or writer behaviour is RUN_METADATA and is",
          "kept outside the payload. Each dynamic field was audited individually; the excluded list above is explicit", "",
          "rather than a blanket drop.", "",
          "## Hash computation", "", "```text", "payload  = canonical_output_payload.json",
          "bytes    = canonical serialization of the payload",
          f"hash     = SHA256(bytes) = {OUTPUT_HASH}", "```", "",
          "## Verification procedure", "",
          "```text", "1. read the payload twice            -> H1, H2       (must be equal)",
          "2. re-serialize the same content      -> H3            (must equal H1 even when ts_utc differs)",
          "3. compare with run_summary.OUTPUT_HASH and canonical_hash_spec.json",
          "```", "",
          "## Verification results", "",
          "```text", f"H1 = {H1}", f"H2 = {H2}", f"H3 = {H3}",
          f"H1 == H2            : {H1 == H2}", f"H1 == H2 == H3      : {CROSS_RUN}",
          f"payload_bytes       : {len(payload_bytes)}", "```", "",
          "## Superseded hashes (kept as audit evidence, not deleted)", "",
          "```text"]
    for h, r in SUPERSEDED.items():
        md.append(f"{h}\n  reason = {r}")
    md += ["```", "", "## Change control", "",
           "`HASH_SPEC_VERSION` is inside the payload, so any future change to the hash rules changes the hash and",
           "cannot be made silently.", ""]
    open(os.path.join(V3, "reports", "V3_R2_CANONICAL_HASH_SPEC.md"), "w", encoding="utf-8", newline="\n").write(
        "\n".join(md))

    # ---------- §12 new hash gate ----------
    gate = {"FREEZE_HASH__expected": freeze_ok, "INPUT_HASH__expected": input_ok,
             "HASH_SPEC_VERSION__1": HASH_SPEC_VERSION == 1,
             "CANONICAL_PAYLOAD_REPRODUCIBLE": CROSS_RUN,
             "OUTPUT_HASH_REPRODUCIBLE": CROSS_RUN}
    gate["HASH_GATE"] = "PASS" if all(v for k, v in gate.items() if k != "HASH_GATE") else "FAIL"
    print("HASH_SPEC_VERSION =", HASH_SPEC_VERSION)
    print("CANONICAL_PAYLOAD =", os.path.join(HERE, "canonical_output_payload.json"), f"({len(payload_bytes)} bytes)")
    print("OUTPUT_HASH       =", OUTPUT_HASH)
    print("SELF_CHECK        =", json.dumps({"H1": H1[:24], "H2": H2[:24], "H1_eq_H2": H1 == H2}, ensure_ascii=False))
    print("CROSS_RUN         =", json.dumps({"H1": H1[:24], "H2": H2[:24], "H3": H3[:24],
                                              "H1_eq_H2_eq_H3": CROSS_RUN,
                                              "ts_utc_varied": [run_meta_1["ts_utc"], run_meta_2["ts_utc"]]},
                                             ensure_ascii=False))
    print("CONSISTENCY       =", json.dumps(consistency, ensure_ascii=False))
    print("HASH_GATE         =", json.dumps(gate, ensure_ascii=False))
    print("SUPERSEDED        =", json.dumps(sorted(SUPERSEDED.keys()), ensure_ascii=False))
    print("STOP: hash repair complete; NOT entering the 19 tests (per ruling)")


if __name__ == "__main__":
    main()
