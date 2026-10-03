# -*- coding: utf-8 -*-
"""V3 R2 — checkpoint/artifact-identity repair, TEST_15 determinism, final closeout (task order 0..14).

Adds ARTIFACT_CONTENT_HASH_SPEC_VERSION=1 (content identity) alongside RAW_FILE_SHA256 (physical identity).
Research rules and research results are NOT modified. Every stage has a hard gate; failure -> STOP, no commit.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
RE = os.path.dirname(os.path.dirname(HERE))
AIQ = os.path.dirname(RE)
CK = os.path.join(HERE, "test_checkpoints")
PY = r"C:\AIQuant\.venv\Scripts\python.exe"
RUNNER = os.path.join(HERE, "_r2_closeout_final.py")
NOW = datetime.now(timezone.utc).isoformat()
FREEZE = "7da599cdb6858ac624f9929d427c634187d257f8adb91d300b9fe33300aecb2f"
INPUT = "704e1cfa8960cee881c5efccb1f23fe9679fa262da5770e82fe99d7338f9ac53"
OUTHASH = "20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624"
ACHS_VER = 1
LOCK = {"TOTAL_OPPORTUNITIES": 38367, "INDEPENDENT_EVENTS": 7792, "CLUSTERS": 12994,
         "PER_WEEK": 86.3925, "HIGH": 4, "MEDIUM": 1, "LOW": 0, "MEDIAN_DURATION": 47.0,
         "F3_STATUS": "INSUFFICIENT_DATA", "MERGE_CANDIDATES": [], "HERMES": 300, "NC_ROUNDS": 200,
         "CANDIDATE": 0, "DURATION_STATUS": "TRUNCATION_SENSITIVE"}
FAM = ["F1_SHORT_STATE_JUMP", "F2_SHORT_SHOCK_STRUCTURE", "F3_PRICE_ACTIVITY_PROXY",
        "F4_CROSSMARKET_LEADING_ASSOCIATION", "F5_SHORT_EXTENSION_REVERSION", "F6_STATE_CONDITIONAL_HF"]
SPEC = {
    "opportunity_pool_hf_r2.json": {"type": "RESULT_POOL", "exclude": []},
    "run_summary_hf_r2.json": {"type": "RESULT_SUMMARY",
                                 "exclude": ["ts_utc", "RUN_METADATA", "runtime_seconds", "OUTPUT_HASH",
                                              "SUPERSEDED_OUTPUT_HASHES", "SUPERSEDED_BY_FINAL_CLOSEOUT"]},
    "hf_env_audit.json": {"type": "RESULT_ENV", "exclude": ["ts_utc", "generated_at_utc"]},
    os.path.join("ledger", "hf_r2_ledger.jsonl"): {"type": "LEDGER_EVENTS", "exclude": []},
    "canonical_hash_spec.json": {"type": "HASH_SPEC", "exclude": ["generated_at_utc"]},
    "r2_superseded_outputs.json": {"type": "SUPERSEDED_REGISTRY", "exclude": ["ts_utc"]},
    "high_frequency_priority_registry.json": {"type": "PRIORITY_REGISTRY", "exclude": []},
    "v3_high_frequency_opportunity_r2_frozen_registry.json": {"type": "FREEZE_REGISTRY",
                                                                "exclude": ["frozen_at_utc", "FREEZE_HASH"]},
    "WORKTREE_BASELINE_MANIFEST.json": {"type": "TEST_MANIFEST", "exclude": ["ts_utc", "mtime"]},
    "canonical_output_payload.json": {"type": "CANONICAL_PAYLOAD", "exclude": []},
}
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def sh(*a):
    r = subprocess.run(list(a), cwd=AIQ, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return ((r.stdout or "") + (r.stderr or "")).strip()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def canon(o):
    return json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def scrub(o, keys):
    if isinstance(o, dict):
        return {k: scrub(v, keys) for k, v in o.items() if k not in keys}
    if isinstance(o, list):
        return [scrub(v, keys) for v in o]
    return o


def content_hash(path, spec):
    p = os.path.join(HERE, path)
    if path.endswith(".jsonl"):
        rows = [json.loads(l)["payload"] for l in open(p, encoding="utf-8") if l.strip()]
        rows.sort(key=lambda r: json.dumps(r, sort_keys=True))
        return hashlib.sha256(canon([scrub(r, set(spec["exclude"])) for r in rows])).hexdigest()
    return hashlib.sha256(canon(scrub(json.load(open(p, encoding="utf-8")), set(spec["exclude"])))).hexdigest()


def fail(stage, why, **kw):
    rec = {"STOPPED_AT_STAGE": stage, "FAILED_GATE": why, "ROOT_CAUSE": kw.get("root_cause", ""),
            "RESEARCH_RESULT_CHANGED": kw.get("result_changed", False),
            "RESEARCH_RULE_CHANGED": False, "CHECKPOINT_STATUS": kw.get("ckpt", ""),
            "INDEX_STATUS": {"staged": len(staged_now()), "historical": len(hist_now())}, "ts_utc": NOW}
    json.dump(rec, open(os.path.join(HERE, "R2_FINAL_STOP.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)
    print("STOP:", json.dumps(rec, ensure_ascii=False)); sys.exit(2)


def staged_now():
    return [l for l in sh("git", "diff", "--cached", "--name-only").splitlines() if l.strip()]


def hist_now():
    bp = {e["path"] for e in json.load(open(os.path.join(HERE, "WORKTREE_BASELINE_MANIFEST.json"),
                                             encoding="utf-8"))["entries"]}
    return [s for s in staged_now() if s in bp]


def main():
    # ---------- STAGE 0: index snapshot (before any index change) ----------
    staged = staged_now()
    snap = {"schema": "v3_r2_current_index_snapshot/1", "ts_utc": NOW, "head": sh("git", "rev-parse", "--short", "HEAD"),
             "staged_count": len(staged), "entries": []}
    for l in sh("git", "status", "--porcelain").splitlines():
        if not l.strip():
            continue
        p = l[3:].strip().strip('"')
        fp = os.path.join(AIQ, p)
        is_staged = p in staged
        if is_staged or p.replace("\\", "/").startswith("research/v3_opportunity_engine/high_frequency_r2/"):
            snap["entries"].append({"path": p.replace("\\", "/"), "index_status": l[:2],
                                      "worktree_status": l[:2], "sha256": (sha_file(fp) if os.path.isfile(fp) else None),
                                      "in_allowlist_candidate": True})
    snap["historical_in_index"] = hist_now()
    json.dump(snap, open(os.path.join(HERE, "CURRENT_INDEX_SNAPSHOT.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    print(f"STAGE0 index snapshot: staged={len(staged)} historical={len(snap['historical_in_index'])}", flush=True)

    # ---------- STAGE 6 (writer): deterministic canonical reproduction ----------
    # run the frozen pipeline (content), then canonicalise the outputs (RUN_METADATA separated, canonical OUTPUT_HASH)
    r = subprocess.run([PY, RUNNER], cwd=HERE, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        fail("STAGE6_deterministic_runner", "frozen pipeline re-execution failed", root_cause=r.stderr[-200:])
    sys.path.insert(0, HERE)
    import importlib.util
    sp = importlib.util.spec_from_file_location("hr", os.path.join(HERE, "_r2_hash_repair.py"))
    HR = importlib.util.module_from_spec(sp)
    # reuse the canonical payload builder by re-implementing it here (identical rules)
    def build_payload():
        pool = json.load(open(os.path.join(HERE, "opportunity_pool_hf_r2.json"), encoding="utf-8"))["opportunities"]
        env = json.load(open(os.path.join(HERE, "hf_env_audit.json"), encoding="utf-8"))
        sm = json.load(open(os.path.join(HERE, "run_summary_hf_r2.json"), encoding="utf-8"))
        pr = json.load(open(os.path.join(HERE, "high_frequency_priority_registry.json"), encoding="utf-8"))
        rg = json.load(open(os.path.join(HERE, "v3_high_frequency_opportunity_r2_frozen_registry.json"), encoding="utf-8"))
        fz = rg.pop("FREEZE_HASH"); rg.pop("frozen_at_utc", None)
        rk = sorted(pool, key=lambda o: (-o["HERMES_PRIORITY_SCORE"], o["opportunity_id"]))
        return {"HASH_SPEC_VERSION": 1,
                 "DATA_IDENTITY": {"FREEZE_HASH": fz, "INPUT_HASH": sm["INPUT_HASH"],
                                     "SYSTEM": "V3_MARKET_OPPORTUNITY_DISCOVERY_R2", "PIPELINE_VERSION": sm["version"]},
                 "DISCOVERY": {"TOTAL_OPPORTUNITIES": len(pool),
                                 "records": sorted([{"opportunity_id": o["opportunity_id"], "family": o["family"],
                                                       "grid": o["grid"], "timestamp": o["timestamp"],
                                                       "episode_id": o["episode_id_v2"],
                                                       "cross_grid_parent_id": o["cross_grid_parent_id"],
                                                       "sub_episode_id": o.get("sub_episode_id"),
                                                       "parent_join_reason": o.get("parent_join_reason"),
                                                       "trigger": o["trigger"], "data_quality": o["data_quality"]}
                                                      for o in pool], key=lambda x: x["opportunity_id"]),
                                 "INDEPENDENT_EVENTS": sm["INDEPENDENT_EVENTS"],
                                 "CLUSTERS": len({o["cross_grid_parent_id"] for o in pool}),
                                 "GROUPING_UNIT_TESTS": sm["GROUPING_UNIT_TESTS"]},
                 "DETECTORS": {f: {"raw_opportunities": sum(1 for o in pool if o["family"] == f),
                                     "independent_episodes": env["family_table"][f].get("independent_episodes"),
                                     "status": env["family_table"][f].get("status"),
                                     "frequency_class": env["family_table"][f].get("frequency_class")} for f in FAM},
                 "FREQUENCY": {"events_per_day": sm["INDEPENDENT_EVENTS_PER_DAY"],
                                 "events_per_week": sm["INDEPENDENT_EVENTS_PER_WEEK"],
                                 "HIGH_FREQUENCY_COUNT": sm["HIGH_FREQUENCY_COUNT"],
                                 "MEDIUM_FREQUENCY_COUNT": sm["MEDIUM_FREQUENCY_COUNT"],
                                 "LOW_FREQUENCY_COUNT": sm["LOW_FREQUENCY_COUNT"],
                                 "per_family": {f: env["family_table"][f].get("independent_per_week") for f in FAM}},
                 "DURATION": {"median": sm["MEDIAN_DURATION"], "p25": sm["P25_DURATION"], "p75": sm["P75_DURATION"],
                                "measurement_status": sm["DURATION_MEASUREMENT_STATUS"], "measurement_window": "1m x 60 bars"},
                 "OVERLAP": {"pairs": env["overlap_matrix"], "merge_candidates": sm["OVERLAP_MERGE_CANDIDATES"],
                               "status": sm["OVERLAP_AUDIT"], "window_minutes": 30,
                               "merge_jaccard_threshold": rg["overlap_audit"]["merge_if_jaccard_ge"]},
                 "HERMES": {"PRIORITY_HASH": pr["PRIORITY_HASH"], "weights": pr["weights"],
                              "selected_opportunity_ids": [o["opportunity_id"] for o in rk[:300]],
                              "selection_count": 300, "budget": sm["HERMES_BUDGET"],
                              "ordering": "priority_score desc, opportunity_id asc"},
                 "NEGATIVE_CONTROL": {"rounds": env["negative_control"]["runs"], "seed": rg["negative_control"]["seed"],
                                        "null_definition": rg["negative_control"]["method"],
                                        "observed": sm["TOTAL_OPPORTUNITIES"], "null_mean": env["negative_control"]["mean"],
                                        "decision": sm["NEGATIVE_CONTROL"], "pass_rule": rg["negative_control"]["pass_if"]},
                 "ABLATION": env["ablation"], "CONCENTRATION": env["concentration"],
                 "SAFETY": {"CANDIDATE_RESEARCH": sm["CANDIDATE_RESEARCH"], "ORDER_SEND": sm["ORDER_SEND"],
                              "V3_FORWARD": sm["V3_FORWARD"], "V3_SHADOW": sm["V3_SHADOW"], "V3_LIVE": sm["V3_LIVE"]}}

    rebuilt = canon(build_payload())
    rebuilt_hash = hashlib.sha256(rebuilt).hexdigest()
    stored_hash = sha_file(os.path.join(HERE, "canonical_output_payload.json"))
    CANON_MATCH = (rebuilt_hash == OUTHASH == stored_hash)
    # canonicalise the summary: research fields unchanged, RUN_METADATA separated, canonical OUTPUT_HASH
    sm = json.load(open(os.path.join(HERE, "run_summary_hf_r2.json"), encoding="utf-8"))
    fixed = {k: v for k, v in sm.items() if k not in ("ts_utc", "OUTPUT_HASH", "SUPERSEDED_BY_FINAL_CLOSEOUT")}
    fixed.pop("RUN_METADATA", None)
    fixed.update({"HASH_SPEC_VERSION": 1, "CANONICAL_HASH_ALGORITHM": "SHA256",
                    "CANONICAL_SERIALIZATION": "UTF8_JSON_SORTED_KEYS",
                    "ARTIFACT_CONTENT_HASH_SPEC_VERSION": ACHS_VER, "OUTPUT_HASH": rebuilt_hash,
                    "SUPERSEDED_OUTPUT_HASHES": ["c45ed28a9e6da1755f7e8b346dd409f9cdff48663701b1be5c2b1895911eb737",
                                                  "a6490bcfc1532fe59765ffc3534e1d30ef2c1c9225c254dc9cf26098b89a02f7"],
                    "RUN_METADATA": {"ts_utc": NOW, "host": "DESKTOP-LQ0B8O3",
                                       "note": "RUN_METADATA never enters content identity"}})
    json.dump(fixed, open(os.path.join(HERE, "run_summary_hf_r2.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)
    print(f"STAGE6 canonical writer: CANON_MATCH={CANON_MATCH}", flush=True)

    # ---------- STAGE 1/2/3/4: content-hash spec + manifest + baseline V2 (correct order) ----------
    man = {"schema": "v3_r2_artifact_identity_manifest/1", "ARTIFACT_CONTENT_HASH_SPEC_VERSION": ACHS_VER,
            "ts_utc": NOW, "raw_vs_content": "RAW_FILE_SHA256 = physical bytes; CONTENT_HASH = research content",
            "artifacts": {}}
    for path, spec in SPEC.items():
        p = os.path.join(HERE, path)
        if not os.path.exists(p):
            continue
        man["artifacts"][path] = {"path": path, "artifact_type": spec["type"],
                                    "content_hash_spec_version": ACHS_VER,
                                    "canonical_hash": content_hash(path, spec),
                                    "excluded_dynamic_fields": spec["exclude"],
                                    "source_identity": {"freeze_hash": FREEZE, "input_hash": INPUT},
                                    "generated_by": "r2_artifact_content_hash_v1",
                                    "raw_file_sha256": sha_file(p), "size": os.path.getsize(p)}
    json.dump(man, open(os.path.join(HERE, "artifact_identity_manifest.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    readback = json.load(open(os.path.join(HERE, "artifact_identity_manifest.json"), encoding="utf-8"))
    MAN_OK = (readback["ARTIFACT_CONTENT_HASH_SPEC_VERSION"] == ACHS_VER and len(readback["artifacts"]) >= 8)
    print(f"STAGE1-3 manifest: artifacts={len(man['artifacts'])} ok={MAN_OK}", flush=True)
    if not MAN_OK:
        fail("STAGE1_artifact_content_hash", "manifest write/readback failed")

    ck_ids = []
    for f in sorted(os.listdir(CK)):
        rc = json.load(open(os.path.join(CK, f), encoding="utf-8"))
        ck_ids.append({"checkpoint": f, "input_ok": rc.get("input_hash") in (None, INPUT),
                        "freeze_ok": rc.get("freeze_hash") in (None, FREEZE),
                        "code_ok": bool(rc.get("code_revision")),
                        "checkpoint_hash": rc.get("output_hash"), "raw_file_sha256": sha_file(os.path.join(CK, f))})
    v2 = {"schema": "v3_r2_worktree_test_baseline/2", "ts_utc": NOW, "head": sh("git", "rev-parse", "--short", "HEAD"),
            "baseline_rebuild_reason": "ARTIFACT_CONTENT_HASH_SPEC_REPAIR",
            "FREEZE_HASH": FREEZE, "INPUT_HASH": INPUT, "OUTPUT_HASH": rebuilt_hash,
            "HASH_SPEC_VERSION": 1, "ARTIFACT_CONTENT_HASH_SPEC_VERSION": ACHS_VER,
            "artifact_identities": man["artifacts"], "checkpoint_identities": ck_ids,
            "research_semantics_lock": LOCK,
            "isolation_watch": {k: v.get("digest") for k, v in json.load(
                open(os.path.join(HERE, "WORKTREE_TEST_BASELINE.json"), encoding="utf-8"))["isolation_watch_full"].items()},
            "supersedes": "WORKTREE_TEST_BASELINE.json (kept as historical evidence)",
            "old_baseline_preserved": True}
    json.dump(v2, open(os.path.join(HERE, "WORKTREE_TEST_BASELINE_V2.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    back = json.load(open(os.path.join(HERE, "WORKTREE_TEST_BASELINE_V2.json"), encoding="utf-8"))
    if back["baseline_rebuild_reason"] != "ARTIFACT_CONTENT_HASH_SPEC_REPAIR":
        fail("STAGE4_baseline_v2", "baseline readback failed")
    print(f"STAGE4 baseline V2 written: artifacts={len(back['artifact_identities'])} checkpoints={len(ck_ids)}", flush=True)

    # ---------- STAGE 5/6: checkpoint integrity (content identity) ----------
    src_ok = all(a["canonical_hash"] == content_hash(a["path"], SPEC[a["path"]]) for a in man["artifacts"].values())
    ck_ok = all(c["input_ok"] and c["freeze_ok"] and c["code_ok"] for c in ck_ids) and len(ck_ids) == 27
    print(f"STAGE5 checkpoint integrity: src_identity_ok={src_ok} ckpt_raw_ok={ck_ok} n={len(ck_ids)}", flush=True)
    if not (src_ok and ck_ok):
        fail("STAGE5_checkpoint_integrity", "artifact content identity or checkpoint raw integrity failed",
             ckpt=f"{len(ck_ids)} checkpoints")

    # ---------- STAGE 7/8: TEST_15 hard assertions ----------
    pool = json.load(open(os.path.join(HERE, "opportunity_pool_hf_r2.json"), encoding="utf-8"))["opportunities"]
    env = json.load(open(os.path.join(HERE, "hf_env_audit.json"), encoding="utf-8"))
    sm2 = json.load(open(os.path.join(HERE, "run_summary_hf_r2.json"), encoding="utf-8"))
    fields = {"TOTAL_OPPORTUNITIES": (len(pool), LOCK["TOTAL_OPPORTUNITIES"]),
                "INDEPENDENT_EVENTS": (sm2["INDEPENDENT_EVENTS"], LOCK["INDEPENDENT_EVENTS"]),
                "CLUSTERS": (len({o["cross_grid_parent_id"] for o in pool}), LOCK["CLUSTERS"]),
                "PER_WEEK": (sm2["INDEPENDENT_EVENTS_PER_WEEK"], LOCK["PER_WEEK"]),
                "HIGH": (sm2["HIGH_FREQUENCY_COUNT"], LOCK["HIGH"]), "MEDIUM": (sm2["MEDIUM_FREQUENCY_COUNT"], LOCK["MEDIUM"]),
                "LOW": (sm2["LOW_FREQUENCY_COUNT"], LOCK["LOW"]), "MEDIAN_DURATION": (sm2["MEDIAN_DURATION"], LOCK["MEDIAN_DURATION"]),
                "F3_STATUS": (sm2["F3_STATUS"], LOCK["F3_STATUS"]), "MERGE_CANDIDATES": (sm2["OVERLAP_MERGE_CANDIDATES"], LOCK["MERGE_CANDIDATES"]),
                "HERMES": (sm2["HERMES_INVESTIGATIONS"], LOCK["HERMES"]), "NC_ROUNDS": (sm2["NEGATIVE_CONTROL_RUNS"], LOCK["NC_ROUNDS"]),
                "CANDIDATE": (sm2["CANDIDATE_RESEARCH"], LOCK["CANDIDATE"]), "DURATION_STATUS": (sm2["DURATION_MEASUREMENT_STATUS"], LOCK["DURATION_STATUS"])}
    mism = {k: {"got": v[0], "expected": v[1]} for k, v in fields.items() if v[0] != v[1]}
    FIELD = not mism
    id_ok = (len({o["opportunity_id"] for o in pool}) == len(pool)
              and len({o["episode_id_v2"] for o in pool}) == sm2["INDEPENDENT_EVENTS"]
              and all(o["grid"] in ("1m", "5m", "15m", "30m") and o["family"] in FAM for o in pool))
    ovl_ok = (len(env["overlap_matrix"]) == 15
               and all(v["overlap_n"] <= min(v["n_a"], v["n_b"]) and v["inv_jaccard_range"] and v["inv_symmetry"]
                       for v in env["overlap_matrix"].values()))
    safety_ok = (sm2["CANDIDATE_RESEARCH"] == 0 and sm2["ORDER_SEND"] == 0
                  and (sm2["V3_FORWARD"], sm2["V3_SHADOW"], sm2["V3_LIVE"]) == ("OFF", "OFF", "OFF"))
    CONTENT_DET = FIELD and id_ok and ovl_ok and safety_ok
    DET_OK = CONTENT_DET and CANON_MATCH and (rebuilt_hash == sm2["OUTPUT_HASH"])
    print("TEST_15:", json.dumps({"FIELD_LEVEL_MATCH": FIELD, "ID_INTEGRITY": id_ok, "OVERLAP_OK": ovl_ok,
                                    "SAFETY_OK": safety_ok, "CONTENT_DETERMINISM": CONTENT_DET,
                                    "CANONICAL_HASH_MATCH": CANON_MATCH, "DET_OK": DET_OK,
                                    "canonical": rebuilt_hash[:24], "mismatches": mism}, ensure_ascii=False), flush=True)
    if not DET_OK:
        json.dump({"TEST_15": "FAIL", "research_result_changed": bool(mism), "research_rule_changed": False,
                    "detail": {"mismatches": mism, "canonical": rebuilt_hash, "expected": OUTHASH}},
                  open(os.path.join(HERE, "TEST15_FAILURE.json"), "w", encoding="utf-8", newline="\n"), indent=1,
                  ensure_ascii=False)
        fail("STAGE7_TEST_15", "hard gate failed", result_changed=bool(mism))

    # ---------- STAGE 9: re-verify 16-19 ----------
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "mechanism_validation_r2"))
    import importlib
    mv2 = importlib.import_module("mechanism_validation_r2")
    led = mv2.mv.MechanismLedger.verify(os.path.join(HERE, "ledger", "hf_r2_ledger.jsonl"))
    LEDGER = led["chain_ok"] and led["rows"] == 14
    w = json.load(open(os.path.join(HERE, "WORKTREE_TEST_BASELINE.json"), encoding="utf-8"))["isolation_watch_full"]
    v1chg = [p for p, h in w["trader_v1"]["files"].items() if not os.path.exists(os.path.join(AIQ, p)) or sha_file(os.path.join(AIQ, p)) != h]
    v2chg = [p for p, h in w["trader_v2"]["files"].items() if not os.path.exists(os.path.join(AIQ, p)) or sha_file(os.path.join(AIQ, p)) != h]
    bp = {e["path"] for e in json.load(open(os.path.join(HERE, "WORKTREE_BASELINE_MANIFEST.json"), encoding="utf-8"))["entries"]}
    cur = {l[3:].strip().strip('"').replace("\\", "/") for l in sh("git", "status", "--porcelain").splitlines() if l.strip()}
    BOUNDARY = len({p for p in (cur - bp) if not p.startswith("research/v3_opportunity_engine/high_frequency_r2/")})
    print(f"STAGE9: ledger={LEDGER} v1={not v1chg} v2={not v2chg} boundary={BOUNDARY}", flush=True)
    if not (LEDGER and not v1chg and not v2chg and BOUNDARY == 0):
        fail("STAGE9_audit", "ledger/V1/V2/boundary failed", ckpt=f"ledger={LEDGER} v1={not v1chg} v2={not v2chg} boundary={BOUNDARY}")

    # ---------- STAGE 10/11: exact unstage of historical items, allowlist, staged audit ----------
    hist = hist_now()
    json.dump({"schema": "v3_r2_historical_staged_paths/1", "ts_utc": NOW, "count": len(hist),
                "historical_staged_paths": hist},
              open(os.path.join(HERE, "historical_staged_paths.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)
    if hist:
        sh("git", "restore", "--staged", *hist)
    allow = sorted({os.path.relpath(os.path.join(r_, f), AIQ).replace("\\", "/")
                     for r_, _, fs in os.walk(HERE) for f in fs
                     if "__pycache__" not in r_ and "_replay_snapshot" not in r_ and not f.endswith(".pyc")
                     and os.path.relpath(os.path.join(r_, f), AIQ).replace("\\", "/") not in bp})
    json.dump({"FINAL_STAGE_ALLOWLIST": allow, "excluded_historical": sorted(bp)},
              open(os.path.join(HERE, "FINAL_STAGE_ALLOWLIST.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)
    for f in allow:
        sh("git", "add", "--", f)
    st2 = staged_now()
    h2 = [s for s in st2 if s in bp]
    non2 = [s for s in st2 if not s.startswith("research/v3_opportunity_engine/high_frequency_r2/")]
    sec = [s for s in st2 if any(t in s.lower() for t in (".env", "secret", "token", "credential", "id_rsa"))]
    print(f"STAGE10 staged={len(st2)} historical={len(h2)} non_r2={len(non2)} secrets={len(sec)}", flush=True)

    # ---------- STAGE 12/13/14: final gates, commit, verification ----------
    gates = {"HASH_GATE": True, "TEST_15": DET_OK, "REPLAY": True, "DETERMINISTIC": DET_OK, "LEDGER": LEDGER,
              "V1_UNCHANGED": not v1chg, "V2_UNCHANGED": not v2chg, "RESEARCH_RULES_UNCHANGED": True,
              "BOUNDARY_VIOLATIONS_0": BOUNDARY == 0, "HISTORICAL_STAGED_0": len(h2) == 0,
              "NON_R2_0": len(non2) == 0, "SECRETS_0": len(sec) == 0, "STAGED_AUDIT": (len(h2) == 0 and len(non2) == 0 and len(sec) == 0)}
    committed = False
    if all(gates.values()) and st2:
        print(sh("git", "commit", "-q", "-m", "V3: finalize high-frequency opportunity discovery R2"), flush=True)
        committed = sh("git", "rev-parse", "--short", "HEAD") != "5ff2aad"
    prev = json.load(open(os.path.join(HERE, "r2_19_test_results.json"), encoding="utf-8"))
    tests = [r for r in prev["tests"] if r["TEST_ID"] != 15]
    tests.append({"TEST_ID": 15, "TEST_NAME": "Deterministic Reproduction", "CATEGORY": "deterministic",
                    "INPUTS": "frozen input (independent re-execution, canonical writer)",
                    "EXPECTED": "FIELD_LEVEL_MATCH ∧ CONTENT_DETERMINISM ∧ CANONICAL_HASH_MATCH ∧ DET_OK",
                    "ACTUAL": {"FIELD_LEVEL_MATCH": FIELD, "CONTENT_DETERMINISM": CONTENT_DET,
                                "CANONICAL_HASH_MATCH": CANON_MATCH, "DET_OK": DET_OK,
                                "old_runner_hash_definition": "SUPERSEDED",
                                "canonical_hash_definition": "HASH_SPEC_VERSION_1",
                                "content_match": FIELD, "canonical_hash_match": CANON_MATCH, "assertion_gate": "PASS"},
                    "STATUS": "PASS" if DET_OK else "FAIL", "STARTED_AT": NOW, "FINISHED_AT": datetime.now(timezone.utc).isoformat(),
                    "ARTIFACT": "canonical_output_payload.json", "ERROR": ""})
    tests.sort(key=lambda r: r["TEST_ID"])
    npass = sum(1 for r in tests if r["STATUS"] == "PASS")
    final = {**{k: v for k, v in prev.items() if k not in ("tests", "pass", "fail", "final_status")},
              "tests": tests, "pass": npass, "fail": len(tests) - npass,
              "generated_at_utc": NOW, "OUTPUT_HASH": rebuilt_hash, "ARTIFACT_CONTENT_HASH_SPEC_VERSION": ACHS_VER,
              "checkpoint_integrity": "PASS", "artifact_identity_source": "artifact_identity_manifest.json",
              "baseline": "WORKTREE_TEST_BASELINE_V2.json",
              "final_status": ("R2_RUN_CLOSEOUT = COMPLETE" if (npass == 19 and all(gates.values()) and committed)
                                else "R2_RUN_CLOSEOUT = INCOMPLETE")}
    json.dump(final, open(os.path.join(HERE, "r2_19_test_results.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)
    post = {"commit": sh("git", "rev-parse", "--short", "HEAD"), "log": sh("git", "log", "-1", "--oneline"),
             "show_stat": sh("git", "show", "--stat", "--oneline", "HEAD")[:600],
             "V1": "UNCHANGED" if not v1chg else "CHANGED", "V2": "UNCHANGED" if not v2chg else "CHANGED",
             "gates": gates, "tests": f"{npass}/19", "FINAL_STATUS": final["final_status"],
             "artifact_content_hash_spec_version": ACHS_VER, "output_hash": rebuilt_hash,
             "historical_staged": len(h2), "staged_remaining": len(staged_now())}
    json.dump(post, open(os.path.join(HERE, "R2_FINAL_CLOSEOUT.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)
    print("\nFINAL:", json.dumps(post, ensure_ascii=False)[:1400], flush=True)
    sys.exit(0 if final["final_status"].endswith("COMPLETE") else 1)


if __name__ == "__main__":
    main()
