# -*- coding: utf-8 -*-
"""V3 Mechanism Validation R2 — the 23 mandatory tests (task section 66).

Design note: these tests verify that the validator BEHAVES CORRECTLY, i.e. that a failing control forces
METHOD_VALIDITY=INVALID and CANDIDATE_RESEARCH=0. They deliberately do NOT require the controls to pass -
requiring that would be the same failure mode as tuning the rules.
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
R2 = os.path.dirname(HERE)
ROOT = os.path.dirname(R2)
sys.path.insert(0, R2)
sys.path.insert(0, os.path.join(ROOT, "mechanism_validation"))
sys.path.insert(0, ROOT)
import mechanism_validation_r2 as mv2                # noqa: E402
import run_mechanism_validation_r2 as orch           # noqa: E402

START = float(os.environ.get("TASK_START_TS", "0")) or (time.time() - 3600)
RESULTS = []


def case(name):
    def deco(fn):
        def run(*a, **k):
            t0 = time.time()
            try:
                d = fn(*a, **k)
                RESULTS.append({"test": name, "result": "PASS", "detail": d, "sec": round(time.time() - t0, 2)})
                print(f"PASS  {name}  {json.dumps(d, ensure_ascii=False)[:190]}")
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
    S = json.load(open(os.path.join(R2, "run_summary_r2.json"), encoding="utf-8"))
    A = json.load(open(os.path.join(R2, "mechanism_validation_r2_audit.json"), encoding="utf-8"))
    ND = json.load(open(os.path.join(R2, "null_distributions.json"), encoding="utf-8"))
    D = json.load(open(os.path.join(R2, "mechanism_decisions_r2.json"), encoding="utf-8"))["decisions"]
    CAND = json.load(open(os.path.join(R2, "candidate_research_r2.json"), encoding="utf-8"))["entries"]

    inp = orch.r1run.load_inputs()
    recs = orch.r1run.prepare(inp["opportunities"], inp["hermes"])

    def ids(pipe):
        return {e["independent_event_id"] for e in pipe["events"]}

    @case("test_r2_deterministic")
    def _det():
        a = mv2.run_validation([dict(r) for r in recs], random.Random(mv2.REGISTRY["random_seed"]), 200)
        b = mv2.run_validation([dict(r) for r in recs], random.Random(mv2.REGISTRY["random_seed"]), 200)
        assert ids(a) == ids(b), "event identity differs between identical runs"
        assert {k: v["decision"] for k, v in a["rows"].items()} == {k: v["decision"] for k, v in b["rows"].items()}
        return {"events": len(ids(a)), "identical": True}

    @case("test_r2_no_lookahead")
    def _nl():
        for r in S["replay"]:
            assert r["identity_stable"], f"closed-window identity changed at {r['frac']}"
        return {"replays_checked": len(S["replay"]), "no_lookahead": S["lookahead"]}

    @case("test_r2_replay_70")
    def _r70():
        r = next(x for x in S["replay"] if x["frac"] == 0.7)
        assert r["identity_stable"], "70% replay identity unstable"
        return r

    @case("test_r2_replay_80")
    def _r80():
        r = next(x for x in S["replay"] if x["frac"] == 0.8)
        assert r["identity_stable"], "80% replay identity unstable"
        return r

    @case("test_r2_replay_90")
    def _r90():
        r = next(x for x in S["replay"] if x["frac"] == 0.9)
        assert r["identity_stable"], "90% replay identity unstable"
        return r

    @case("test_registry_hash")
    def _reg():
        h = mv2.registry_hash()
        assert h == mv2.registry_hash(), "registry hash unstable"
        p = os.path.join(R2, "mechanism_validation_r2_registry.json")
        h2 = hashlib.sha256(json.dumps(json.load(open(p, encoding="utf-8")), sort_keys=True,
                                         ensure_ascii=False).encode()).hexdigest()
        assert h == h2 == A["registry_hash"], "registry hash mismatch between live/written/audit"
        assert mv2.REGISTRY["permutation_count"] >= 500, "permutation count below the frozen minimum"
        return {"registry_hash": h[:20], "permutation_count": mv2.REGISTRY["permutation_count"],
                 "random_seed": mv2.REGISTRY["random_seed"]}

    @case("test_immutable_inputs")
    def _imm():
        for k, h in (("opportunity_1h", A["input_opportunity_hash"].split("+")[0]),
                      ("opportunity_5m", A["input_opportunity_hash"].split("+")[1]),
                      ("quality", A["input_quality_hash"]), ("hermes", A["input_hermes_hash"])):
            assert orch.sha_file(inp["paths"][k]) == h, f"{k} changed"
        assert A["inputs_unchanged_after_run"], "audit reports the inputs changed"
        return {"four_inputs_unchanged": True}

    def _nc(name_key, status_key):
        nc = S[name_key]
        assert nc["null_runs"] == mv2.REGISTRY["null_runs"], f"{name_key} wrong null_runs"
        assert all("supported_rate" in r for r in nc["runs"]), f"{name_key} runs lack supported_rate"
        if nc["status"] != "PASS":
            assert S["METHOD_VALIDITY"] == "INVALID", f"{name_key} failed but the method stayed valid"
            assert S["candidate_research"] == 0, f"{name_key} failed but candidates were emitted"
        return {"status": nc["status"], "mean_rate": nc["supported_rate_mean"], "max_rate": nc["supported_rate_max"],
                 "ceiling": nc["pre_registered_ceiling"]}

    @case("test_negative_control_a")
    def _nca():
        return _nc("NEGATIVE_CONTROL_A", "a")

    @case("test_negative_control_b")
    def _ncb():
        return _nc("NEGATIVE_CONTROL_B", "b")

    @case("test_negative_control_c")
    def _ncc():
        return _nc("NEGATIVE_CONTROL_C", "c")

    @case("test_positive_control")
    def _pc():
        pc = S["POSITIVE_CONTROL"]
        assert "distribution" in pc and pc["definition"], "positive control not pre-registered"
        if pc["decision"] != "PASS":
            assert S["METHOD_VALIDITY"] == "INVALID", "positive control failed but the method stayed valid"
            assert S["candidate_research"] == 0, "positive control failed but candidates were emitted"
        return {"decision": pc["decision"], "detected": pc["detected"], "distribution": pc["distribution"]}

    @case("test_null_distribution")
    def _nd():
        need = ("observed", "null_mean", "null_std", "null_quantiles", "p_value", "n_perm", "seed")
        st = ND["mechanism_level_stats"]
        assert st, "no mechanism-level null statistics stored"
        for m, row in st.items():
            t = row["TIME_STABILITY"]
            miss = [k for k in need if k not in t]
            assert not miss, f"{m} null summary missing {miss}"
            assert t["n_perm"] == mv2.REGISTRY["permutation_count"], f"{m} permutation count mismatch"
            assert t["seed"] == mv2.REGISTRY["random_seed"], f"{m} seed mismatch"
        return {"mechanisms_with_full_null_summary": len(st),
                 "example_p": {m: st[m]["TIME_STABILITY"]["p_value"] for m in list(st)[:2]}}

    @case("test_permutation_reproducibility")
    def _perm():
        times = [e["event_start"] for e in mv2.mv.build_events([dict(r) for r in recs])[1]][:40]
        a = mv2.permutation_stability(times, "TIME_STABILITY", random.Random(7), 200)
        b = mv2.permutation_stability(times, "TIME_STABILITY", random.Random(7), 200)
        assert a["p_value"] == b["p_value"] and a["observed"] == b["observed"], "permutation test not reproducible"
        return {"p_value": a["p_value"], "reproducible": True}

    @case("test_artifact_separation")
    def _art():
        for m, r in D.items():
            ac = r["evidence_matrix"]["ARTIFACT_CLASSES"]
            for cls in ("DATA_ARTIFACT", "TIMESTAMP_ARTIFACT", "PROXY_ARTIFACT", "DUPLICATION_ARTIFACT",
                         "SELECTION_ARTIFACT", "UNKNOWN_ARTIFACT"):
                assert cls in ac, f"{m} missing artifact class {cls}"
            assert isinstance(r["evidence_matrix"]["FATAL_ARTIFACT"], bool)
            if r["decision"] == "MECHANISM_REJECTED":
                assert r["evidence_matrix"]["FATAL_ARTIFACT"] or r["counter_evidence"]["level"] == "FATAL", \
                    f"{m} rejected without a fatal reason"
        return {"mechanisms": len(D), "fatal_only_blocks": True}

    @case("test_duplicate_evidence_separation")
    def _dup():
        assert mv2.REGISTRY["duplicate_detection_stage"] == "EVENT_LEVEL", "duplication stage not declared"
        assert mv2.REGISTRY["duplicate_counted_once"] is True, "duplication counted more than once"
        ev = json.load(open(os.path.join(R2, "mechanism_events_r2.json"), encoding="utf-8"))["events"]
        assert sum(e["opportunities_merged"] for e in ev) >= len(ev), "event merge bookkeeping looks wrong"
        return {"stage": "EVENT_LEVEL", "events": len(ev), "opportunities": sum(e["opportunities_merged"] for e in ev)}

    @case("test_counter_evidence_independence")
    def _ce():
        ce = json.load(open(os.path.join(R2, "mechanism_evidence_r2.json"), encoding="utf-8"))["counter_evidence"]
        for m, row in ce.items():
            assert "parent_id" in row and row["parent_id"].startswith("CE_P_"), f"{m} lacks a counter-evidence parent"
            assert row["level"] in mv2.REGISTRY["counter_evidence_levels"], f"{m} illegal level"
        parents = mv2.REGISTRY["counter_evidence_parents"]
        codes = [c for cs in parents.values() for c in cs]
        assert len(codes) == len(set(codes)), "a code maps to two parents"
        return {"mechanisms": len(ce), "one_parent_per_code": True}

    @case("test_evidence_dependency")
    def _dep():
        dep = mv2.evidence_independence()
        assert dep["pairs"], "no evidence-pair audit produced"
        for p in dep["pairs"]:
            assert p["status"] in ("DEPENDENT_EVIDENCE", "INDEPENDENT_EVIDENCE")
        return {"pairs": len(dep["pairs"]), "dependent": dep["dependent_pairs"]}

    @case("test_mechanism_cluster_stability")
    def _cl():
        ck = json.load(open(os.path.join(R2, "mechanism_clusters_r2.json"), encoding="utf-8"))["clusters"]
        seen = {}
        for m, keys in ck.items():
            for k in keys:
                assert k not in seen or seen[k] == m, f"cluster {k} under two mechanisms"
                seen[k] = m
        return {"clusters": len(seen), "mechanisms": len(ck)}

    @case("test_independent_event_count")
    def _ev():
        ev = json.load(open(os.path.join(R2, "mechanism_events_r2.json"), encoding="utf-8"))["events"]
        assert S["independent_event_count"] == len(ev), "event count disagrees with the summary"
        assert S["independent_event_count"] < 404, "dedup produced no reduction vs the raw INVESTIGATE count"
        return {"independent_events": len(ev), "raw_investigate": S["input_hermes_investigate"]}

    @case("test_candidate_gate")
    def _gate():
        if S["METHOD_VALIDITY"] != "VALID":
            assert S["candidate_research"] == 0 and not CAND, "invalid method produced candidates"
        else:
            for c in CAND:
                m = c["mechanism_id"]
                assert D[m]["decision"] == "MECHANISM_SUPPORTED", f"{m} candidate without SUPPORTED"
                assert c["independent_event_count"] >= mv2.REGISTRY["minimum_independent_events"]
                assert not D[m]["evidence_matrix"]["FATAL_ARTIFACT"]
        return {"method_validity": S["METHOD_VALIDITY"], "candidates": len(CAND)}

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
        for f in ("mechanism_validation_r2.py", "run_mechanism_validation_r2.py"):
            tree = ast.parse(open(os.path.join(R2, f), encoding="utf-8").read())
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
        reg = json.load(open(os.path.join(R2, "mechanism_validation_r2_registry.json"), encoding="utf-8"))
        fi = " ".join(reg["forbidden_identifiers"]).lower()
        for t in ("future_return", "future_pnl", "pnl", "win_rate", "sharpe", "order_send", "broker", "execution"):
            assert t in fi, f"registry does not declare {t} forbidden"
        return {"ast_clean": True, "registry_complete": True}

    for fn in (_det, _nl, _r70, _r80, _r90, _reg, _imm, _nca, _ncb, _ncc, _pc, _nd, _perm, _art, _dup, _ce,
                _dep, _cl, _ev, _gate, _v1, _v2, _ord):
        fn()

    summary = {"schema": "v3_mechanism_r2_tests/1", "total": len(RESULTS),
                "pass": sum(1 for r in RESULTS if r["result"] == "PASS"),
                "fail": sum(1 for r in RESULTS if r["result"] != "PASS"), "results": RESULTS}
    print("\nTESTS:", json.dumps({k: v for k, v in summary.items() if k != "results"}, ensure_ascii=False))
    json.dump(summary, open(os.path.join(HERE, "mechanism_r2_test_results.json"), "w", encoding="utf-8",
                             newline="\n"), indent=1, ensure_ascii=False)
    sys.exit(0 if summary["fail"] == 0 else 1)


if __name__ == "__main__":
    main()
