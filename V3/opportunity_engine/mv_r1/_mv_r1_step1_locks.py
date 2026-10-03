# -*- coding: utf-8 -*-
"""MV-R1 STEP 1 — INPUT LOCK + METHOD LOCK + MV-R3 control re-verification + MV-R1 baseline/policy freeze.

READ_ONLY on R2 (bdd3d7d). Writes only under research/v3_opportunity_engine/mv_r1/.
Any gate failure -> STOP, NO RESEARCH, NO COMMIT.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))          # .../v3_opportunity_engine/mv_r1
ENGINE = os.path.dirname(HERE)                              # .../v3_opportunity_engine
RE = os.path.dirname(ENGINE)                                # .../research
AIQ = os.path.dirname(RE)
R2 = os.path.join(ENGINE, "high_frequency_r2")
MV2 = os.path.join(ENGINE, "mechanism_validation_r2")
MV3 = os.path.join(ENGINE, "mechanism_validation_r3")
MV4 = os.path.join(ENGINE, "mechanism_validation_r4")
OUT = HERE
NOW = datetime.now(timezone.utc).isoformat()
EXPECT = {"TOTAL_OPPORTUNITIES": 38367, "INDEPENDENT_EVENTS": 7792, "CLUSTERS": 12994,
           "F3_STATUS": "INSUFFICIENT_DATA", "MERGE_CANDIDATES": [], "HIGH_FREQUENCY_COUNT": 4, "CANDIDATE": 0,
           "FREEZE_HASH": "7da599cdb6858ac624f9929d427c634187d257f8adb91d300b9fe33300aecb2f",
           "CANONICAL": "20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624",
           "INPUT": "704e1cfa8960cee881c5efccb1f23fe9679fa262da5770e82fe99d7338f9ac53",
           "METHOD_HASH": "571bad8fd9621780d676bfbd97b0687a1fa9c87e365311827456093969f36394"}
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def sh(*a):
    r = subprocess.run(list(a), cwd=AIQ, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return ((r.stdout or "") + (r.stderr or "")).strip()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def canon(o):
    return json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def stop(stage, gate, extra=None):
    os.makedirs(OUT, exist_ok=True)
    rec = {"STATUS": "STOPPED", "STOPPED_AT": stage, "FIRST_FAILED_GATE": gate,
            "RESEARCH_STARTED": False, "COMMIT": "NONE", "ts_utc": NOW, **(extra or {})}
    json.dump(rec, open(os.path.join(OUT, "run_summary.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)
    print("\n=== MV-R1 ===\n" + json.dumps(rec, ensure_ascii=False, indent=1), flush=True)
    sys.exit(2)


def main():
    os.makedirs(OUT, exist_ok=True)
    gates, detail = {}, {}

    # ---------- STEP 1: R2 INPUT LOCK ----------
    summ = json.load(open(os.path.join(R2, "run_summary_hf_r2.json"), encoding="utf-8"))
    pool = json.load(open(os.path.join(R2, "opportunity_pool_hf_r2.json"), encoding="utf-8"))["opportunities"]
    canon_hash = sha_file(os.path.join(R2, "canonical_output_payload.json"))
    counts = {"TOTAL_OPPORTUNITIES": len(pool), "INDEPENDENT_EVENTS": summ["INDEPENDENT_EVENTS"],
               "CLUSTERS": len({o["cross_grid_parent_id"] for o in pool}), "F3_STATUS": summ["F3_STATUS"],
               "MERGE_CANDIDATES": summ["OVERLAP_MERGE_CANDIDATES"],
               "HIGH_FREQUENCY_COUNT": summ["HIGH_FREQUENCY_COUNT"], "CANDIDATE": summ["CANDIDATE_RESEARCH"]}
    gates["R2_FREEZE_HASH_MATCH"] = (summ["FREEZE_HASH"] == EXPECT["FREEZE_HASH"])
    gates["R2_CANONICAL_HASH_MATCH"] = (canon_hash == EXPECT["CANONICAL"] == summ["OUTPUT_HASH"])
    gates["R2_INPUT_HASH_MATCH"] = (summ["INPUT_HASH"] == EXPECT["INPUT"])
    mism = {k: {"got": counts[k], "expected": EXPECT[k]} for k in counts if counts[k] != EXPECT[k]}
    gates["R2_COUNTS_MATCH"] = not mism
    gates["R2_HEAD_IS_bdd3d7d"] = (sh("git", "log", "-1", "--format=%h %s").startswith("bdd3d7d "))
    input_lock = {"head": sh("git", "log", "-1", "--format=%h %s"),
                   "FREEZE_HASH": summ["FREEZE_HASH"][:24], "CANONICAL": canon_hash[:24], "INPUT": summ["INPUT_HASH"][:24],
                   "counts": counts, "mismatches": mism, "pool_size": len(pool),
                   "unique_opportunity_ids": len({o["opportunity_id"] for o in pool}),
                   "unique_episode_ids": len({o["episode_id_v2"] for o in pool}),
                   "unique_cross_grid_parent_ids": len({o["cross_grid_parent_id"] for o in pool})}
    detail["INPUT_LOCK"] = input_lock
    print("STEP1 INPUT LOCK:", json.dumps({**input_lock, "counts": counts, "mismatches": mism},
                                            ensure_ascii=False)[:900], flush=True)
    if not all(gates[k] for k in ("R2_FREEZE_HASH_MATCH", "R2_CANONICAL_HASH_MATCH", "R2_INPUT_HASH_MATCH",
                                    "R2_COUNTS_MATCH", "R2_HEAD_IS_bdd3d7d")):
        stop("STEP1_INPUT_LOCK", "R2 input identity mismatch", {"detail": input_lock})

    # ---------- STEP 2: METHOD LOCK (MV-R3) ----------
    mb = json.load(open(os.path.join(MV4, "method_baseline_r3.json"), encoding="utf-8"))
    method_hash = mb["R3_METHOD_HASH"]
    gates["METHOD_HASH_MATCH"] = (method_hash == EXPECT["METHOD_HASH"])
    mv2_reg = json.load(open(os.path.join(MV2, "run_summary_r2.json"), encoding="utf-8"))["registry_hash"]
    detail["METHOD_LOCK"] = {"method_hash": method_hash, "from": "mechanism_validation_r4/method_baseline_r3.json",
                              "mv2_registry_hash": mv2_reg, "method_changed": mb["METHOD_CHANGED"],
                              "inherits": "MV-R3_POSITIVE_CONTROL_REPAIR"}
    print("STEP2 METHOD LOCK:", json.dumps({"METHOD_HASH_MATCH": gates["METHOD_HASH_MATCH"],
                                              "method_hash": method_hash[:24]}, ensure_ascii=False), flush=True)
    if not gates["METHOD_HASH_MATCH"]:
        stop("STEP2_METHOD_LOCK", "METHOD_HASH != 571bad8f…", {"detail": detail["METHOD_LOCK"]})

    # ---------- STEP 3: MV-R3 control validity (must all be PASS) ----------
    r3 = json.load(open(os.path.join(MV3, "run_summary_r3.json"), encoding="utf-8"))
    ctl = {"POSITIVE_CONTROL": r3["POSITIVE_CONTROL"], "POSITIVE_DETECTED": r3.get("POSITIVE_CONTROL_DETECTED"),
            "NEGATIVE_CONTROL_A": r3["NEGATIVE_CONTROL_A"]["status"],
            "NEGATIVE_CONTROL_B": r3["NEGATIVE_CONTROL_B"]["status"],
            "NEGATIVE_CONTROL_C": r3["NEGATIVE_CONTROL_C"]["status"],
            "METHOD_VALIDITY": r3["METHOD_VALIDITY"],
            "permutation_count": r3["permutation_count"], "null_runs": r3["null_runs"],
            "seed": r3["random_seed"]}
    gates["POSITIVE_CONTROL_PASS"] = (ctl["POSITIVE_CONTROL"] == "PASS")
    gates["NC_A_PASS"] = (ctl["NEGATIVE_CONTROL_A"] == "PASS")
    gates["NC_B_PASS"] = (ctl["NEGATIVE_CONTROL_B"] == "PASS")
    gates["NC_C_PASS"] = (ctl["NEGATIVE_CONTROL_C"] == "PASS")
    detail["CONTROLS"] = ctl
    print("STEP3 MV-R3 CONTROLS:", json.dumps(ctl, ensure_ascii=False), flush=True)
    if not all(gates[k] for k in ("POSITIVE_CONTROL_PASS", "NC_A_PASS", "NC_B_PASS", "NC_C_PASS")):
        stop("STEP3_CONTROLS", "METHOD_VALIDITY = INVALID (a control failed)", {"detail": ctl})

    # ---------- STEP 4: event-dedup pre-audit (structure only, no research yet) ----------
    fam = {}
    grid = {}
    for o in pool:
        fam[o["family"]] = fam.get(o["family"], 0) + 1
        grid[o["grid"]] = grid.get(o["grid"], 0) + 1
    ep_to_parents, cg_multi = {}, 0
    for o in pool:
        ep_to_parents.setdefault(o["episode_id_v2"], set()).add(o["cross_grid_parent_id"])
    for p, eps in {}.items():
        pass
    parent_grids = {}
    for o in pool:
        parent_grids.setdefault(o["cross_grid_parent_id"], set()).add(o["grid"])
    cg_multi = sum(1 for v in parent_grids.values() if len(v) > 1)
    fam_of_parent = {}
    for o in pool:
        fam_of_parent.setdefault(o["cross_grid_parent_id"], set()).add(o["family"])
    cf_multi = sum(1 for v in fam_of_parent.values() if len(v) > 1)
    dedup = {"RAW_OPPORTUNITIES": len(pool), "INDEPENDENT_EVENTS": len({o["episode_id_v2"] for o in pool}),
              "CLUSTERS_CROSS_GRID_PARENT": len(parent_grids),
              "CROSS_GRID_MULTI_PARENT_COUNT": cg_multi,
              "CROSS_FAMILY_MULTI_PARENT_COUNT": cf_multi,
              "DETECTOR_COUNTS": fam, "GRID_COUNTS": grid,
              "episode_ids_per_parent_max": max((len(v) for v in ep_to_parents.values()), default=0)}
    detail["DEDUP_STRUCTURE"] = dedup
    print("STEP4 DEDUP STRUCTURE:", json.dumps(dedup, ensure_ascii=False)[:700], flush=True)

    # ---------- STEP 5: MV-R1 baseline + boundary policy freeze ----------
    base = {"schema": "v3_mvr1_worktree_baseline/1", "ts_utc": NOW, "HEAD": sh("git", "log", "-1", "--format=%h %s"),
             "R2_FREEZE_HASH": summ["FREEZE_HASH"], "R2_CANONICAL_HASH": canon_hash, "R2_INPUT_HASH": summ["INPUT_HASH"],
             "METHOD_HASH": method_hash, "R2_COUNTS": counts,
             "WORKTREE_STATUS": sh("git", "status", "--porcelain")[:6000],
             "isolation_baseline": {}}
    watch = {"trader_v1": os.path.join(RE, "hermes", "trader_v1"), "trader_v2": os.path.join(RE, "hermes", "trader_v2"),
              "trader_v3_strategy": os.path.join(RE, "hermes", "trader_v3", "strategy")}
    for k, root in watch.items():
        files = {}
        for r_, _, fs in os.walk(root):
            if "__pycache__" in r_:
                continue
            for f in fs:
                if f.lower().endswith((".py", ".yaml", ".yml")):
                    p = os.path.join(r_, f)
                    files[os.path.relpath(p, AIQ).replace("\\", "/")] = sha_file(p)
        base["isolation_baseline"][k] = {"source_files": len(files),
                                           "digest": hashlib.sha256(canon(files)).hexdigest(), "files": files}
    json.dump(base, open(os.path.join(OUT, "WORKTREE_BASELINE_MV_R1.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    policy = {"POLICY_VERSION": 1, "policy_name": "MV_R1_BOUNDARY_POLICY",
               "mv_r1_scope_prefix": "research/v3_opportunity_engine/mv_r1/",
               "r2_scope_prefix_readonly": "research/v3_opportunity_engine/high_frequency_r2/",
               "closeout_artifact_allowlist": ["research/hermes/trader_v3/reports/V3_R2_CANONICAL_HASH_SPEC.md"],
               "runtime_output_path_classes": ["research/hermes/trader_v1/run_state/*",
                                                 "research/hermes/trader_v1/memory/reviews/*",
                                                 "research/hermes/trader_v2/observations/*",
                                                 "research/hermes/trader_v2/state/decision_contexts/*"],
               "non_research_cache_patterns": ["*__pycache__/*", "*.pyc"],
               "unexpected_classes": ["V1/V2 source/config", "unknown trader_v3 files", "unregistered research files"],
               "principles": {"exclusions_pre_registered_before_results": True,
                               "exclusion_unit": "PATH_CLASS_NOT_INDIVIDUAL_FILES",
                               "unknown_new_file": "BOUNDARY_VIOLATION",
                               "no_reset_hard_no_clean_fd_no_checkout_dot": True}}
    policy["POLICY_HASH"] = hashlib.sha256(canon({k: v for k, v in policy.items()})).hexdigest()
    json.dump(policy, open(os.path.join(OUT, "MV_R1_BOUNDARY_POLICY.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    herm = {"HERMES_BUDGET_FROZEN": 500, "frozen_at_utc": NOW,
             "note": "locked before execution; 501+ requires a new task; if insufficient -> STOP REPORT_BUDGET_EXHAUSTED"}
    json.dump(herm, open(os.path.join(OUT, "hermes_budget.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)

    # ---------- REPORT ----------
    out = {"STATUS": "INPUT_AND_METHOD_LOCKED", "ts_utc": NOW,
            "R2_HEAD": "bdd3d7d", "R2_INPUT_IMMUTABLE": True,
            "R2_FREEZE_HASH_MATCH": True, "R2_CANONICAL_HASH_MATCH": True, "R2_INPUT_HASH_MATCH": True,
            "R2_COUNTS": counts, "METHOD_HASH_MATCH": True, "METHOD_HASH": method_hash,
            "POSITIVE_CONTROL": ctl["POSITIVE_CONTROL"], "NEGATIVE_A": ctl["NEGATIVE_CONTROL_A"],
            "NEGATIVE_B": ctl["NEGATIVE_CONTROL_B"], "NEGATIVE_C": ctl["NEGATIVE_CONTROL_C"],
            "METHOD_VALIDITY": ctl["METHOD_VALIDITY"], "HERMES_BUDGET": 500,
            "baseline": "WORKTREE_BASELINE_MV_R1.json", "boundary_policy_hash": policy["POLICY_HASH"],
            "dedup_structure": dedup,
            "gates": gates,
            "NEXT": ["event dedup / cross-grid / cross-family dependency audit", "mechanism identification (M01-M11)",
                      "artifact audit", "counter-evidence", "null/permutation", "Hermes <=500", "positive/negative controls",
                      "deterministic", "replay", "isolation", "boundary", "commit gate"],
            "COMMIT": "NONE", "CANDIDATE": 0, "ORDER_SEND": 0, "V3_FORWARD": "OFF", "V3_SHADOW": "OFF", "V3_LIVE": "OFF",
            "STOP_AFTER_MV_R1": True}
    json.dump(out, open(os.path.join(OUT, "run_summary.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)
    json.dump(detail, open(os.path.join(OUT, "lock_details.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)
    print("\n=== MV-R1 (STEP 1 LOCK REPORT) ===\n" + json.dumps(out, ensure_ascii=False, indent=1)[:2000], flush=True)


if __name__ == "__main__":
    main()
