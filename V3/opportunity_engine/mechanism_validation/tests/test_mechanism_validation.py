# -*- coding: utf-8 -*-
"""V3 Opportunity Mechanism Validation R1 — the 17 mandatory tests (section 58).

Run:  python tests/test_mechanism_validation.py
Self-contained. Exits non-zero on any failure.
AST identifier analysis is used for the code-boundary test (string mentions of forbidden names inside a
registry declaration must NOT be confused with actually using them as identifiers).
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import sys
import time

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
MV_DIR = os.path.dirname(HERE)
ROOT = os.path.dirname(MV_DIR)
sys.path.insert(0, MV_DIR)
sys.path.insert(0, ROOT)
import mechanism_validation as mv                      # noqa: E402
import run_mechanism_validation_r1 as orch             # noqa: E402

START = float(os.environ.get("TASK_START_TS", "0")) or (time.time() - 3600)
RESULTS = []


def case(name):
    def deco(fn):
        def run(*a, **k):
            t0 = time.time()
            try:
                d = fn(*a, **k)
                RESULTS.append({"test": name, "result": "PASS", "detail": d, "sec": round(time.time() - t0, 2)})
                print(f"PASS  {name}  {json.dumps(d, ensure_ascii=False)[:200]}")
            except AssertionError as e:
                RESULTS.append({"test": name, "result": "FAIL", "detail": str(e)[:300], "sec": round(time.time() - t0, 2)})
                print(f"FAIL  {name}  {e}")
            except Exception as e:  # noqa: BLE001
                RESULTS.append({"test": name, "result": "ERROR", "detail": f"{type(e).__name__}: {str(e)[:200]}",
                                 "sec": round(time.time() - t0, 2)})
                print(f"ERROR {name}  {type(e).__name__}: {e}")
        return run
    return deco


def main():
    inp = orch.load_inputs()
    recs = orch.prepare(inp["opportunities"], inp["hermes"])
    P = orch.run_pipeline(recs)
    R = json.load(open(os.path.join(MV_DIR, "run_summary.json"), encoding="utf-8"))
    A = json.load(open(os.path.join(MV_DIR, "mechanism_validation_audit.json"), encoding="utf-8"))
    D = json.load(open(os.path.join(MV_DIR, "mechanism_decisions.json"), encoding="utf-8"))["decisions"]

    def idset(pipe):
        return {(e["independent_event_id"], e["event_start"], e["mechanism_id"]) for m, evs in pipe["by_mech"].items()
                for e in evs}

    @case("test_mechanism_deterministic")
    def _det():
        P2 = orch.run_pipeline(orch.prepare(inp["opportunities"], inp["hermes"]))
        assert idset(P) == idset(P2), "event identity differs between two runs"
        assert {m: d[0] for m, d in P["decisions"].items()} == {m: d[0] for m, d in P2["decisions"].items()}, \
            "decisions differ between two runs"
        return {"events": len(idset(P)), "mechanisms": len(P["decisions"]), "identical": True}

    def _truncate(frac):
        cut = recs[int(len(recs) * frac) - 1]["detected_at"]
        full_closed = {t for t in idset(P) if t[1] <= cut}
        tr = [r for r in recs if r["detected_at"] <= cut]
        PT = orch.run_pipeline(tr)
        tr_closed = {t for t in idset(PT) if t[1] <= cut}
        assert tr_closed == full_closed, f"historical event identity changed at {frac}: missing={len(full_closed-tr_closed)} extra={len(tr_closed-full_closed)}"
        return {"frac": frac, "cut": cut, "closed_events": len(full_closed)}

    @case("test_mechanism_no_lookahead")
    def _nolook():
        r = _truncate(0.7)
        src = open(os.path.join(MV_DIR, "run_mechanism_validation_r1.py"), encoding="utf-8").read()
        assert "post_event" not in src.lower().replace("response_observation", ""), \
            "orchestrator appears to read post-event values"
        return r

    @case("test_mechanism_replay")
    def _replay():
        out = [_truncate(f) for f in (0.7, 0.8, 0.9)]
        return {"replays": out, "all_identity_stable": True}

    @case("test_mechanism_registry_hash")
    def _reg():
        h = mv.registry_hash()
        assert h == mv.registry_hash(), "registry hash unstable"
        p = os.path.join(MV_DIR, "mechanism_validation_registry.json")
        h2 = hashlib.sha256(json.dumps(json.load(open(p, encoding="utf-8")), sort_keys=True,
                                         ensure_ascii=False).encode()).hexdigest()
        assert h == h2, "written registry differs from the live registry"
        assert A["registry_hash"] == h, "audit registry hash mismatch"
        return {"registry_hash": h[:20], "matches_written_and_audit": True}

    @case("test_immutable_opportunity_ledger")
    def _imm_opp():
        for g in ("1h", "5m"):
            p = os.path.join(ROOT, "ledger", f"v3_opportunity_ledger_{g}.jsonl")
            assert orch.sha_file(p) == A["input_opportunity_hash"].split("+")[0 if g == "1h" else 1], \
                f"opportunity ledger {g} changed"
        return {"opportunity_ledgers_unchanged": True}

    @case("test_immutable_quality_ledger")
    def _imm_qual():
        p = os.path.join(ROOT, "ledger", "v3_opportunity_quality_ledger.jsonl")
        assert orch.sha_file(p) == A["input_quality_hash"], "quality ledger changed"
        return {"quality_ledger_unchanged": True}

    @case("test_cross_grid_dedup")
    def _xg():
        ev = json.load(open(os.path.join(MV_DIR, "mechanism_events.json"), encoding="utf-8"))["events"]
        bad = [e for e in ev if len(e["grids_involved"]) > 1 and e["grids_involved"] not in (["1h", "5m"], ["5m", "1h"])]
        assert not bad, f"cross-grid merge produced an unexpected grid set: {bad[:2]}"
        pairs = sum(1 for e in ev if len(e["grids_involved"]) > 1)
        assert R["cross_grid_duplicates_merged"] == pairs, "audit merge count disagrees with the events file"
        return {"cross_grid_events": pairs, "merged": R["cross_grid_duplicates_merged"]}

    @case("test_independent_event_count")
    def _iec():
        ev = json.load(open(os.path.join(MV_DIR, "mechanism_events.json"), encoding="utf-8"))["events"]
        df = pd.DataFrame(ev)
        assert df["independent_event_id"].is_unique, "duplicate independent_event_id"
        win = {(6 if "1h" in g else 0.5) for g in df["grids_involved"]}
        per = df.groupby(["mechanism_id", "cluster_key"]).size()
        assert (per >= 1).all()
        assert R["independent_event_count"] == len(df), "audit event count disagrees with the events file"
        return {"independent_events": len(df), "opportunities": sum(e["opportunities_merged"] for e in ev),
                 "merged_reported": R["opportunities_merged"]}

    @case("test_mechanism_cluster_stability")
    def _cs():
        ck = json.load(open(os.path.join(MV_DIR, "mechanism_clusters.json"), encoding="utf-8"))["clusters"]
        seen = {}
        for m, keys in ck.items():
            for k in keys:
                assert k not in seen or seen[k] == m, f"cluster key {k} maps to two mechanisms"
                seen[k] = m
        assert all(k.split("|")[0] == m for m, keys in ck.items() for k in keys), "cluster key mechanism prefix mismatch"
        return {"clusters": len(seen), "mechanisms": len(ck), "one_to_one": True}

    @case("test_counter_evidence_aggregation")
    def _ce():
        ce = json.load(open(os.path.join(MV_DIR, "mechanism_evidence.json"), encoding="utf-8"))["counter_evidence"]
        for m, row in ce.items():
            assert row["counter_evidence_count"] >= 1, f"{m} has no counter-evidence recorded"
            assert row["strongest_counter_evidence"][0] in mv.COUNTER_CODES, f"{m} strongest code invalid"
            assert set(row["COUNTER_EVIDENCE"].keys()) <= set(mv.COUNTER_CODES), f"{m} unknown code"
        return {"mechanisms": len(ce), "strongest_present": True}

    @case("test_artifact_detection")
    def _art():
        for m, r in D.items():
            ar = r["evidence_matrix"]["ARTIFACT_RISK"]
            if ar == "HIGH":
                assert r["decision"] != "MECHANISM_SUPPORTED", f"{m} is SUPPORTED despite HIGH artifact risk"
            if m in ("M03", "M04"):
                assert r["semantic_dependencies"]["UST10Y"].startswith("PROXY"), f"{m} must flag the ^TNX proxy"
        return {"artifact_high": R["artifact_risk_high"], "proxy_flagged": True}

    @case("test_negative_control")
    def _nc():
        nc = R["negative_control"]
        assert "real" in nc and "shuffled" in nc, "negative control was not recorded"
        assert nc.get("status") in ("PASS", "FAIL"), "negative control status missing"
        if nc["status"] == "FAIL":
            # the control did its job: it exposed that the method cannot separate real structure from randomness.
            # The required behaviour is then to invalidate the method - NOT to retune the rules until it passes.
            assert R.get("method_validity") == "INVALID_NEGATIVE_CONTROL_FAILED", \
                "a failed negative control must invalidate the method"
            assert all(r.get("provisional") and not r.get("usable") for r in D.values()), \
                "failed negative control did not mark the mechanism decisions unusable"
            assert R.get("candidate_research", 0) == 0, "candidates emitted despite an invalid method"
        else:
            assert nc["shuffled"].get("MECHANISM_SUPPORTED", 0) <= max(1, nc["real"].get("MECHANISM_SUPPORTED", 0)), \
                "shuffled run produced more supported mechanisms"
        return {"status": nc["status"], "real": nc["real"], "shuffled": nc["shuffled"],
                 "method_validity": R.get("method_validity"), "handled_correctly": True}

    @case("test_hermes_cache")
    def _cache():
        c = json.load(open(os.path.join(MV_DIR, "mechanism_research_cache.json"), encoding="utf-8"))["cache"]
        total_subs = 0
        for m, row in c.items():
            assert row["first_event"]["review_type"] == "FULL_REVIEW", f"{m} first event is not a full review"
            for s in row["subsequent_events"]:
                assert s["review_type"] in ("INCREMENTAL_REVIEW", "NO_NEW_EVIDENCE"), f"{m} illegal review type"
                total_subs += 1
        assert total_subs < R["independent_event_count"], "cache did not compress any review"
        return {"mechanisms": len(c), "subsequent_events": total_subs, "compression": True}

    @case("test_candidate_gate")
    def _gate():
        cands = json.load(open(os.path.join(MV_DIR, "candidate_research.json"), encoding="utf-8"))["entries"]
        for e in cands:
            m = e["mechanism_id"]
            assert D[m]["decision"] == "MECHANISM_SUPPORTED", f"{m} candidate without SUPPORTED"
            assert e["independent_event_count"] >= mv.REGISTRY["minimum_independent_events"], f"{m} below min events"
            assert e["artifact_risk"] != "HIGH", f"{m} candidate with HIGH artifact risk"
            assert e["counter_evidence"]["strongest_counter_evidence"][0] != "C08", f"{m} candidate with C08"
            for bad in ("entry", "exit", "stop", "target", "size"):
                assert bad not in json.dumps(e, ensure_ascii=False).lower().replace("boundary_conditions", ""), \
                    f"{m} candidate mentions {bad}"
        assert len(cands) == R["candidate_research"], "candidate count disagrees with the summary"
        return {"candidates": len(cands), "gate_conditions_enforced": True}

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
        return {"v2_source_modified": 0, "v2_runtime_files": len(a), "task_footprint_in_v2": 0}

    @case("test_order_send_disabled")
    def _orders():
        FORBIDDEN = ("order_send", "order_check", "metatrader5", "broker", "execution", "future_return",
                      "future_pnl", "pnl", "win_rate", "sharpe", "profit_factor", "expected_profit",
                      "expected_return", "profit_score", "win_probability")
        bad = []
        for f in ("mechanism_validation.py", "run_mechanism_validation_r1.py"):
            tree = ast.parse(open(os.path.join(MV_DIR, f), encoding="utf-8").read())
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
            bad += [f"{f}:{t}" for t in FORBIDDEN if t in names]
        assert not bad, f"forbidden identifiers used as code: {bad}"
        reg = json.load(open(os.path.join(MV_DIR, "mechanism_validation_registry.json"), encoding="utf-8"))
        fi = " ".join(reg["forbidden_identifiers"]).lower()
        for t in FORBIDDEN:
            assert t in fi, f"registry does not declare {t} forbidden"
        return {"ast_clean": True, "registry_declares_forbidden": True, "scanned": 2}

    for fn in (_det, _nolook, _replay, _reg, _imm_opp, _imm_qual, _xg, _iec, _cs, _ce, _art, _nc, _cache, _gate,
                _v1, _v2, _orders):
        fn()

    summary = {"schema": "v3_mechanism_tests/1", "total": len(RESULTS),
                "pass": sum(1 for r in RESULTS if r["result"] == "PASS"),
                "fail": sum(1 for r in RESULTS if r["result"] != "PASS"), "results": RESULTS}
    print("\nTESTS:", json.dumps({k: v for k, v in summary.items() if k != "results"}, ensure_ascii=False))
    json.dump(summary, open(os.path.join(HERE, "mechanism_test_results.json"), "w", encoding="utf-8", newline="\n"),
              indent=1, ensure_ascii=False)
    sys.exit(0 if summary["fail"] == 0 else 1)


if __name__ == "__main__":
    main()
