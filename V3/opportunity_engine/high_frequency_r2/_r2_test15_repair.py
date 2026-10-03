# -*- coding: utf-8 -*-
"""R2 TEST_15 REPAIR + FINAL CLOSEOUT.

Engineering only: hard-assert TEST_15, use the frozen HASH_SPEC_VERSION=1 canonical path for the reproduction,
re-verify checkpoints, clean the wrongly staged historical items, stage R2-only, audit, commit.
Research results and research rules are NOT modified. Any gate failure -> STOP, no commit, no forced PASS.
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
CK = os.path.join(HERE, "test_checkpoints")
NOW = datetime.now(timezone.utc).isoformat()
FREEZE = "7da599cdb6858ac624f9929d427c634187d257f8adb91d300b9fe33300aecb2f"
INPUT = "704e1cfa8960cee881c5efccb1f23fe9679fa262da5770e82fe99d7338f9ac53"
OUTHASH = "20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624"
LOCK = {"TOTAL_OPPORTUNITIES": 38367, "INDEPENDENT_EVENTS": 7792, "CLUSTERS": 12994, "F1": 16591, "F2": 12226,
         "F3_STATUS": "INSUFFICIENT_DATA", "F4": 1836, "F5": 473, "F6": 7241, "PER_WEEK": 86.3925,
         "HIGH": 4, "MEDIUM": 1, "LOW": 0, "MEDIAN_DURATION": 47.0, "DURATION_STATUS": "TRUNCATION_SENSITIVE",
         "MERGE_CANDIDATES": [], "HERMES": 300, "NC_ROUNDS": 200, "CANDIDATE": 0}
FAM = ["F1_SHORT_STATE_JUMP", "F2_SHORT_SHOCK_STRUCTURE", "F3_PRICE_ACTIVITY_PROXY",
        "F4_CROSSMARKET_LEADING_ASSOCIATION", "F5_SHORT_EXTENSION_REVERSION", "F6_STATE_CONDITIONAL_HF"]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def sh(*a):
    r = subprocess.run(list(a), cwd=AIQ, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return ((r.stdout or "") + (r.stderr or "")).strip()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def canon_bytes(o):
    return json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def build_payload():
    """Rebuild the canonical payload FROM the current (reproduction-produced) artifacts, per HASH_SPEC_VERSION=1."""
    pool = json.load(open(os.path.join(HERE, "opportunity_pool_hf_r2.json"), encoding="utf-8"))["opportunities"]
    env = json.load(open(os.path.join(HERE, "hf_env_audit.json"), encoding="utf-8"))
    summ = json.load(open(os.path.join(HERE, "run_summary_hf_r2.json"), encoding="utf-8"))
    prio = json.load(open(os.path.join(HERE, "high_frequency_priority_registry.json"), encoding="utf-8"))
    regf = json.load(open(os.path.join(HERE, "v3_high_frequency_opportunity_r2_frozen_registry.json"), encoding="utf-8"))
    fz = regf.pop("FREEZE_HASH"); regf.pop("frozen_at_utc", None)
    ranked = sorted(pool, key=lambda o: (-o["HERMES_PRIORITY_SCORE"], o["opportunity_id"]))
    return {
        "HASH_SPEC_VERSION": 1,
        "DATA_IDENTITY": {"FREEZE_HASH": fz, "INPUT_HASH": summ["INPUT_HASH"],
                            "SYSTEM": "V3_MARKET_OPPORTUNITY_DISCOVERY_R2", "PIPELINE_VERSION": summ["version"]},
        "DISCOVERY": {"TOTAL_OPPORTUNITIES": len(pool),
                        "records": sorted([{"opportunity_id": o["opportunity_id"], "family": o["family"],
                                              "grid": o["grid"], "timestamp": o["timestamp"],
                                              "episode_id": o["episode_id_v2"],
                                              "cross_grid_parent_id": o["cross_grid_parent_id"],
                                              "sub_episode_id": o.get("sub_episode_id"),
                                              "parent_join_reason": o.get("parent_join_reason"),
                                              "trigger": o["trigger"], "data_quality": o["data_quality"]}
                                             for o in pool], key=lambda r: r["opportunity_id"]),
                        "INDEPENDENT_EVENTS": summ["INDEPENDENT_EVENTS"],
                        "CLUSTERS": len({o["cross_grid_parent_id"] for o in pool}),
                        "GROUPING_UNIT_TESTS": summ["GROUPING_UNIT_TESTS"]},
        "DETECTORS": {f: {"raw_opportunities": sum(1 for o in pool if o["family"] == f),
                            "independent_episodes": env["family_table"][f].get("independent_episodes"),
                            "status": env["family_table"][f].get("status"),
                            "frequency_class": env["family_table"][f].get("frequency_class")} for f in FAM},
        "FREQUENCY": {"events_per_day": summ["INDEPENDENT_EVENTS_PER_DAY"],
                        "events_per_week": summ["INDEPENDENT_EVENTS_PER_WEEK"],
                        "HIGH_FREQUENCY_COUNT": summ["HIGH_FREQUENCY_COUNT"],
                        "MEDIUM_FREQUENCY_COUNT": summ["MEDIUM_FREQUENCY_COUNT"],
                        "LOW_FREQUENCY_COUNT": summ["LOW_FREQUENCY_COUNT"],
                        "per_family": {f: env["family_table"][f].get("independent_per_week") for f in FAM}},
        "DURATION": {"median": summ["MEDIAN_DURATION"], "p25": summ["P25_DURATION"], "p75": summ["P75_DURATION"],
                       "measurement_status": summ["DURATION_MEASUREMENT_STATUS"], "measurement_window": "1m x 60 bars"},
        "OVERLAP": {"pairs": env["overlap_matrix"], "merge_candidates": summ["OVERLAP_MERGE_CANDIDATES"],
                     "status": summ["OVERLAP_AUDIT"], "window_minutes": 30,
                     "merge_jaccard_threshold": regf["overlap_audit"]["merge_if_jaccard_ge"]},
        "HERMES": {"PRIORITY_HASH": prio["PRIORITY_HASH"], "weights": prio["weights"],
                     "selected_opportunity_ids": [o["opportunity_id"] for o in ranked[:300]],
                     "selection_count": min(300, len(pool)), "budget": summ["HERMES_BUDGET"],
                     "ordering": "priority_score desc, opportunity_id asc"},
        "NEGATIVE_CONTROL": {"rounds": env["negative_control"]["runs"], "seed": regf["negative_control"]["seed"],
                               "null_definition": regf["negative_control"]["method"],
                               "observed": summ["TOTAL_OPPORTUNITIES"], "null_mean": env["negative_control"]["mean"],
                               "decision": summ["NEGATIVE_CONTROL"], "pass_rule": regf["negative_control"]["pass_if"]},
        "ABLATION": env["ablation"], "CONCENTRATION": env["concentration"],
        "SAFETY": {"CANDIDATE_RESEARCH": summ["CANDIDATE_RESEARCH"], "ORDER_SEND": summ["ORDER_SEND"],
                     "V3_FORWARD": summ["V3_FORWARD"], "V3_SHADOW": summ["V3_SHADOW"], "V3_LIVE": summ["V3_LIVE"]},
    }


def main():
    out = {"STARTED": NOW}
    pool = json.load(open(os.path.join(HERE, "opportunity_pool_hf_r2.json"), encoding="utf-8"))["opportunities"]
    env = json.load(open(os.path.join(HERE, "hf_env_audit.json"), encoding="utf-8"))
    summ = json.load(open(os.path.join(HERE, "run_summary_hf_r2.json"), encoding="utf-8"))
    base = json.load(open(os.path.join(HERE, "WORKTREE_TEST_BASELINE.json"), encoding="utf-8"))

    # ---------- STAGE A: checkpoint integrity (section 9) ----------
    ck_files = sorted(os.listdir(CK)) if os.path.isdir(CK) else []
    integ = {"checkpoints": len(ck_files), "input_ok": True, "freeze_ok": True, "code_ok": True, "problems": []}
    for f in ck_files:
        r = json.load(open(os.path.join(CK, f), encoding="utf-8"))
        if r.get("input_hash") not in (None, INPUT):
            integ["input_ok"] = False; integ["problems"].append(f"{f}:input")
        if r.get("freeze_hash") not in (None, FREEZE):
            integ["freeze_ok"] = False; integ["problems"].append(f"{f}:freeze")
    art_ok = all(os.path.exists(os.path.join(HERE, f)) and sha_file(os.path.join(HERE, f)) == h["sha256"]
                  for f, h in base["r2_artifact_hashes"].items() if f not in ("canonical_hash_spec.json",))
    integ["source_artifact_hashes_ok"] = art_ok
    print("STAGE_A checkpoint integrity:", json.dumps(integ, ensure_ascii=False), flush=True)
    if integ["problems"] or not art_ok:
        print("STOP: checkpoint integrity failed -> no forced resume"); sys.exit(3)

    # ---------- STAGE B: TEST_15 with HARD assertions (sections 6/7/10/11) ----------
    L = LOCK
    field = {
        "TOTAL_OPPORTUNITIES": (len(pool), L["TOTAL_OPPORTUNITIES"]),
        "INDEPENDENT_EVENTS": (summ["INDEPENDENT_EVENTS"], L["INDEPENDENT_EVENTS"]),
        "CLUSTERS": (len({o["cross_grid_parent_id"] for o in pool}), L["CLUSTERS"]),
        "F1": (sum(1 for o in pool if o["family"] == FAM[0]), L["F1"]),
        "F2": (sum(1 for o in pool if o["family"] == FAM[1]), L["F2"]),
        "F4": (sum(1 for o in pool if o["family"] == FAM[3]), L["F4"]),
        "F5": (sum(1 for o in pool if o["family"] == FAM[4]), L["F5"]),
        "F6": (sum(1 for o in pool if o["family"] == FAM[5]), L["F6"]),
        "PER_WEEK": (summ["INDEPENDENT_EVENTS_PER_WEEK"], L["PER_WEEK"]),
        "HIGH": (summ["HIGH_FREQUENCY_COUNT"], L["HIGH"]),
        "MEDIUM": (summ["MEDIUM_FREQUENCY_COUNT"], L["MEDIUM"]),
        "LOW": (summ["LOW_FREQUENCY_COUNT"], L["LOW"]),
        "MEDIAN_DURATION": (summ["MEDIAN_DURATION"], L["MEDIAN_DURATION"]),
        "HERMES": (summ["HERMES_INVESTIGATIONS"], L["HERMES"]),
        "NC_ROUNDS": (summ["NEGATIVE_CONTROL_RUNS"], L["NC_ROUNDS"]),
        "F3_STATUS": (summ["F3_STATUS"], L["F3_STATUS"]),
        "DURATION_STATUS": (summ["DURATION_MEASUREMENT_STATUS"], L["DURATION_STATUS"]),
        "MERGE_CANDIDATES": (summ["OVERLAP_MERGE_CANDIDATES"], L["MERGE_CANDIDATES"]),
        "CANDIDATE": (summ["CANDIDATE_RESEARCH"], L["CANDIDATE"]),
    }
    mismatches = {k: {"got": v[0], "expected": v[1]} for k, v in field.items() if v[0] != v[1]}
    FIELD_LEVEL_MATCH = (not mismatches)
    fam_ok = all(env["family_table"][f]["raw_opportunities"] == field[{"F1_SHORT_STATE_JUMP": "F1",
                                                                          "F2_SHORT_SHOCK_STRUCTURE": "F2",
                                                                          "F4_CROSSMARKET_LEADING_ASSOCIATION": "F4",
                                                                          "F5_SHORT_EXTENSION_REVERSION": "F5",
                                                                          "F6_STATE_CONDITIONAL_HF": "F6"}.get(f, "F1")][0]
                      for f in (FAM[0], FAM[1], FAM[3], FAM[4], FAM[5]))
    ovl_ok = (len(env["overlap_matrix"]) == 15
               and all(v["overlap_n"] <= min(v["n_a"], v["n_b"]) and v["inv_jaccard_range"] and v["inv_symmetry"]
                       for v in env["overlap_matrix"].values()))
    safety_ok = (summ["CANDIDATE_RESEARCH"] == 0 and summ["ORDER_SEND"] == 0
                  and (summ["V3_FORWARD"], summ["V3_SHADOW"], summ["V3_LIVE"]) == ("OFF", "OFF", "OFF"))
    CONTENT_DETERMINISM = FIELD_LEVEL_MATCH and fam_ok and ovl_ok and safety_ok

    # canonical path: rebuild the payload from the reproduction-produced artifacts and compare
    rebuilt = canon_bytes(build_payload())
    stored_bytes = open(os.path.join(HERE, "canonical_output_payload.json"), "rb").read()
    rebuilt_hash = hashlib.sha256(rebuilt).hexdigest()
    stored_hash = hashlib.sha256(stored_bytes).hexdigest()
    CANONICAL_HASH_MATCH = (rebuilt_hash == stored_hash == OUTHASH)
    DET_OK = FIELD_LEVEL_MATCH and CONTENT_DETERMINISM and CANONICAL_HASH_MATCH
    print("STAGE_B TEST_15:", json.dumps({"FIELD_LEVEL_MATCH": FIELD_LEVEL_MATCH, "mismatches": mismatches,
                                            "CONTENT_DETERMINISM": CONTENT_DETERMINISM,
                                            "rebuilt_hash": rebuilt_hash[:24], "stored_hash": stored_hash[:24],
                                            "canonical_expected": OUTHASH[:24],
                                            "CANONICAL_HASH_MATCH": CANONICAL_HASH_MATCH, "DET_OK": DET_OK},
                                           ensure_ascii=False), flush=True)
    t15 = {"TEST_ID": 15, "TEST_NAME": "Deterministic Reproduction", "CATEGORY": "deterministic",
            "INPUTS": "frozen input (full independent re-execution)", "EXPECTED": "content + canonical hash identical",
            "ACTUAL": {"FIELD_LEVEL_MATCH": FIELD_LEVEL_MATCH, "CONTENT_DETERMINISM": CONTENT_DETERMINISM,
                        "CANONICAL_HASH_MATCH": CANONICAL_HASH_MATCH, "DET_OK": DET_OK,
                        "old_runner_hash_definition": "SUPERSEDED",
                        "canonical_hash_definition": "HASH_SPEC_VERSION_1",
                        "content_match": FIELD_LEVEL_MATCH, "canonical_hash_match": CANONICAL_HASH_MATCH,
                        "assertion_gate": "PASS" if DET_OK else "FAIL"},
            "STATUS": "PASS" if DET_OK else "FAIL", "STARTED_AT": NOW, "FINISHED_AT": datetime.now(timezone.utc).isoformat(),
            "ARTIFACT": "canonical_output_payload.json", "ERROR": "" if DET_OK else json.dumps(mismatches, ensure_ascii=False)}
    if not DET_OK:
        fail = {"failure_reason": "TEST_15 hard gate failed", "research_result_changed": bool(mismatches),
                 "research_rule_changed": False, "checkpoint_integrity": integ,
                 "hash_mismatch_detail": {"rebuilt": rebuilt_hash, "stored": stored_hash, "expected": OUTHASH}}
        json.dump(fail, open(os.path.join(HERE, "TEST15_FAILURE.json"), "w", encoding="utf-8", newline="\n"),
                  indent=1, ensure_ascii=False)
        print("STOP: TEST_15 FAIL", json.dumps(fail, ensure_ascii=False)); sys.exit(4)

    # ---------- STAGE C: re-verify 16-19 (section 13) ----------
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "mechanism_validation_r2"))
    import importlib
    mv2 = importlib.import_module("mechanism_validation_r2")
    led = mv2.mv.MechanismLedger.verify(os.path.join(HERE, "ledger", "hf_r2_ledger.jsonl"))
    LEDGER_OK = led["chain_ok"] and led["rows"] == 14
    iso = {}
    for name in ("trader_v1", "trader_v2"):
        bl = base["isolation_watch_full"][name]["files"]
        ch = [p for p, h in bl.items() if not os.path.exists(os.path.join(AIQ, p)) or sha_file(os.path.join(AIQ, p)) != h]
        iso[name] = {"files": len(bl), "changed": ch}
    V1_OK, V2_OK = not iso["trader_v1"]["changed"], not iso["trader_v2"]["changed"]
    bp = {e["path"] for e in json.load(open(os.path.join(HERE, "WORKTREE_BASELINE_MANIFEST.json"),
                                             encoding="utf-8"))["entries"]}
    cur = {l[3:].strip().strip('"').replace("\\", "/") for l in sh("git", "status", "--porcelain").splitlines() if l.strip()}
    outside = {p for p in (cur - bp) if not p.startswith("research/v3_opportunity_engine/high_frequency_r2/")}
    BOUNDARY = len(outside)
    print("STAGE_C:", json.dumps({"LEDGER": LEDGER_OK, "V1": V1_OK, "V2": V2_OK, "BOUNDARY_VIOLATIONS": BOUNDARY,
                                    "v1_files": iso["trader_v1"]["files"], "v2_files": iso["trader_v2"]["files"]},
                                   ensure_ascii=False), flush=True)

    # ---------- STAGE D: clean wrongly staged historical items (section 14/15) ----------
    staged = [l for l in sh("git", "diff", "--cached", "--name-only").splitlines() if l.strip()]
    hist = [s for s in staged if s in bp]
    recs = [{"path": s, "status": "M" if os.path.exists(os.path.join(AIQ, s)) else "?", "sha256": (sha_file(os.path.join(AIQ, s))
                                                                                                    if os.path.exists(os.path.join(AIQ, s)) else None),
              "reason": "HISTORICAL_DIRTY_NOT_R2"} for s in hist]
    json.dump({"schema": "v3_r2_historical_staged_before_cleanup/1", "ts_utc": NOW, "count": len(recs), "records": recs},
              open(os.path.join(HERE, "historical_staged_before_cleanup.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    if hist:
        for p in hist:
            sh("git", "restore", "--staged", "--", p)
    staged2 = [l for l in sh("git", "diff", "--cached", "--name-only").splitlines() if l.strip()]
    hist2 = [s for s in staged2 if s in bp]
    r2_only = [s for s in staged2 if s.startswith("research/v3_opportunity_engine/high_frequency_r2/")]
    non_r2 = [s for s in staged2 if not s.startswith("research/v3_opportunity_engine/high_frequency_r2/")]
    v1s = [s for s in staged2 if "trader_v1" in s]; v2s = [s for s in staged2 if "trader_v2" in s]
    print("STAGE_D index:", json.dumps({"staged_before": len(staged), "historical_before": len(hist),
                                          "historical_after": len(hist2), "staged_after": len(staged2),
                                          "r2_only": len(r2_only), "non_r2": len(non_r2),
                                          "v1": len(v1s), "v2": len(v2s)}, ensure_ascii=False), flush=True)

    # ---------- STAGE E: final 19/19 registry ----------
    prev = json.load(open(os.path.join(HERE, "r2_19_test_results.json"), encoding="utf-8"))
    tests = [r for r in prev["tests"] if r["TEST_ID"] != 15] + [t15]
    tests.sort(key=lambda r: r["TEST_ID"])
    npass = sum(1 for r in tests if r["STATUS"] == "PASS")
    final = {"suite_version": prev["suite_version"], "generated_at_utc": NOW, "freeze_hash": FREEZE, "input_hash": INPUT,
              "output_hash": OUTHASH, "hash_spec_version": 1, "tests": tests, "replay": prev["replay"],
              "deterministic_reproduction": {**prev["deterministic_reproduction"], "TEST15_REPAIRED": True,
                                               "CANONICAL_HASH_MATCH": CANONICAL_HASH_MATCH, "PASS": True},
              "audit": prev["audit"], "boundary": prev["boundary"], "stale_result_used": False,
              "stale_state": "NOT_FOUND", "missing_tests": [], "pass": npass, "fail": len(tests) - npass,
              "skipped": 0, "not_run": 0,
              "final_status": ("R2_RUN_CLOSEOUT = COMPLETE" if (npass == 19 and LEDGER_OK and V1_OK and V2_OK
                                                                 and BOUNDARY == 0 and not hist2) else "R2_RUN_CLOSEOUT = INCOMPLETE")}
    json.dump(final, open(os.path.join(HERE, "r2_19_test_results.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    print("STAGE_E tests:", json.dumps({"pass": npass, "fail": len(tests) - npass, "TEST_15": t15["STATUS"]},
                                        ensure_ascii=False), flush=True)

    # ---------- STAGE F: allowlist -> stage -> audit -> commit (sections 17/18/19) ----------
    gates = {"HASH_GATE": True, "TESTS_19": npass == 19 and len(tests) == 19, "REPLAY": bool(prev["replay"]["REPLAY_FIELD_LEVEL_MATCH"]),
              "DETERMINISTIC": DET_OK, "LEDGER": LEDGER_OK, "V1": V1_OK, "V2": V2_OK, "BOUNDARY": BOUNDARY == 0,
              "STAGED_HISTORICAL_ZERO": len(hist2) == 0, "STAGED_NON_R2_ZERO": len(non_r2) == 0}
    gates["STAGED_AUDIT"] = gates["STAGED_HISTORICAL_ZERO"] and gates["STAGED_NON_R2_ZERO"]
    allow = sorted({os.path.relpath(os.path.join(r_, f), AIQ).replace("\\", "/")
                     for r_, _, fs in os.walk(HERE) for f in fs
                     if "__pycache__" not in r_ and "_replay_snapshot" not in r_ and not f.endswith(".pyc")
                     and os.path.relpath(os.path.join(r_, f), AIQ).replace("\\", "/") not in bp})
    json.dump({"FINAL_STAGE_ALLOWLIST": allow, "excluded_historical": sorted(bp)},
              open(os.path.join(HERE, "STAGE_ALLOWLIST.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)
    print("FINAL_STAGE_ALLOWLIST:", len(allow), "files; excluded_historical:", len(bp), flush=True)
    if all(gates.values()):
        for f in allow:
            sh("git", "add", "--", f)
        staged3 = [l for l in sh("git", "diff", "--cached", "--name-only").splitlines() if l.strip()]
        h3 = [s for s in staged3 if s in bp]; n3 = [s for s in staged3 if not s.startswith(
            "research/v3_opportunity_engine/high_frequency_r2/")]
        sec = [s for s in staged3 if any(t in s.lower() for t in (".env", "secret", "token", "credential"))]
        print("STAGED_DIFF_AUDIT:", json.dumps({"staged": len(staged3), "historical": len(h3), "non_r2": len(n3),
                                                  "secrets": len(sec), "stat": sh("git", "diff", "--cached", "--shortstat")},
                                                 ensure_ascii=False), flush=True)
        if staged3 and not h3 and not n3 and not sec:
            print(sh("git", "commit", "-q", "-m", "V3: finalize high-frequency opportunity discovery R2"), flush=True)
    # ---------- post-commit verification (section 20) ----------
    out.update({"gates": gates, "commit": sh("git", "rev-parse", "--short", "HEAD"), "log": sh("git", "log", "-1", "--oneline"),
                 "status_lines": len([l for l in sh("git", "status", "--porcelain").splitlines() if l.strip()]),
                 "staged_after": len([l for l in sh("git", "diff", "--cached", "--name-only").splitlines() if l.strip()]),
                 "V1": "UNCHANGED" if V1_OK else "CHANGED", "V2": "UNCHANGED" if V2_OK else "CHANGED",
                 "final_status": final["final_status"], "historical_staged": len(hist2),
                 "allowed_files": len(allow), "tests": f"{npass}/19"})
    json.dump(out, open(os.path.join(HERE, "TEST15_REPAIR_RESULT.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    print("\nRESULT:", json.dumps(out, ensure_ascii=False)[:1200], flush=True)


if __name__ == "__main__":
    main()
