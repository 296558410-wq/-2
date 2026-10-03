# -*- coding: utf-8 -*-
"""MV-R3 — the mandatory tests (task section 50). Verifies the pre-registered control, the four-quadrant
outcome, and that a VALID method still does NOT emit candidates (task section 35: STOP).
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import random
import sys
import time

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
R3 = os.path.dirname(HERE)
ROOT = os.path.dirname(R3)
sys.path.insert(0, R3)
sys.path.insert(0, os.path.join(ROOT, "mechanism_validation_r2"))
sys.path.insert(0, ROOT)
import positive_control_definition_r3 as pcdef   # noqa: E402
import mechanism_validation_r2 as mv2            # noqa: E402
import run_mechanism_validation_r3 as r3run      # noqa: E402

START = float(os.environ.get("TASK_START_TS", "0")) or (time.time() - 3600)
RESULTS = []


def case(name):
    def deco(fn):
        def run(*a, **k):
            t0 = time.time()
            try:
                d = fn(*a, **k)
                RESULTS.append({"test": name, "result": "PASS", "detail": d, "sec": round(time.time() - t0, 2)})
                print(f"PASS  {name}  {json.dumps(d, ensure_ascii=False)[:185]}")
            except AssertionError as e:
                RESULTS.append({"test": name, "result": "FAIL", "detail": str(e)[:300], "sec": round(time.time() - t0, 2)})
                print(f"FAIL  {name}  {e}")
            except Exception as e:  # noqa: BLE001
                RESULTS.append({"test": name, "result": "ERROR", "detail": f"{type(e).__name__}: {str(e)[:180]}",
                                 "sec": round(time.time() - t0, 2)})
                print(f"ERROR {name}  {type(e).__name__}: {e}")
        return run
    return deco


def main():
    S = json.load(open(os.path.join(R3, "run_summary_r3.json"), encoding="utf-8"))
    A = json.load(open(os.path.join(R3, "mechanism_validation_r3_audit.json"), encoding="utf-8"))
    PCA = json.load(open(os.path.join(R3, "positive_control_audit.json"), encoding="utf-8"))
    PCR = json.load(open(os.path.join(R3, "positive_control_results.json"), encoding="utf-8"))
    NR = json.load(open(os.path.join(R3, "negative_control_results.json"), encoding="utf-8"))
    MV = json.load(open(os.path.join(R3, "method_validity_r3.json"), encoding="utf-8"))
    CD = json.load(open(os.path.join(R3, "positive_control_definition_r3.json"), encoding="utf-8"))
    DS = json.load(open(os.path.join(R3, "positive_control_dataset.json"), encoding="utf-8"))

    pc_recs, pc_manifest = pcdef.build_control_records()
    pc_row = list(PCR["rows"].values())[0] if PCR["rows"] else {}

    @case("test_positive_control_deterministic")
    def _det():
        a = mv2.run_validation([dict(r) for r in pc_recs], random.Random(mv2.REGISTRY["random_seed"]), 200)
        b = mv2.run_validation([dict(r) for r in pc_recs], random.Random(mv2.REGISTRY["random_seed"]), 200)
        assert {e["independent_event_id"] for e in a["events"]} == {e["independent_event_id"] for e in b["events"]}
        assert a["distribution"] == b["distribution"]
        assert S["positive_control_deterministic"], "orchestrator reports non-determinism"
        return {"events": len(a["events"]), "identical": True}

    @case("test_positive_control_pre_registered")
    def _pre():
        assert CD["pre_registered"] is True and CD["single_shot"] is True and CD["no_adaptation"] is True
        assert A["positive_control_definition_hash"] == pcdef.definition_hash(), "definition hash changed"
        assert MV["positive_control"] in ("PASS", "FAIL")
        for k in ("synthetic_event_count", "event_separation", "variation_bounds", "random_seed", "expected_decision"):
            assert k in CD, f"definition lacks {k}"
        return {"definition_hash": pcdef.definition_hash()[:20], "single_shot": True}

    @case("test_positive_control_no_lookahead")
    def _nl():
        assert S["positive_control_no_lookahead"], "PC lookahead check failed"
        assert all(r["identity_stable"] for r in S["positive_control_replay"]), "PC replay identity changed"
        return {"replays": len(S["positive_control_replay"]), "no_lookahead": True}

    @case("test_positive_control_replay_70")
    def _r70():
        r = next(x for x in S["positive_control_replay"] if x["frac"] == 0.7)
        assert r["identity_stable"] and r["supported"] >= 1, "PC not detected at 70%"
        return r

    @case("test_positive_control_replay_80")
    def _r80():
        r = next(x for x in S["positive_control_replay"] if x["frac"] == 0.8)
        assert r["identity_stable"] and r["supported"] >= 1, "PC not detected at 80%"
        return r

    @case("test_positive_control_replay_90")
    def _r90():
        r = next(x for x in S["positive_control_replay"] if x["frac"] == 0.9)
        assert r["identity_stable"] and r["supported"] >= 1, "PC not detected at 90%"
        return r

    @case("test_positive_event_separation")
    def _sep():
        gaps = [(pd.Timestamp(pc_recs[i + 1]["detected_at"]) - pd.Timestamp(pc_recs[i]["detected_at"])).total_seconds() / 3600
                for i in range(len(pc_recs) - 1)]
        assert all(g > 6 for g in gaps), f"a gap violates the 6h separation window: {min(gaps)}"
        assert len(set(gaps)) > 1, "gaps are perfectly regular (forbidden by section 11)"
        assert PCA["gaps_all_above_window"], "audit disagrees about the gaps"
        return {"min_gap_h": min(gaps), "max_gap_h": max(gaps), "distinct_gaps": len(set(gaps))}

    @case("test_positive_independent_event_count")
    def _cnt():
        defined = CD["synthetic_event_count"]
        got = S["POSITIVE_CONTROL_INDEPENDENT_EVENTS"]
        tol = CD["acceptance"]["independent_event_tolerance"]["abs"]
        assert abs(got - defined) <= tol, f"independent events {got} vs defined {defined} outside tolerance {tol}"
        assert got >= mv2.REGISTRY["minimum_independent_events"], "below the frozen minimum"
        return {"defined": defined, "detected": got, "tolerance": tol}

    @case("test_positive_no_duplicate")
    def _dup():
        assert PCA["duplicate_events"] == 0, f"duplicate events detected: {PCA['duplicate_events']}"
        tr = CD["event_separation"]["intra_episode_gaps_hours"]
        assert all(g > CD["event_separation"]["separation_window_hours"] for g in tr)
        return {"duplicate_events": 0, "intra_gaps": tr}

    @case("test_positive_no_cross_grid_double_count")
    def _xg():
        assert PCA["cross_grid_events"] == 0, "control produced a cross-grid event"
        assert CD["grid"] == "1h", "control grid not declared"
        return {"cross_grid_events": 0, "grid": CD["grid"]}

    @case("test_positive_no_artifact")
    def _art():
        assert PCA["FATAL_ARTIFACT"] is False, "control produced a FATAL artifact"
        for cls in ("DATA_ARTIFACT", "TIMESTAMP_ARTIFACT", "DUPLICATION_ARTIFACT", "SELECTION_ARTIFACT"):
            assert cls in PCA["artifact_classes"], f"artifact class {cls} missing from the audit"
            assert PCA["artifact_classes"][cls]["fatal"] is False, f"{cls} reported fatal"
        return {"FATAL_ARTIFACT": False, "artifact": S["POSITIVE_CONTROL_ARTIFACT"]}

    def _nc(key, obj):
        assert obj["null_runs"] == mv2.REGISTRY["null_runs"]
        assert obj["pre_registered_ceiling"] == mv2.REGISTRY["negative_controls"]["max_null_rate"]
        assert obj["status"] in ("PASS", "FAIL")
        if obj["status"] != "PASS":
            assert S["METHOD_VALIDITY"] == "INVALID", f"{key} failed but METHOD_VALIDITY is {S['METHOD_VALIDITY']}"
        return {"status": obj["status"], "rate_mean": obj["supported_rate_mean"], "ceiling": obj["pre_registered_ceiling"]}

    @case("test_negative_control_a")
    def _a():
        return _nc("NC_A", NR["NC_A"])

    @case("test_negative_control_b")
    def _b():
        return _nc("NC_B", NR["NC_B"])

    @case("test_negative_control_c")
    def _c():
        return _nc("NC_C", NR["NC_C"])

    @case("test_null_distribution")
    def _nd():
        st = PCR["stats"]
        assert st, "no null statistics stored for the control"
        need = ("observed", "null_mean", "null_std", "null_quantiles", "p_value", "n_perm", "seed")
        for m, row in st.items():
            for dim in ("TIME_STABILITY", "SESSION_STABILITY", "STATE_STABILITY"):
                miss = [k for k in need if k not in row[dim]]
                assert not miss, f"{m}/{dim} null summary missing {miss}"
            assert row["TIME_STABILITY"]["n_perm"] == mv2.REGISTRY["permutation_count"]
        return {"mechanisms": len(st), "full_summary": True,
                 "pc_time_p_value": list(st.values())[0]["TIME_STABILITY"]["p_value"]}

    @case("test_permutation_reproducibility")
    def _perm():
        times = [e["event_start"] for e in mv2.mv.build_events([dict(r) for r in pc_recs])[1]]
        a = mv2.permutation_stability(times, "TIME_STABILITY", random.Random(11), 300)
        b = mv2.permutation_stability(times, "TIME_STABILITY", random.Random(11), 300)
        assert a["p_value"] == b["p_value"] and a["observed"] == b["observed"], "permutation not reproducible"
        return {"p_value": a["p_value"], "n_perm": a["n_perm"], "reproducible": True}

    @case("test_r2_registry_immutable")
    def _r2reg():
        base = json.load(open(os.path.join(ROOT, "mechanism_validation_r2", "run_summary_r2.json"),
                               encoding="utf-8"))
        assert mv2.registry_hash() == base["registry_hash"], "R2 registry hash changed"
        assert A["r2_registry_hash"] == base["registry_hash"], "audit sees a different R2 registry"
        assert A["r2_modified"] is False, "audit reports R2 as modified"
        return {"r2_registry_hash": mv2.registry_hash()[:20], "immutable": True}

    @case("test_real_input_immutable")
    def _imm():
        inp = r3run.r1run.load_inputs()
        assert r3run.sha_file(inp["paths"]["opportunity_1h"]) == A["input_opportunity_hash"].split("+")[0]
        assert r3run.sha_file(inp["paths"]["opportunity_5m"]) == A["input_opportunity_hash"].split("+")[1]
        assert r3run.sha_file(inp["paths"]["quality"]) == A["input_quality_hash"]
        assert r3run.sha_file(inp["paths"]["hermes"]) == A["input_hermes_hash"]
        assert A["real_inputs_unchanged_after_run"] is True
        assert A["synthetic_in_real_ledgers"] is False
        return {"four_inputs_unchanged": True, "synthetic_isolated": True}

    @case("test_candidate_gate")
    def _gate():
        assert S["CANDIDATE_RESEARCH"] == 0, "candidates were emitted"
        real = S["REAL_DISTRIBUTION_R2_BASELINE"]
        assert real["MECHANISM_SUPPORTED"] == 0, "real mechanisms must not be re-labelled by the control"
        if S["METHOD_VALIDITY"] == "VALID":
            # section 35: a VALID method still STOPS here; real mechanisms are NOT re-evaluated
            assert S["method_invalid_reasons"] == []
        return {"METHOD_VALIDITY": S["METHOD_VALIDITY"], "candidates": 0, "real_supported": real["MECHANISM_SUPPORTED"]}

    SRC_EXT = (".py", ".yaml", ".yml", ".toml", ".cfg", ".ini")

    def _classify(root):
        s, a = [], []
        for r, _, fs in os.walk(root):
            for f in fs:
                p = os.path.join(r, f)
                try:
                    if os.path.getmtime(p) <= START:
                        continue
                except OSError:
                    continue
                (s if os.path.relpath(p, root).lower().endswith(SRC_EXT) else a).append(p)
        return s, a

    @case("test_v1_isolation")
    def _v1():
        s, a = _classify(r"C:\AIQuant\research\hermes\trader_v1")
        assert not s, f"V1 source/config modified: {s[:3]}"
        return {"v1_source_modified": 0, "v1_runtime_files": len(a)}

    @case("test_v2_isolation")
    def _v2():
        s, a = _classify(r"C:\AIQuant\research\hermes\trader_v2")
        assert not s, f"V2 source/config modified: {s[:3]}"
        assert not [p for p in a if "v3_opportunity_engine" in p.lower()], "task footprint inside V2"
        return {"v2_source_modified": 0, "v2_runtime_files": len(a)}

    @case("test_order_send_disabled")
    def _ord():
        FORB = mv2.REGISTRY["forbidden_identifiers"]
        bad = []
        for f in ("positive_control_definition_r3.py", "run_mechanism_validation_r3.py"):
            tree = ast.parse(open(os.path.join(R3, f), encoding="utf-8").read())
            names = set()
            for n in ast.walk(tree):
                if isinstance(n, ast.Name):
                    names.add(n.id.lower())
                elif isinstance(n, ast.Attribute):
                    names.add(n.attr.lower())
                elif isinstance(n, ast.arg):
                    names.add(n.arg.lower())
                elif isinstance(n, ast.FunctionDef):
                    names.add(n.name.lower())
                elif isinstance(n, ast.keyword) and n.arg:
                    names.add(n.arg.lower())
            bad += [f"{f}:{t}" for t in FORB if t in names]
        assert not bad, f"forbidden identifiers used as code: {bad}"
        return {"ast_clean": True, "files_scanned": 2}

    for fn in (_det, _pre, _nl, _r70, _r80, _r90, _sep, _cnt, _dup, _xg, _art, _a, _b, _c, _nd, _perm,
                _r2reg, _imm, _gate, _v1, _v2, _ord):
        fn()

    summary = {"schema": "v3_mechanism_r3_tests/1", "total": len(RESULTS),
                "pass": sum(1 for r in RESULTS if r["result"] == "PASS"),
                "fail": sum(1 for r in RESULTS if r["result"] != "PASS"), "results": RESULTS}
    print("\nTESTS:", json.dumps({k: v for k, v in summary.items() if k != "results"}, ensure_ascii=False))
    json.dump(summary, open(os.path.join(HERE, "mechanism_r3_test_results.json"), "w", encoding="utf-8",
                             newline="\n"), indent=1, ensure_ascii=False)
    sys.exit(0 if summary["fail"] == 0 else 1)


if __name__ == "__main__":
    main()
