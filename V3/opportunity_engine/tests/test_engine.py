# -*- coding: utf-8 -*-
"""V3 Opportunity Engine R1 — the 11 mandatory tests (section 27).

Run:  python tests/test_engine.py <state_parquet> <ledger_path> <v1_dir> <v2_dir>
Exits non-zero if any test fails. Prints a machine-readable summary at the end.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import engine  # noqa: E402

RESULTS = []


def case(name):
    def deco(fn):
        def run(*a, **k):
            t0 = time.time()
            try:
                detail = fn(*a, **k)
                RESULTS.append({"test": name, "result": "PASS", "detail": detail, "sec": round(time.time() - t0, 2)})
                print(f"PASS  {name}  {detail}")
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
    state_p, ledger_p, v1, v2 = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    S = pd.read_parquet(state_p)
    S = S.sort_index()

    @case("test_asof_features")
    def _asof():
        cut = int(len(S) * 0.7)
        a = S.iloc[:cut + 1]
        assert a.index.equals(S.iloc[:cut + 1].index), "index mismatch"
        # recomputing features on a truncated frame must not change the earlier rows
        b = engine.build_state(a[["xau", "dxy", "vix", "tnx"]])
        common = b.index.intersection(S.index[:cut + 1])
        cols = [c for c in b.columns if b[c].dtype.kind in "fi"]
        d = (b.loc[common, cols].fillna(-999) - S.loc[common, cols].fillna(-999)).abs().max().max()
        assert float(d) < 1e-9, f"state changed when future rows were removed (max diff {d})"
        return {"rows_checked": int(len(common)), "max_abs_diff": float(d)}

    @case("test_no_lookahead")
    def _nolook():
        cut = int(len(S) * 0.7)
        tcut = S.index[cut]
        full = engine.detect(S)
        trunc = engine.detect(S.iloc[:cut + 1])
        f = [r for r in full if pd.Timestamp(r["detected_at"]) <= tcut]
        assert len(f) == len(trunc), f"opportunity count before cut differs: full={len(f)} trunc={len(trunc)}"
        assert [r["context_hash"] for r in f] == [r["context_hash"] for r in trunc], "context hashes differ"
        return {"cut": str(tcut), "opps_before_cut": len(f), "identical": True}

    @case("test_deterministic_detection")
    def _det():
        a = engine.detect(S); b = engine.detect(S)
        assert [r["context_hash"] for r in a] == [r["context_hash"] for r in b], "non-deterministic detection"
        return {"opps": len(a), "identical": True}

    @case("test_context_hash")
    def _ctx():
        a = engine.detect(S)
        if not a:
            return {"skipped": "no opportunities"}
        h1 = a[0]["context_hash"]
        h2 = hashlib.sha256(json.dumps({"t": a[0]["detected_at"], "type": a[0]["opportunity_type"],
                                          "det": a[0]["trigger"],
                                          "feat": a[0]["feature_values"]}, sort_keys=True).encode()).hexdigest()
        assert h1 == h2, "context_hash is not reproducible from the record"
        return {"first_ctx": h1[:16], "reproducible": True}

    @case("test_ledger_chain")
    def _chain():
        L = engine.Ledger(ledger_p)
        t = os.path.join(os.path.dirname(ledger_p), "_tmp_chain_test.jsonl")
        if os.path.exists(t):
            os.remove(t)
        L2 = engine.Ledger(t)
        for i in range(5):
            L2.append({"i": i, "x": "y"})
        v = engine.Ledger.verify(t)
        assert v["chain_ok"] and v["rows"] == 5, f"chain verify failed: {v}"
        # tamper -> must fail
        lines = open(t, encoding="utf-8").read().splitlines()
        row = json.loads(lines[2]); row["payload"]["i"] = 999
        lines[2] = json.dumps(row, sort_keys=True, ensure_ascii=False)
        open(t, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
        v2 = engine.Ledger.verify(t)
        os.remove(t)
        assert not v2["chain_ok"], "tampered ledger still verified"
        return {"chain_ok": True, "tamper_detected": True}

    @case("test_replay_consistency")
    def _replay():
        cut = int(len(S) * 0.7)
        trunc, full = engine.replay(S, cut)
        f = [r["context_hash"] for r in full if pd.Timestamp(r["detected_at"]) <= S.index[cut]]
        assert f == [r["context_hash"] for r in trunc], "replay prefix differs from the full run"
        return {"cut": str(S.index[cut]), "prefix_len": len(f), "consistent": True}

    @case("test_duplicate_opportunity")
    def _dup():
        a = engine.cluster(engine.detect(S))
        seen = {(r["cluster_id"], r["detected_at"]) for r in a}
        assert len(seen) == len(a), "duplicate (cluster_id, detected_at) pairs"
        cont = sum(1 for r in a if r.get("is_cluster_continuation"))
        return {"records": len(a), "unique_pairs": len(seen), "cluster_continuations": cont}

    @case("test_timestamp_alignment")
    def _align():
        assert S.index.is_monotonic_increasing, "state index not monotonic"
        assert not S.index.duplicated().any(), "duplicate timestamps in state"
        assert S.index.tz is not None, "state index is not tz-aware (UTC required)"
        return {"rows": int(len(S)), "tz": str(S.index.tz), "monotonic": True, "unique": True}

    SOURCE_EXT = (".py", ".yaml", ".yml", ".toml", ".cfg", ".ini")
    ARTIFACT_DIRS = ("runs", "data_cache", "observations", "run_state", "__pycache__", "logs", "decisions",
                     "state")

    def _classify(root):
        """Isolation invariant for a RUNNING peer system:
        THIS task must not modify the peer's source or configuration. The peer's own runtime artifacts
        (run dirs, decision files, caches, observations) legitimately change while the peer runs; they are
        counted and reported, never silently ignored. Attribution also requires that none of this task's
        outputs live under the peer's tree."""
        src, art = [], []
        for r, _, fs in os.walk(root):
            for f in fs:
                p = os.path.join(r, f)
                try:
                    if os.path.getmtime(p) <= START:
                        continue
                except OSError:
                    continue
                rel = os.path.relpath(p, root).lower()
                is_art = any(d in rel for d in ARTIFACT_DIRS) or not rel.endswith(SOURCE_EXT)
                (art if is_art else src).append(p)
        return src, art

    @case("test_v1_isolation")
    def _v1():
        src, art = _classify(v1)
        assert not src, f"V1 source/config modified: {src[:3]}"
        return {"v1_source_or_config_modified": 0, "v1_runtime_artifacts_written_by_v1": len(art)}

    @case("test_v2_isolation")
    def _v2():
        src, art = _classify(v2)
        assert not src, f"V2 source/config modified: {src[:3]}"
        own = [p for p in art if "v3_opportunity_engine" in p.lower()]
        assert not own, f"this task wrote inside V2: {own[:2]}"
        return {"v2_source_or_config_modified": 0, "v2_runtime_artifacts_written_by_v2": len(art),
                 "task_footprint_inside_v2": 0,
                 "artifact_examples": [os.path.basename(p) for p in art[:3]]}

    @case("test_order_send_disabled")
    def _orders():
        scanned = []
        for f in ("engine.py", "run_r1.py"):
            s = open(os.path.join(ROOT, f), encoding="utf-8").read().lower()
            for token in ("order_send", "order_check", "metatrader5", "import mt5"):
                assert token not in s, f"{f} references {token}"
            scanned.append(f)
        sp = os.path.join(ROOT, "schemas", "opportunity_schema.json")
        sch = json.load(open(sp, encoding="utf-8"))
        fb = " ".join(sch.get("forbidden_fields", [])).lower()
        for tok in ("order", "signal", "profit_score", "win_probability", "expected_profit"):
            assert tok in fb, f"opportunity schema does not forbid {tok}"
        return {"engine_no_order_path": True, "files_scanned": scanned, "schema_forbids_order_fields": True}

    # runner
    _asof(); _nolook(); _det(); _ctx(); _chain(); _replay(); _dup(); _align(); _v1(); _v2(); _orders()
    summary = {"schema": "v3_opportunity_tests/1", "total": len(RESULTS),
                "pass": sum(1 for r in RESULTS if r["result"] == "PASS"),
                "fail": sum(1 for r in RESULTS if r["result"] != "PASS"), "results": RESULTS}
    print("\nTESTS:", json.dumps({k: v for k, v in summary.items() if k != "results"}, ensure_ascii=False))
    out = os.path.join(ROOT, "tests", "test_results.json")
    json.dump(summary, open(out, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
    sys.exit(0 if summary["fail"] == 0 else 1)


if __name__ == "__main__":
    START = float(os.environ.get("TASK_START_TS", "0")) or time.time() - 10 ** 9
    main()
