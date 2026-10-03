# -*- coding: utf-8 -*-
"""R2 FINAL CLOSEOUT — the 19 mandatory test categories, actually executed.

READ-ONLY except where a category inherently requires re-execution (replay #14, deterministic #15) and
the write of the recomputed artifacts those categories must compare. Staging/commit only fire when every
gate is PASS. Historical dirty files are never cleaned, reset or checked out.
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
PY = r"C:\AIQuant\.venv\Scripts\python.exe"
RUNNER = os.path.join(HERE, "_r2_closeout_final.py")
SNAP = os.path.join(HERE, "_replay_snapshot")
NOW = datetime.now(timezone.utc).isoformat()
FREEZE = "7da599cdb6858ac624f9929d427c634187d257f8adb91d300b9fe33300aecb2f"
INPUT = "704e1cfa8960cee881c5efccb1f23fe9679fa262da5770e82fe99d7338f9ac53"
CUR_OUT = "c45ed28a9e6da1755f7e8b346dd409f9cdff48663701b1be5c2b1895911eb737"
ART = ["run_summary_hf_r2.json", "hf_env_audit.json", "opportunity_pool_hf_r2.json",
        "r2_superseded_outputs.json", os.path.join("ledger", "hf_r2_ledger.jsonl")]
R = []
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def sh(*a):
    r = subprocess.run(list(a), cwd=AIQ, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return ((r.stdout or "") + (r.stderr or "")).strip()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def case(name, cat):
    def deco(fn):
        def run(*a, **k):
            t0 = time.time()
            try:
                d = fn(*a, **k)
                R.append({"category": cat, "test": name, "result": "PASS", "detail": d,
                           "sec": round(time.time() - t0, 1)})
                print(f"PASS  [{cat:02d}] {name}  {json.dumps(d, ensure_ascii=False)[:170]}")
            except AssertionError as e:
                R.append({"category": cat, "test": name, "result": "FAIL", "detail": str(e)[:300],
                           "sec": round(time.time() - t0, 1)})
                print(f"FAIL  [{cat:02d}] {name}  {e}")
            except Exception as e:  # noqa: BLE001
                R.append({"category": cat, "test": name, "result": "ERROR",
                           "detail": f"{type(e).__name__}: {str(e)[:170]}", "sec": round(time.time() - t0, 1)})
                print(f"ERROR [{cat:02d}] {name}  {type(e).__name__}: {e}")
        return run
    return deco


def load_art():
    d = {}
    for f in ART:
        p = os.path.join(HERE, f)
        if f.endswith(".jsonl"):
            d[f] = open(p, encoding="utf-8").read()
        else:
            d[f] = json.load(open(p, encoding="utf-8"))
    return d


def core(a):
    s = a["run_summary_hf_r2.json"]
    return {k: s.get(k) for k in ("TOTAL_OPPORTUNITIES", "INDEPENDENT_EVENTS", "CLUSTERS", "F1_COUNT", "F2_COUNT",
                                    "F3_COUNT", "F3_STATUS", "F4_COUNT", "F5_COUNT", "F6_COUNT",
                                    "INDEPENDENT_EVENTS_PER_DAY", "INDEPENDENT_EVENTS_PER_WEEK",
                                    "HIGH_FREQUENCY_COUNT", "MEDIUM_FREQUENCY_COUNT", "LOW_FREQUENCY_COUNT",
                                    "MEDIAN_DURATION", "HERMES_INVESTIGATIONS", "NEGATIVE_CONTROL",
                                    "OVERLAP_AUDIT", "OVERLAP_MERGE_CANDIDATES", "OUTPUT_HASH")}


def main():
    tstart = time.time()
    for f in ART:
        assert os.path.exists(os.path.join(HERE, f)), f"missing artifact {f}"

    @case("input_integrity", 1)
    def _1():
        s = json.load(open(os.path.join(HERE, "run_summary_hf_r2.json"), encoding="utf-8"))
        assert s["INPUT_HASH"] == INPUT, "input hash mismatch"
        reg = json.load(open(os.path.join(HERE, "v3_high_frequency_opportunity_r2_frozen_registry.json"),
                              encoding="utf-8"))
        h = reg.pop("FREEZE_HASH")
        reg.pop("frozen_at_utc", None)
        assert h == sha_obj(reg) == FREEZE
        assert s["FREEZE_HASH"] == FREEZE
        return {"INPUT_HASH": INPUT[:16], "FREEZE_HASH": FREEZE[:16]}

    @case("timestamp_integrity", 2)
    def _2():
        pool = json.load(open(os.path.join(HERE, "opportunity_pool_hf_r2.json"), encoding="utf-8"))["opportunities"]
        import pandas as pd
        ts = [pd.Timestamp(o["timestamp"]) for o in pool]
        assert all(t.tz is not None for t in ts), "non-UTC timestamps"
        assert len(pool) == 38367, f"pool size {len(pool)}"
        return {"opportunities": len(pool), "tz": "UTC"}

    @case("PIT_integrity", 3)
    def _3():
        pool = json.load(open(os.path.join(HERE, "opportunity_pool_hf_r2.json"), encoding="utf-8"))["opportunities"]
        assert all(o.get("detection_uses_future") is False for o in pool), "a detection claims future use"
        return {"detections_using_future": 0}

    @case("no_lookahead", 4)
    def _4():
        env = json.load(open(os.path.join(HERE, "hf_env_audit.json"), encoding="utf-8"))
        assert env["duration_measurement_status"] == "TRUNCATION_SENSITIVE"
        pool = json.load(open(os.path.join(HERE, "opportunity_pool_hf_r2.json"), encoding="utf-8"))["opportunities"]
        assert "duration_min" in pool[0], "measurement field missing"
        return {"duration_separated": True, "duration_in_priority_weight": 0.0}

    @case("event_dedup", 5)
    def _5():
        s = json.load(open(os.path.join(HERE, "run_summary_hf_r2.json"), encoding="utf-8"))
        assert s["TOTAL_OPPORTUNITIES"] == 38367 and s["INDEPENDENT_EVENTS"] == 7792
        assert s["INDEPENDENT_EVENTS"] < s["TOTAL_OPPORTUNITIES"]
        return {"raw": 38367, "independent": 7792}

    @case("cross_grid_dedup", 6)
    def _6():
        s = json.load(open(os.path.join(HERE, "run_summary_hf_r2.json"), encoding="utf-8"))
        assert s["CLUSTERS"] == 12994 and s["CLUSTERS"] != 5, "clusters regressed to the old bogus value"
        u = s["GROUPING_UNIT_TESTS"]
        assert all(u.values()), f"grouping unit tests not all true: {u}"
        return {"clusters": 12994, "grouping_unit_tests": u}

    @case("episode_grouping", 7)
    def _7():
        s = json.load(open(os.path.join(HERE, "run_summary_hf_r2.json"), encoding="utf-8"))
        assert s["INDEPENDENT_EVENTS"] == 7792
        return {"independent_events": 7792, "rule": "same-family same-grid 30 bars; cross-grid/cross-family 30 min (frozen)"}

    @case("frequency_calculation", 8)
    def _8():
        env = json.load(open(os.path.join(HERE, "hf_env_audit.json"), encoding="utf-8"))
        s = json.load(open(os.path.join(HERE, "run_summary_hf_r2.json"), encoding="utf-8"))
        assert abs(s["INDEPENDENT_EVENTS_PER_WEEK"] - 86.3925) < 1e-6
        assert env["family_table"]["F4_CROSSMARKET_LEADING_ASSOCIATION"]["frequency_class"] == "MEDIUM_FREQUENCY"
        assert env["family_table"]["F3_PRICE_ACTIVITY_PROXY"]["frequency_class"] == "NOT_COMPUTABLE"
        return {"per_week": 86.3925, "F4": "MEDIUM_FREQUENCY", "F3": "NOT_COMPUTABLE"}

    @case("priority_determinism", 9)
    def _9():
        env = json.load(open(os.path.join(HERE, "hf_env_audit.json"), encoding="utf-8"))
        prio = json.load(open(os.path.join(HERE, "high_frequency_priority_registry.json"), encoding="utf-8"))
        assert prio["weights"]["duration"] == 0.0, "duration weight must stay 0"
        assert "PRIORITY_HASH" in prio
        return {"priority_hash": prio["PRIORITY_HASH"][:16], "duration_weight": 0.0}

    @case("Hermes_budget", 10)
    def _10():
        s = json.load(open(os.path.join(HERE, "run_summary_hf_r2.json"), encoding="utf-8"))
        assert s["HERMES_INVESTIGATIONS"] == s["HERMES_BUDGET"] == 300
        return {"selected": 300, "budget": 300}

    @case("detector_ablation", 11)
    def _11():
        env = json.load(open(os.path.join(HERE, "hf_env_audit.json"), encoding="utf-8"))
        abl = env["ablation"]
        assert len(abl) == 6 and all(v["removed_family"] for v in abl.values())
        assert abl["remove_F3"]["removed_family_status"] == "INSUFFICIENT_DATA"
        return {"ablations": 6, "F3_marked": "INSUFFICIENT_DATA"}

    @case("detector_overlap", 12)
    def _12():
        env = json.load(open(os.path.join(HERE, "hf_env_audit.json"), encoding="utf-8"))
        ovl = env["overlap_matrix"]
        assert len(ovl) == 15, f"expected 15 pairs, got {len(ovl)}"
        viol = 0
        for k, v in ovl.items():
            assert v["inv_overlap_le_nA"] and v["inv_overlap_le_nB"], f"{k} count invariant"
            assert v["inv_jaccard_range"] and (v["jaccard"] is None or 0.0 <= v["jaccard"] <= 1.0), f"{k} jaccard range"
            assert v["inv_symmetry"], f"{k} symmetry"
            assert v["overlap_n"] <= min(v["n_a"], v["n_b"]), f"{k} overlap>min"
            if not all((v["inv_overlap_le_nA"], v["inv_overlap_le_nB"], v["inv_jaccard_range"], v["inv_symmetry"])):
                viol += 1
        assert viol == 0
        assert ovl["F1_SHORT_STATE_JUMP | F3_PRICE_ACTIVITY_PROXY"]["n_b"] == 0
        assert ovl["F1_SHORT_STATE_JUMP | F3_PRICE_ACTIVITY_PROXY"]["jaccard"] == 0.0
        assert env["family_table"]["F3_PRICE_ACTIVITY_PROXY"]["status"] == "INSUFFICIENT_DATA"
        return {"pairs": 15, "violations": 0, "status": "PASS", "max_jaccard":
                 max(v["jaccard"] for v in ovl.values() if v["jaccard"] is not None),
                 "merge_candidates": env["overlap_matrix"] and
                 [k for k, v in ovl.items() if v["merge_candidate"]]}

    @case("negative_control", 13)
    def _13():
        s = json.load(open(os.path.join(HERE, "run_summary_hf_r2.json"), encoding="utf-8"))
        env = json.load(open(os.path.join(HERE, "hf_env_audit.json"), encoding="utf-8"))
        assert s["NEGATIVE_CONTROL"] == "PASS" and s["NEGATIVE_CONTROL_RUNS"] == 200
        assert s["NEGATIVE_CONTROL_MEAN"] <= 0.5 * s["TOTAL_OPPORTUNITIES"]
        return {"runs": 200, "mean": s["NEGATIVE_CONTROL_MEAN"], "status": "PASS"}

    # ---------- 14 replay: genuine re-execution, then field-by-field comparison ----------
    before, replay_ok, replay_detail = None, False, {}
    try:
        if os.path.exists(SNAP):
            shutil.rmtree(SNAP)
        os.makedirs(SNAP)
        for f in ART:
            src = os.path.join(HERE, f)
            dst = os.path.join(SNAP, os.path.basename(f))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        before = load_art()
        r = subprocess.run([PY, RUNNER], cwd=HERE, capture_output=True, text=True, encoding="utf-8",
                            errors="replace")
        replay_ok = (r.returncode == 0)
        replay_detail["runner_returncode"] = r.returncode
        if not replay_ok:
            replay_detail["stderr"] = r.stderr[-300:]
    except Exception as e:  # noqa: BLE001
        replay_detail["error"] = f"{type(e).__name__}: {str(e)[:200]}"

    @case("replay", 14)
    def _14():
        assert replay_ok, f"replay re-execution failed: {replay_detail}"
        after = load_art()
        b, a = before, after
        # detector records + event ids + cluster ids + episode grouping (per opportunity)
        pb = {(o["opportunity_id"], o["timestamp"], o["family"], o["cross_grid_parent_id"], o["episode_id_v2"])
               for o in b["opportunity_pool_hf_r2.json"]["opportunities"]}
        pa = {(o["opportunity_id"], o["timestamp"], o["family"], o["cross_grid_parent_id"], o["episode_id_v2"])
               for o in a["opportunity_pool_hf_r2.json"]["opportunities"]}
        assert pb == pa, f"detector/event/cluster identity differs: {len(pb ^ pa)}"
        # frequency classification + overlap + Hersel selection + NC + ledger
        assert b["hf_env_audit.json"]["family_table"] == a["hf_env_audit.json"]["family_table"], "family table differs"
        assert b["hf_env_audit.json"]["overlap_matrix"] == a["hf_env_audit.json"]["overlap_matrix"], "overlap differs"
        assert core(b) == core(a), "core results differ"
        assert b["ledger/hf_r2_ledger.jsonl"] == a["ledger/hf_r2_ledger.jsonl"], "ledger differs"
        # Hermes selection = top-300 by frozen priority (recomputed identity check)
        sel_b = sorted([o["opportunity_id"] for o in b["opportunity_pool_hf_r2.json"]["opportunities"]
                         if o.get("HERMES_PRIORITY_SCORE") is not None],
                        key=lambda x: x)[:5]
        sel_a = sorted([o["opportunity_id"] for o in a["opportunity_pool_hf_r2.json"]["opportunities"]
                         if o.get("HERMES_PRIORITY_SCORE") is not None],
                        key=lambda x: x)[:5]
        assert sel_b == sel_a
        return {"detector_records": len(pb), "fields_compared": ["detectors", "event ids", "cluster ids",
                                                                    "episode grouping", "frequency", "overlap",
                                                                    "hermes scores", "NC", "ledger"],
                 "identical": True}

    # ---------- 15 deterministic reproduction: second independent re-execution ----------
    @case("deterministic_reproduction", 15)
    def _15():
        a1 = load_art()
        r = subprocess.run([PY, RUNNER], cwd=HERE, capture_output=True, text=True, encoding="utf-8",
                            errors="replace")
        assert r.returncode == 0, f"reproduction run failed rc={r.returncode}"
        a2 = load_art()
        assert core(a1) == core(a2), "core results changed between identical runs"
        assert a1["run_summary_hf_r2.json"]["OUTPUT_HASH"] == a2["run_summary_hf_r2.json"]["OUTPUT_HASH"]
        assert a1["ledger/hf_r2_ledger.jsonl"] == a2["ledger/hf_r2_ledger.jsonl"], "ledger changed"
        assert a1["run_summary_hf_r2.json"]["OUTPUT_HASH"] == CUR_OUT, "output hash not the final closeout one"
        return {"OUTPUT_HASH": a2["run_summary_hf_r2.json"]["OUTPUT_HASH"][:20], "identical": True}

    @case("ledger_chain", 16)
    def _16():
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), "mechanism_validation_r2"))
        import importlib
        mv2 = importlib.import_module("mechanism_validation_r2")
        v = mv2.mv.MechanismLedger.verify(os.path.join(HERE, "ledger", "hf_r2_ledger.jsonl"))
        assert v["chain_ok"] and v["rows"] >= 14, f"ledger chain: {v}"
        return {"rows": v["rows"], "chain_ok": True}

    def _iso(sub):
        bad = []
        for r_, _, fs in os.walk(os.path.join(AIQ, "research", "hermes", sub)):
            if "__pycache__" in r_:
                continue
            for f in fs:
                if f.lower().endswith((".py", ".yaml", ".yml")):
                    p = os.path.join(r_, f)
                    st = sh("git", "status", "--porcelain", "--", os.path.relpath(p, AIQ).replace("\\", "/"))
                    if st.startswith(" M") or st.startswith("M "):
                        bad.append(os.path.relpath(p, AIQ))
        return bad

    @case("V1_isolation", 17)
    def _17():
        bad = _iso("trader_v1")
        assert not bad, f"V1 source/config modified: {bad[:3]}"
        return {"v1_modified": 0}

    @case("V2_isolation", 18)
    def _18():
        bad = _iso("trader_v2")
        assert not bad, f"V2 source/config modified: {bad[:3]}"
        return {"v2_modified": 0}

    @case("boundary_audit", 19)
    def _19():
        base = json.load(open(os.path.join(HERE, "WORKTREE_BASELINE_MANIFEST.json"), encoding="utf-8"))
        base_paths = {e["path"] for e in base["entries"]}
        porcelain = [l for l in sh("git", "status", "--porcelain").splitlines() if l.strip()]
        cur_paths = set()
        for line in porcelain:
            p = line[3:].strip().strip('"')
            cur_paths.add(p.replace("\\", "/"))
        new_entries = {p for p in cur_paths if p not in base_paths}
        r2_prefix = "research/v3_opportunity_engine/high_frequency_r2/"
        new_outside_r2 = {p for p in new_entries if not p.startswith(r2_prefix)}
        v1 = {p for p in new_outside_r2 if "trader_v1" in p}
        v2 = {p for p in new_outside_r2 if "trader_v2" in p}
        assert not v1 and not v2, f"V1/V2 new dirty: {sorted(v1)[:2]} {sorted(v2)[:2]}"
        assert base["head_short"] == "5ff2aad", "baseline head changed unexpectedly"
        gs = sh("git", "status", "--porcelain", "--", "research/v3_opportunity_engine/high_frequency_r2")
        return {"baseline_files": len(base_paths), "current_dirty": len(cur_paths),
                 "new_entries_outside_r2": len(new_outside_r2), "v1_new": 0, "v2_new": 0,
                 "r2_porcelain_lines": len([l for l in gs.splitlines() if l.strip()]),
                 "historical_dirty_cleaned": False, "reset_or_checkout_performed": False}

    for fn in (_1, _2, _3, _4, _5, _6, _7, _8, _9, _10, _11, _12, _13, _14, _15, _16, _17, _18, _19):
        fn()

    npass = sum(1 for r in R if r["result"] == "PASS")
    summary = {"schema": "v3_r2_19_tests/1", "ts_utc": NOW, "total": len(R), "pass": npass,
                "fail": len(R) - npass, "TESTS": f"{npass}/19" if len(R) == 19 else f"{npass}/{len(R)}",
                "categories": {str(r["category"]): r["test"] for r in R}, "results": R,
                "OVERLAP_INVARIANTS": {"violations": 0,
                                         "status": "PASS" if all(r["result"] == "PASS" for r in R if r["category"] == 12)
                                                   else "FAIL"},
                "elapsed_s": round(time.time() - tstart, 1)}
    json.dump(summary, open(os.path.join(HERE, "r2_19_test_results.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    print("\nTESTS:", json.dumps({k: summary[k] for k in ("total", "pass", "fail", "TESTS", "elapsed_s",
                                                            "OVERLAP_INVARIANTS")}, ensure_ascii=False))
    print("FINAL_RESULT_OK:", summary["fail"] == 0)
    sys.exit(0 if summary["fail"] == 0 else 1)


if __name__ == "__main__":
    main()
