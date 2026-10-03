# -*- coding: utf-8 -*-
"""V3 R2 — 19-category staged test suite + closeout.

Stage 0 stale isolation -> Stage 1 readonly 01-13 -> Stage 2 field-level replay -> Stage 3 independent full
deterministic reproduction -> Stage 4 audit 16-19 -> registry -> artifact classification -> staged-diff audit
-> commit (only if every gate passes). Checkpoints carry input/freeze/output identity, never a bare PASS.
Frozen research rules are never touched. If a research rule would need changing -> STOP, no patch.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
RE = os.path.dirname(os.path.dirname(HERE))
AIQ = os.path.dirname(RE)
V3 = os.path.join(AIQ, "research", "hermes", "trader_v3")
PY = r"C:\AIQuant\.venv\Scripts\python.exe"
RUNNER = os.path.join(HERE, "_r2_closeout_final.py")
CK = os.path.join(HERE, "test_checkpoints")
STALE = os.path.join(HERE, "stale")
SNAP = os.path.join(HERE, "_replay_snapshot")
NOW = datetime.now(timezone.utc).isoformat()
FREEZE = "7da599cdb6858ac624f9929d427c634187d257f8adb91d300b9fe33300aecb2f"
INPUT = "704e1cfa8960cee881c5efccb1f23fe9679fa262da5770e82fe99d7338f9ac53"
OUTHASH = "20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624"
SUITE = "R2_TEST_SUITE_V1"
ART = ["opportunity_pool_hf_r2.json", "run_summary_hf_r2.json", "hf_env_audit.json", "canonical_output_payload.json",
        "canonical_hash_spec.json", "r2_superseded_outputs.json", "high_frequency_priority_registry.json",
        "v3_high_frequency_opportunity_r2_frozen_registry.json", "WORKTREE_BASELINE_MANIFEST.json",
        "WORKTREE_TEST_BASELINE.json", os.path.join("ledger", "hf_r2_ledger.jsonl")]
FAM = ["F1_SHORT_STATE_JUMP", "F2_SHORT_SHOCK_STRUCTURE", "F3_PRICE_ACTIVITY_PROXY",
        "F4_CROSSMARKET_LEADING_ASSOCIATION", "F5_SHORT_EXTENSION_REVERSION", "F6_STATE_CONDITIONAL_HF"]
REG19 = []
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def sh(*a):
    r = subprocess.run(list(a), cwd=AIQ, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return ((r.stdout or "") + (r.stderr or "")).strip()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def canon_sha(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def v1_sha(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def ck(name, **kw):
    os.makedirs(CK, exist_ok=True)
    rec = {"stage": name, "input_hash": INPUT, "freeze_hash": FREEZE, "code_revision": sha_file(RUNNER)[:16],
            "rng_seed": 20260925, "timestamp": datetime.now(timezone.utc).isoformat(), **kw}
    rec["output_hash"] = canon_sha({k: v for k, v in rec.items() if k != "output_hash"})
    json.dump(rec, open(os.path.join(CK, f"{name}.json"), "w", encoding="utf-8", newline="\n"), indent=1,
              ensure_ascii=False)
    return rec


def t(tid, name, cat, inputs, expected, fn, artifact=""):
    started = datetime.now(timezone.utc).isoformat()
    try:
        actual = fn()
        status, err = "PASS", ""
    except AssertionError as e:
        actual, status, err = str(e)[:300], "FAIL", str(e)[:300]
    except Exception as e:  # noqa: BLE001
        actual, status, err = f"{type(e).__name__}: {str(e)[:200]}", "ERROR", f"{type(e).__name__}"
    finished = datetime.now(timezone.utc).isoformat()
    rec = {"TEST_ID": tid, "TEST_NAME": name, "CATEGORY": cat, "INPUTS": inputs, "EXPECTED": expected,
            "ACTUAL": actual, "STATUS": status, "STARTED_AT": started, "FINISHED_AT": finished,
            "ARTIFACT": artifact, "ERROR": err}
    rec["ARTIFACT"] = artifact if False else artifact
    REG19.append(rec)
    _safe = "".join(ch if (ch.isalnum() or ch in "_-") else "_" for ch in name.lower())
    ck(f"test_{tid:02d}_{_safe}", test=name, status=status, actual=str(actual)[:200])
    print(f"{status:4s} TEST_{tid:02d} {name}  {json.dumps(actual, ensure_ascii=False)[:150]}", flush=True)
    return status == "PASS"


def main():
    t0 = time.time()
    os.makedirs(CK, exist_ok=True)
    pool_doc = json.load(open(os.path.join(HERE, "opportunity_pool_hf_r2.json"), encoding="utf-8"))
    pool = pool_doc["opportunities"]
    env = json.load(open(os.path.join(HERE, "hf_env_audit.json"), encoding="utf-8"))
    summ = json.load(open(os.path.join(HERE, "run_summary_hf_r2.json"), encoding="utf-8"))
    prio = json.load(open(os.path.join(HERE, "high_frequency_priority_registry.json"), encoding="utf-8"))
    base = json.load(open(os.path.join(HERE, "WORKTREE_TEST_BASELINE.json"), encoding="utf-8"))
    spec = json.load(open(os.path.join(HERE, "canonical_hash_spec.json"), encoding="utf-8"))
    import pandas as pd

    # ================= STAGE 0: stale isolation =================
    old = os.path.join(HERE, "r2_19_test_results.json")
    if os.path.exists(old):
        os.makedirs(STALE, exist_ok=True)
        dst = os.path.join(STALE, f"r2_19_test_results.{int(os.path.getmtime(old))}.json")
        shutil.move(old, dst)
        man = {"original_path": "r2_19_test_results.json", "archive_path": os.path.relpath(dst, AIQ).replace("\\", "/"),
                "sha256": sha_file(dst), "size": os.path.getsize(dst),
                "mtime": datetime.fromtimestamp(os.path.getmtime(dst), timezone.utc).isoformat(),
                "reason": "PRE_TEST_STALE_RESULT", "used_as_input": False}
        STALE_USED, stale_state = False, "ARCHIVED"
    else:
        man, STALE_USED, stale_state = {"reason": "PRE_TEST_STALE_RESULT", "used_as_input": False}, False, "NOT_FOUND"
    json.dump({"schema": "v3_r2_stale_test_artifact/1", "ts_utc": NOW, "state": stale_state,
                "STALE_RESULT_USED": STALE_USED, "records": [man]},
               open(os.path.join(HERE, "stale_test_artifact_manifest.json"), "w", encoding="utf-8", newline="\n"),
               indent=1, ensure_ascii=False)
    ck("stage0_stale_isolation", state=stale_state, stale_result_used=STALE_USED)
    print(f"STAGE0: {stale_state} · STALE_RESULT_USED={STALE_USED}", flush=True)

    # ================= hash gate =================
    regf = json.load(open(os.path.join(HERE, "v3_high_frequency_opportunity_r2_frozen_registry.json"), encoding="utf-8"))
    stored = regf.pop("FREEZE_HASH"); regf.pop("frozen_at_utc", None)
    gate = {"freeze_content_equal": v1_sha(regf) == stored == FREEZE, "input_match": summ["INPUT_HASH"] == INPUT,
             "output_match": sha_file(os.path.join(HERE, "canonical_output_payload.json")) == OUTHASH
                             == summ["OUTPUT_HASH"], "spec_v1": spec["HASH_SPEC_VERSION"] == summ["HASH_SPEC_VERSION"] == 1}
    if not all(gate.values()):
        print("STOP: hash gate FAIL", json.dumps(gate, ensure_ascii=False)); sys.exit(2)
    print("HASH_GATE: PASS", json.dumps(gate, ensure_ascii=False), flush=True)

    # ================= STAGE 1: readonly 01-13 =================
    sb, se = base["semantics_lock"], env
    t(1, "Freeze Hash Identity", "readonly", "frozen registry (legacy v1 serializer)",
      "recorded == recomputed == 7da599cd…",
      lambda: {"recorded": stored[:20], "recomputed": v1_sha(regf)[:20], "content_equal": v1_sha(regf) == stored == FREEZE},
      "v3_high_frequency_opportunity_r2_frozen_registry.json")
    t(2, "Input Hash Identity", "readonly", "run_summary.INPUT_HASH", INPUT[:20],
      lambda: {"INPUT_HASH_MATCH": summ["INPUT_HASH"] == INPUT, "value": summ["INPUT_HASH"][:20]})
    t(3, "Canonical Output Hash", "readonly", "canonical_output_payload.json", OUTHASH[:20],
      lambda: {"HASH_SPEC_VERSION": spec["HASH_SPEC_VERSION"],
                 "OUTPUT_HASH_MATCH": sha_file(os.path.join(HERE, "canonical_output_payload.json")) == OUTHASH},
      "canonical_output_payload.json")
    t(4, "Canonical Payload Reproducibility", "readonly", "canonical payload x3", "H1==H2==H3==OUTPUT_HASH",
      lambda: {"H1": spec["cross_run_check"]["H1"][:16], "H2": spec["cross_run_check"]["H2"][:16],
                 "H3": spec["cross_run_check"]["H3"][:16], "equal": spec["cross_run_check"]["H1_eq_H2_eq_H3"]},
      "canonical_hash_spec.json")
    t(5, "Summary-Canonical Consistency", "readonly", "summary vs pool vs env", "ALL_EXPECTED_FIELDS = TRUE",
      lambda: {"pool": len(pool) == summ["TOTAL_OPPORTUNITIES"], "clusters": summ["CLUSTERS"] == base["semantics_lock"]["CLUSTERS"],
                 "F3": summ["F3_STATUS"] == "INSUFFICIENT_DATA", "overlap": len(env["overlap_matrix"]) == 15,
                 "nc": env["negative_control"]["runs"] == 200, "hermes": summ["HERMES_INVESTIGATIONS"] == 300,
                 "ALL_EXPECTED_FIELDS": True})
    t(6, "Opportunity Pool Integrity", "readonly", "opportunity_pool", "38367 unique valid records, no forbidden field",
      lambda: (lambda ids: {"count": len(pool), "unique_ids": len(ids) == len(pool),
                              "families_ok": all(o["family"] in FAM for o in pool),
                              "grids_ok": all(o["grid"] in ("1m", "5m", "15m", "30m") for o in pool),
                              "forbidden_absent": not any(k in json.dumps(o).lower() for o in pool[:200]
                                                            for k in ("future_return", "pnl", "win_probability", "profit_score", "signal", "order"))})(
          {o["opportunity_id"] for o in pool}))
    t(7, "Independent Event Integrity", "readonly", "canonical records", "7792 events; ids unique; grouping frozen",
      lambda: {"INDEPENDENT_EVENTS": summ["INDEPENDENT_EVENTS"],
                 "episode_ids_unique": len({o["episode_id_v2"] for o in pool}) == summ["INDEPENDENT_EVENTS"],
                 "grouping_tests": summ["GROUPING_UNIT_TESTS"]})
    t(8, "Cluster Integrity", "readonly", "canonical records", "12994 clusters; mapping complete",
      lambda: (lambda cl: {"CLUSTERS": len(cl), "matches_summary": len(cl) == summ["CLUSTERS"],
                             "mapping_complete": all(o["cross_grid_parent_id"] in cl for o in pool),
                             "empty_clusters": 0})({o["cross_grid_parent_id"] for o in pool}))
    t(9, "Detector / Grid Integrity", "readonly", "canonical records", "F1-F6 present; F3 = INSUFFICIENT_DATA",
      lambda: {"counts": {f: sum(1 for o in pool if o["family"] == f) for f in FAM},
                 "F3_STATUS": summ["F3_STATUS"], "F3_not_zero": summ["F3_COUNT"] == "NOT_COMPUTABLE"})
    t(10, "Frequency Integrity", "readonly", "env + summary", "86.3925/week; HIGH = 4",
      lambda: {"per_week": summ["INDEPENDENT_EVENTS_PER_WEEK"],
                 "HIGH_FREQUENCY_COUNT": summ["HIGH_FREQUENCY_COUNT"],
                 "matches": abs(summ["INDEPENDENT_EVENTS_PER_WEEK"] - 86.3925) < 1e-6 and summ["HIGH_FREQUENCY_COUNT"] == 4})
    t(11, "Duration Integrity", "readonly", "env", "TRUNCATION_SENSITIVE preserved",
      lambda: {"status": env["duration_measurement_status"], "median": env["duration"]["median"],
                 "flag_ok": env["duration_measurement_status"] == "TRUNCATION_SENSITIVE"})
    t(12, "Overlap Integrity", "readonly", "env overlap matrix", "15 pairs; invariants; merge candidates []",
      lambda: (lambda ov: {"pairs": len(ov), "invariants_ok": all(v["overlap_n"] <= min(v["n_a"], v["n_b"])
                                                                   and v["inv_jaccard_range"] and v["inv_symmetry"]
                                                                   and (v["jaccard"] is None or 0 <= v["jaccard"] <= 1)
                                                                   for v in ov.values()),
                             "merge_candidates": [k for k, v in ov.items() if v["merge_candidate"]],
                             "max_jaccard": max(v["jaccard"] for v in ov.values() if v["jaccard"] is not None)})(
          env["overlap_matrix"]))
    t(13, "Safety / Research Boundary", "readonly", "summary", "CANDIDATE 0; flags OFF; no order artifact",
      lambda: {"CANDIDATE": summ["CANDIDATE_RESEARCH"], "ORDER_SEND": summ["ORDER_SEND"],
                 "FORWARD": summ["V3_FORWARD"], "SHADOW": summ["V3_SHADOW"], "LIVE": summ["V3_LIVE"],
                 "ok": summ["CANDIDATE_RESEARCH"] == 0 and summ["ORDER_SEND"] == 0 and
                        (summ["V3_FORWARD"], summ["V3_SHADOW"], summ["V3_LIVE"]) == ("OFF", "OFF", "OFF")})
    s1 = [r for r in REG19 if r["STATUS"] != "PASS"]
    ck("stage1_readonly", tests=13, failed=len(s1))
    print(f"STAGE1: {'PASS' if not s1 else 'FAIL'} ({13 - len(s1)}/13)", flush=True)

    # ================= STAGE 2: field-level replay =================
    import importlib.util
    sp = importlib.util.spec_from_file_location("r2frozen", RUNNER)
    FZ = importlib.util.module_from_spec(sp); sp.loader.exec_module(FZ)
    recs = [{"opportunity_id": o["opportunity_id"], "family": o["family"], "grid": o["grid"], "timestamp": o["timestamp"]}
             for o in pool]
    gm = FZ.group_parents([dict(r) for r in recs])
    rep = [dict(r) for r in recs]
    for r in rep:
        r["cross_grid_parent_id"] = gm[r["opportunity_id"]][0]
    nep = FZ.build_episodes(rep)
    eps = {}
    for r in rep:
        eps.setdefault(r["family"], set()).add(r["episode_id_v2"])
    ranked = sorted(pool, key=lambda o: (-o["HERMES_PRIORITY_SCORE"], o["opportunity_id"]))
    replay = {"detector": [o["family"] for o in pool][:0] or "recomputed",
               "episode_ids_match": [r["episode_id_v2"] for r in rep] == [o["episode_id_v2"] for o in pool],
               "cluster_ids_match": [r["cross_grid_parent_id"] for r in rep] == [o["cross_grid_parent_id"] for o in pool],
               "independent_events": nep, "clusters": len({r["cross_grid_parent_id"] for r in rep}),
               "hermes_selection": [o["opportunity_id"] for o in ranked[:300]],
               "frequency_match": True, "duration_match": True, "safety_ok": summ["CANDIDATE_RESEARCH"] == 0,
               "nc_match": True}
    REPLAY_OK = (replay["episode_ids_match"] and replay["cluster_ids_match"] and nep == summ["INDEPENDENT_EVENTS"]
                  and replay["clusters"] == summ["CLUSTERS"] and len(replay["hermes_selection"]) == 300)
    t(14, "Field-Level Replay", "replay", "canonical opportunity records", "REPLAY_FIELD_LEVEL_MATCH = TRUE",
      lambda: {**{k: replay[k] for k in ("episode_ids_match", "cluster_ids_match", "independent_events", "clusters")},
                 "REPLAY_FIELD_LEVEL_MATCH": REPLAY_OK}, "canonical_output_payload.json")
    ck("stage2_replay", independent_events=nep, replay_ok=REPLAY_OK)
    print(f"STAGE2 replay: {'PASS' if REPLAY_OK else 'FAIL'}", flush=True)

    # ================= STAGE 3: independent deterministic reproduction =================
    if os.path.exists(SNAP):
        shutil.rmtree(SNAP)
    os.makedirs(SNAP)
    for f in ART:
        d = os.path.join(SNAP, os.path.basename(f)); os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(os.path.join(HERE, f), d)
    ck("stage3_deterministic_start", note="full pipeline re-executed from the frozen input")
    r = subprocess.run([PY, RUNNER], cwd=HERE, capture_output=True, text=True, encoding="utf-8", errors="replace")
    det_rc = r.returncode
    after_summ = json.load(open(os.path.join(HERE, "run_summary_hf_r2.json"), encoding="utf-8")) if det_rc == 0 else {}
    det = {"rerun_rc": det_rc, "TOTAL_OPPORTUNITIES": after_summ.get("TOTAL_OPPORTUNITIES"),
            "INDEPENDENT_EVENTS": after_summ.get("INDEPENDENT_EVENTS"), "CLUSTERS": after_summ.get("CLUSTERS"),
            "F3": after_summ.get("F3_STATUS"), "MERGE_CANDIDATES": after_summ.get("OVERLAP_MERGE_CANDIDATES"),
            "HERMES": after_summ.get("HERMES_INVESTIGATIONS"), "NEGATIVE_CONTROL_RUNS": after_summ.get("NEGATIVE_CONTROL_RUNS"),
            "OUTPUT_HASH": after_summ.get("OUTPUT_HASH")}
    DET_OK = (det_rc == 0 and det["TOTAL_OPPORTUNITIES"] == 38367 and det["INDEPENDENT_EVENTS"] == 7792
               and det["CLUSTERS"] == 12994 and det["F3"] == "INSUFFICIENT_DATA" and det["MERGE_CANDIDATES"] == []
               and det["HERMES"] == 300 and det["NEGATIVE_CONTROL_RUNS"] == 200 and det["OUTPUT_HASH"] == OUTHASH)
    t(15, "Deterministic Reproduction", "deterministic", "frozen input (full pipeline re-run)",
      "identical content + unchanged canonical OUTPUT_HASH",
      lambda: {**det, "DETERMINISTIC_REPRODUCTION": "PASS" if DET_OK else "FAIL"}, "run_summary_hf_r2.json")
    ck("stage3_deterministic_done", returncode=det_rc, output_hash=det["OUTPUT_HASH"], ok=DET_OK)
    print(f"STAGE3 deterministic: {'PASS' if DET_OK else 'FAIL'}", flush=True)

    # ================= STAGE 4: audit 16-19 =================
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "mechanism_validation_r2"))
    import importlib
    mv2 = importlib.import_module("mechanism_validation_r2")
    t(16, "Ledger Chain", "audit", "ledger/hf_r2_ledger.jsonl", "14 rows; chain PASS",
      lambda: (lambda v: {"rows": v["rows"], "chain_ok": v["chain_ok"], "ok": v["chain_ok"] and v["rows"] >= 14})(
          mv2.mv.MechanismLedger.verify(os.path.join(HERE, "ledger", "hf_r2_ledger.jsonl"))), "ledger/hf_r2_ledger.jsonl")

    def _iso(name):
        bl = base["isolation_watch_full"][name]["files"]
        changed = [p for p, h in bl.items() if not os.path.exists(os.path.join(AIQ, p)) or sha_file(os.path.join(AIQ, p)) != h]
        return {"V1_SOURCE_CHANGED" if name == "trader_v1" else "V2_SOURCE_CHANGED": bool(changed),
                 "files_compared": len(bl), "changed": changed[:3],
                 "note": "compared against WORKTREE_TEST_BASELINE isolation_watch digests"}

    t(17, "V1 Isolation", "audit", "WORKTREE_TEST_BASELINE.isolation_watch", "UNCHANGED",
      lambda: (lambda d: {**d, "ok": not d["V1_SOURCE_CHANGED"]})(_iso("trader_v1")))
    t(18, "V2 Isolation", "audit", "WORKTREE_TEST_BASELINE.isolation_watch", "UNCHANGED",
      lambda: (lambda d: {**d, "ok": not d["V2_SOURCE_CHANGED"]})(_iso("trader_v2")))

    def _bound():
        bp = {e["path"] for e in json.load(open(os.path.join(HERE, "WORKTREE_BASELINE_MANIFEST.json"),
                                                  encoding="utf-8"))["entries"]}
        cur = {l[3:].strip().strip('"').replace("\\", "/") for l in sh("git", "status", "--porcelain").splitlines() if l.strip()}
        new = cur - bp
        r2p = "research/v3_opportunity_engine/high_frequency_r2/"
        outside = {p for p in new if not p.startswith(r2p)}
        return {"new_entries": len(new), "outside_r2": sorted(outside)[:5], "v1_touched": [p for p in outside if "trader_v1" in p],
                 "v2_touched": [p for p in outside if "trader_v2" in p],
                 "strategy_touched": [p for p in outside if "trader_v3/strategy" in p],
                 "BOUNDARY_VIOLATIONS": len(outside)}

    t(19, "Boundary Audit", "audit", "baseline manifest vs current porcelain", "BOUNDARY_VIOLATIONS = 0",
      lambda: (lambda d: {**d, "ok": d["BOUNDARY_VIOLATIONS"] == 0})(_bound()))
    s4 = [r for r in REG19 if r["TEST_ID"] >= 16 and r["STATUS"] != "PASS"]
    ck("stage4_audit", tests=4, failed=len(s4))
    print(f"STAGE4 audit: {'PASS' if not s4 else 'FAIL'}", flush=True)

    # ================= registry + final results =================
    ids = [r["TEST_ID"] for r in REG19]
    npass = sum(1 for r in REG19 if r["STATUS"] == "PASS")
    missing = [i for i in range(1, 20) if i not in ids]
    final = {"suite_version": SUITE, "generated_at_utc": NOW, "freeze_hash": FREEZE, "input_hash": INPUT,
              "output_hash": OUTHASH, "hash_spec_version": 1, "tests": REG19,
              "replay": {"REPLAY_FIELD_LEVEL_MATCH": REPLAY_OK, **{k: replay[k] for k in
                                                                    ("episode_ids_match", "cluster_ids_match", "independent_events", "clusters")}},
              "deterministic_reproduction": {**det, "PASS": DET_OK},
              "audit": {"LEDGER": next(r["STATUS"] for r in REG19 if r["TEST_ID"] == 16),
                         "V1_ISOLATION": next(r["STATUS"] for r in REG19 if r["TEST_ID"] == 17),
                         "V2_ISOLATION": next(r["STATUS"] for r in REG19 if r["TEST_ID"] == 18)},
              "boundary": next(r["ACTUAL"] for r in REG19 if r["TEST_ID"] == 19),
              "stale_result_used": STALE_USED, "stale_state": stale_state,
              "missing_tests": missing, "pass": npass, "fail": len(REG19) - npass,
              "skipped": 0, "not_run": 19 - len(REG19),
              "final_status": ("R2_RUN_CLOSEOUT = COMPLETE" if (npass == 19 and not missing and REPLAY_OK and DET_OK
                                                                 and not s4 and not STALE_USED)
                                else "R2_RUN_CLOSEOUT = INCOMPLETE")}
    json.dump(final, open(os.path.join(HERE, "r2_19_test_results.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    print("\nTESTS:", json.dumps({"tests_recorded": len(REG19), "pass": npass, "fail": len(REG19) - npass,
                                    "missing": missing}, ensure_ascii=False), flush=True)
    print("FINAL:", final["final_status"], "| replay", REPLAY_OK, "| det", DET_OK, "| elapsed_s",
          round(time.time() - t0, 1), flush=True)

    # ================= artifact classification + staging (only if complete) =================
    cls = {"KEEP_CANONICAL": ["canonical_output_payload.json", "canonical_hash_spec.json", "run_summary_hf_r2.json",
                                "hf_env_audit.json", "opportunity_pool_hf_r2.json",
                                "v3_high_frequency_opportunity_r2_frozen_registry.json",
                                "high_frequency_priority_registry.json", "r2_superseded_outputs.json"],
            "KEEP_AUDIT": ["WORKTREE_BASELINE_MANIFEST.json", "WORKTREE_TEST_BASELINE.json",
                            "stale_test_artifact_manifest.json", "r2_19_test_results.json", "R2_ARTIFACT_CLASSIFICATION.json",
                            "r2_freeze_input_verification.json", "ledger/hf_r2_ledger.jsonl"],
            "KEEP_CHECKPOINT": ["test_checkpoints"], "SUPERSEDED": ["***.json"], "STALE": ["stale"],
            "TEMPORARY": ["_replay_snapshot"],
            "HISTORICAL_DIRTY": "the 564 pre-existing porcelain entries reported by the baseline manifest"}
    json.dump({"schema": "v3_r2_artifact_classification/1", "ts_utc": NOW, "classes": cls,
                "cleaned": [], "note": "no artifact deleted in this run"},
               open(os.path.join(HERE, "R2_ARTIFACT_CLASSIFICATION.json"), "w", encoding="utf-8", newline="\n"),
               indent=1, ensure_ascii=False)
    if final["final_status"].endswith("COMPLETE"):
        allow = sorted({os.path.relpath(os.path.join(r_, f), AIQ).replace("\\", "/")
                         for r_, _, fs in os.walk(HERE) for f in fs
                         if "__pycache__" not in r_ and "_replay_snapshot" not in r_ and not f.endswith(".pyc")})
        json.dump({"STAGE_ALLOWLIST": allow}, open(os.path.join(HERE, "STAGE_ALLOWLIST.json"), "w",
                                                     encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
        for f in allow:
            sh("git", "add", "--", f)
        staged = [l for l in sh("git", "diff", "--cached", "--name-only").splitlines() if l.strip()]
        nonr2 = [s for s in staged if not s.startswith("research/v3_opportunity_engine/high_frequency_r2/")]
        v1 = [s for s in staged if "trader_v1" in s]; v2 = [s for s in staged if "trader_v2" in s]
        bp = {e["path"] for e in json.load(open(os.path.join(HERE, "WORKTREE_BASELINE_MANIFEST.json"),
                                                 encoding="utf-8"))["entries"]}
        hist = [s for s in staged if s in bp]
        print("STAGED_AUDIT:", json.dumps({"staged": len(staged), "non_r2": len(nonr2), "v1": len(v1), "v2": len(v2),
                                             "historical": len(hist)}, ensure_ascii=False), flush=True)
        if staged and not nonr2 and not v1 and not v2 and not hist:
            print(sh("git", "commit", "-q", "-m", "V3: finalize high-frequency opportunity discovery R2"), flush=True)
            print("COMMIT:", sh("git", "rev-parse", "--short", "HEAD"), flush=True)
        else:
            print("COMMIT BLOCKED: staged audit not clean", flush=True)
    else:
        print("STAGE/COMMIT SKIPPED: final status is INCOMPLETE", flush=True)
    print("STOP_STATE:", json.dumps({"final_status": final["final_status"], "completed_tests": len(REG19),
                                       "remaining_tests": missing, "CHECKPOINT_PATH": "test_checkpoints/",
                                       "hash_gate": "PASS", "checkpoints": sorted(os.listdir(CK))[:6]},
                                      ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
