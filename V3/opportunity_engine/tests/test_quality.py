# -*- coding: utf-8 -*-
"""V3 Opportunity Quality Filter R1 — the 12 mandatory tests (section 34).

Run:  python tests/test_quality.py
Self-contained: loads R1 inputs + the gate modules directly. Exits non-zero on any failure.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import quality_filter as qf            # noqa: E402
import run_quality_r1 as orch          # noqa: E402

START = float(os.environ.get("TASK_START_TS", "0")) or (time.time() - 3600)
RESULTS = []


def case(name):
    def deco(fn):
        def run(*a, **k):
            t0 = time.time()
            try:
                d = fn(*a, **k)
                RESULTS.append({"test": name, "result": "PASS", "detail": d, "sec": round(time.time() - t0, 2)})
                print(f"PASS  {name}  {json.dumps(d, ensure_ascii=False)[:220]}")
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
    recs, src = orch.load_opportunities()
    state = {g: pd.read_parquet(os.path.join(ROOT, "state_engine", f"state_{g}.parquet")).sort_index()
              for g in ("1h", "5m")}
    full = orch.assess_all(recs, state)

    @case("test_quality_deterministic")
    def _det():
        again = orch.assess_all(recs, state)
        a = [(x["opportunity_id"], x["quality_decision"]) for x in full]
        b = [(x["opportunity_id"], x["quality_decision"]) for x in again]
        assert a == b, "non-deterministic quality decisions"
        return {"assessed": len(a), "identical": True}

    @case("test_quality_no_lookahead")
    def _nolook():
        cut = int(len(recs) * 0.7)
        tcut = recs[cut - 1]["detected_at"]
        trunc_recs = [r for r in recs if r["detected_at"] <= tcut]
        trunc_state = {g: s[s.index <= pd.Timestamp(tcut)] for g, s in state.items()}
        part = orch.assess_all(trunc_recs, trunc_state)
        f = [x for x in full if x["detected_at"] <= tcut]
        assert [(x["opportunity_id"], x["quality_decision"]) for x in f] == \
               [(x["opportunity_id"], x["quality_decision"]) for x in part], "decision changed when future data was deleted"
        return {"cut": tcut, "assessed_before_cut": len(f), "identical": True}

    @case("test_quality_replay")
    def _replay():
        cut = int(len(recs) * 0.5)
        tcut = recs[cut - 1]["detected_at"]
        rep = orch.assess_all([r for r in recs if r["detected_at"] <= tcut],
                                {g: s[s.index <= pd.Timestamp(tcut)] for g, s in state.items()})
        key = lambda xs: [(x["opportunity_id"], json.dumps(x["quality_matrix"], sort_keys=True), x["quality_decision"])
                           for x in xs]
        assert key(rep) == key([x for x in full if x["detected_at"] <= tcut]), "replay differs from the full run"
        return {"cut": tcut, "replayed": len(rep), "consistent": True}

    @case("test_quality_registry_hash")
    def _reg():
        h1, h2 = qf.registry_hash(), qf.registry_hash()
        assert h1 == h2, "registry hash unstable"
        p = os.path.join(ROOT, "quality", "quality_filter_registry.json")
        if os.path.exists(p):
            h3 = hashlib.sha256(json.dumps(json.load(open(p, encoding="utf-8")), sort_keys=True,
                                             ensure_ascii=False).encode()).hexdigest()
            assert h3 == h1, "written registry file hash differs from the live registry"
        return {"registry_hash": h1[:20], "stable": True, "matches_written_file": os.path.exists(p)}

    @case("test_quality_immutable_input")
    def _immutable():
        p = os.path.join(ROOT, "quality", "quality_filter_audit.json")
        assert os.path.exists(p), "audit file missing - run the orchestrator first"
        aud = json.load(open(p, encoding="utf-8"))
        now = {g: orch.sha_file(os.path.join(ROOT, "ledger", f"v3_opportunity_ledger_{g}.jsonl")) for g in ("1h", "5m")}
        assert all(now[g] == aud["input_files"][g]["sha256"] for g in now), "R1 ledger changed after the run"
        assert aud["input_unchanged_after_run"] is True, "audit reports the input changed"
        return {"r1_ledger_hashes_unchanged": True, "audit_input_hash": aud["input_hash"][:16]}

    @case("test_quality_no_future_return")
    def _nofut():
        import ast
        TOK = ("future_return", "win_rate", "profit_factor", "sharpe", "expected_profit",
               "expected_return", "pnl", "profit_score", "win_probability")

        def identifiers(path):
            tree = ast.parse(open(path, encoding="utf-8").read())
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
            return names

        used = []
        for f in ("quality_filter.py", "run_quality_r1.py"):
            ids = identifiers(os.path.join(ROOT, f))
            used += [f"{f}:{t}" for t in TOK if t in ids]
        assert not used, f"forbidden quantities exist as real identifiers: {used}"
        reg = json.load(open(os.path.join(ROOT, "quality", "quality_filter_registry.json"), encoding="utf-8"))
        fb = " ".join(reg.get("forbidden_fields", [])).lower()
        for t in TOK:
            assert t in fb, f"registry does not declare {t} forbidden"
        aud = json.load(open(os.path.join(ROOT, "quality", "quality_filter_audit.json"), encoding="utf-8"))
        assert aud.get("future_return_used") is False, "audit does not assert no future-return usage"
        return {"identifiers_absent": True, "declared_forbidden_in_registry": True,
                 "audit_asserts_no_future_return": True, "scanned": ["quality_filter.py", "run_quality_r1.py"]}

    @case("test_hermes_three_way_decision")
    def _threeway():
        p = os.path.join(ROOT, "hermes", "hermes_quality_reviews.json")
        assert os.path.exists(p), "hermes reviews missing - run the orchestrator"
        rev = json.load(open(p, encoding="utf-8"))["reviews"]
        dec = {}
        for r in rev:
            d = r["review_status"]
            assert d in ("INVESTIGATE", "REJECT", "INSUFFICIENT_EVIDENCE"), f"illegal decision {d}"
            dec[d] = dec.get(d, 0) + 1
        assert len(dec) >= 2, f"Hermes still collapses to a single decision: {dec}"
        return {"decisions": dec, "distinct": len(dec)}

    @case("test_candidate_schema")
    def _cand():
        p = os.path.join(ROOT, "quality", "candidate_research.json")
        assert os.path.exists(p), "candidate file missing"
        ents = json.load(open(p, encoding="utf-8"))["entries"]
        need = ["opportunity_id", "cluster_id", "detector_id", "quality_matrix", "hermes_review",
                 "mechanism_hypotheses", "counter_evidence", "data_quality", "semantic_dependencies",
                 "decision_reason", "context_hash"]
        for e in ents:
            miss = [k for k in need if k not in e]
            assert not miss, f"candidate {e.get('opportunity_id')} missing {miss}"
        return {"candidates": len(ents), "schema_ok": True}

    @case("test_ledger_chain")
    def _chain():
        lp = os.path.join(ROOT, "ledger", "v3_opportunity_quality_ledger.jsonl")
        v = qf.QualityLedger.verify(lp)
        assert v["chain_ok"] and v["rows"] > 0, f"quality ledger chain failed: {v}"
        tmp = os.path.join(ROOT, "ledger", "_tmp_qf_chain.jsonl")
        if os.path.exists(tmp):
            os.remove(tmp)
        L = qf.QualityLedger(tmp, qf.registry_hash())
        for i in range(4):
            L.append({"i": i})
        assert qf.QualityLedger.verify(tmp)["chain_ok"], "fresh chain invalid"
        lines = open(tmp, encoding="utf-8").read().splitlines()
        row = json.loads(lines[1]); row["payload"]["i"] = 99
        lines[1] = json.dumps(row, sort_keys=True, ensure_ascii=False)
        open(tmp, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
        assert not qf.QualityLedger.verify(tmp)["chain_ok"], "tampering not detected"
        os.remove(tmp)
        return {"rows": v["rows"], "chain_ok": True, "tamper_detected": True}

    SOURCE_EXT = (".py", ".yaml", ".yml", ".toml", ".cfg", ".ini")

    def _classify(root):
        srcf, art = [], []
        for r, _, fs in os.walk(root):
            for f in fs:
                p = os.path.join(r, f)
                try:
                    if os.path.getmtime(p) <= START:
                        continue
                except OSError:
                    continue
                rel = os.path.relpath(p, root).lower()
                (srcf if rel.endswith(SOURCE_EXT) else art).append(p)
        return srcf, art

    @case("test_v1_isolation")
    def _v1():
        s, a = _classify(r"C:\AIQuant\research\hermes\trader_v1")
        assert not s, f"V1 source/config modified: {s[:3]}"
        return {"v1_source_modified": 0, "v1_own_runtime_files": len(a)}

    @case("test_v2_isolation")
    def _v2():
        s, a = _classify(r"C:\AIQuant\research\hermes\trader_v2")
        assert not s, f"V2 source/config modified: {s[:3]}"
        assert not [p for p in a if "v3_opportunity_engine" in p.lower()], "task footprint inside V2"
        return {"v2_source_modified": 0, "v2_own_runtime_files": len(a), "task_footprint_in_v2": 0}

    @case("test_order_send_disabled")
    def _orders():
        for f in ("quality_filter.py", "run_quality_r1.py"):
            s = open(os.path.join(ROOT, f), encoding="utf-8").read().lower()
            for tok in ("order_send", "order_check", "metatrader5", "import mt5", "broker_exec"):
                assert tok not in s, f"{f} references {tok}"
        sch = json.load(open(os.path.join(ROOT, "schemas", "opportunity_schema.json"), encoding="utf-8"))
        fb = " ".join(sch.get("forbidden_fields", [])).lower()
        for tok in ("order", "signal", "profit_score", "win_probability"):
            assert tok in fb, f"schema does not forbid {tok}"
        return {"no_order_path": True, "schema_forbids_order_fields": True}

    # run all
    for fn in (_det, _nolook, _replay, _reg, _immutable, _nofut, _threeway, _cand, _chain, _v1, _v2, _orders):
        fn()

    summary = {"schema": "v3_quality_tests/1", "total": len(RESULTS),
                "pass": sum(1 for r in RESULTS if r["result"] == "PASS"),
                "fail": sum(1 for r in RESULTS if r["result"] != "PASS"), "results": RESULTS}
    print("\nTESTS:", json.dumps({k: v for k, v in summary.items() if k != "results"}, ensure_ascii=False))
    json.dump(summary, open(os.path.join(ROOT, "tests", "quality_test_results.json"), "w",
                             encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
    sys.exit(0 if summary["fail"] == 0 else 1)


if __name__ == "__main__":
    main()
