# -*- coding: utf-8 -*-
"""V1-R2 PHASE B-R5 — ns_v3 module-level refactor proof (BEFORE / AFTER stages).

Stage before: SOURCE_HASH_BEFORE, semantic_rule_hash_before (ast-normalized logic hash of
  ns_v3/groups_of/rule_mu/rule_variant), and ns_v3 outputs on:
    - 40,546 historical states (B2 stored rows, frozen evidence)
    - 1,328 tick-only states (B4 m15_tick_bid.parquet)
Stage after : SOURCE_HASH_AFTER, semantic_rule_hash_after, recompute same outputs,
  per-row comparison -> DIFF_ROWS, writes reports/V1_R2_NS_V3_REFACTOR_AUDIT.json.
Read-only w.r.t. trading/data. No orders. No engine.py. GIT_COMMIT=NONE."""
from __future__ import annotations

import ast
import glob
import hashlib
import importlib.util
import json
import os
import sys
import textwrap
from datetime import datetime, timezone

import pandas as pd

REPO = r"C:\AIQuant"
UP = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_prediction_upgrade")
R1_PATH = os.path.join(UP, "_v1r2_phaseB_R1.py")
R2_PATH = os.path.join(UP, "_v1r2_phaseB_R2.py")
R2_REFACTORED_PATH = os.path.join(UP, "_v1r2_phaseB_R2.py")  # after in-place refactor
REPORTS = os.path.join(UP, "reports")
BEFORE_EV = os.path.join(UP, "_v1r2_phaseB_R5_refactor_before.json")
AFTER_EV = os.path.join(UP, "_v1r2_phaseB_R5_refactor_after.json")
RULE_FNS = ("ns_v3", "groups_of", "rule_mu", "rule_variant")


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def wjson(p, o):
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, default=str)


def find_fn(tree, name):
    """Return the FunctionDef node named `name` (module level or nested)."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def logic_hash(src_text, names):
    """Semantic rule hash: sha256 over ast.dump of each named function (logic only, no comments/whitespace)."""
    tree = ast.parse(src_text)
    parts = []
    for n in names:
        node = find_fn(tree, n)
        if node is None:
            parts.append(n + ":MISSING")
        else:
            parts.append(n + ":" + ast.dump(node, include_attributes=False))
    return sha_obj(sorted(parts))


def extract_ns_v3(src_text, groups_of):
    """Extract the ns_v3 FunctionDef (nested in main()) and return a runnable function.
    groups_of is injected from the module scope (the closure referenced the same module-level fn)."""
    tree = ast.parse(src_text)
    node = find_fn(tree, "ns_v3")
    if node is None:
        raise RuntimeError("ns_v3 not found")
    seg = textwrap.dedent(ast.get_source_segment(src_text, node))
    ns = {"groups_of": groups_of}
    exec(seg, ns)  # noqa: S102 - controlled local namespace
    return ns["ns_v3"]


def load_hist_states():
    b2 = sorted(glob.glob(os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B2_*")))[-1]
    p = os.path.join(b2, "v1_r2_states_v2.jsonl")
    rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    return rows


def load_tick_states():
    b4 = sorted(glob.glob(os.path.join(UP, "v1_r2_research_runs", "V1_R2_RUN_B4_*")))[-1]
    pq = os.path.join(b4, "m15_tick_bid.parquet")
    df = pd.read_parquet(pq)
    R1 = load_mod("v1r2_r1", R1_PATH)
    jd = R1.indicators(df.copy())
    return R1.engines_v2(jd)


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "before"
    src = open(R2_PATH, encoding="utf-8").read()
    source_hash = sha_file(R2_PATH)
    sem_hash = logic_hash(src, RULE_FNS)

    hist = load_hist_states()
    tick = load_tick_states()

    if stage == "before":
        R2_mod = load_mod("v1r2_r2_orig", R2_PATH)
        ns_before = extract_ns_v3(src, R2_mod.groups_of)
        hist_out = [ns_before(r) for r in hist]
        tick_out = [ns_before(r) for r in tick]
        ev = {"stage": "before", "source_hash": source_hash, "semantic_rule_hash": sem_hash,
              "hist_rows": len(hist), "tick_rows": len(tick),
              "hist_outputs_hash": sha_obj(hist_out), "tick_outputs_hash": sha_obj(tick_out),
              "hist_outputs": hist_out, "tick_outputs": tick_out,
              "ts_utc": datetime.now(timezone.utc).isoformat()}
        wjson(BEFORE_EV, ev)
        print("STAGE=before")
        print("SOURCE_HASH_BEFORE =", source_hash)
        print("SEMANTIC_RULE_HASH_BEFORE =", sem_hash)
        print("hist outputs hash:", ev["hist_outputs_hash"][:16], "| tick outputs hash:", ev["tick_outputs_hash"][:16])
        print("BEFORE EVIDENCE WRITTEN ->", BEFORE_EV)
        return

    if stage == "after":
        src = open(R2_REFACTORED_PATH, encoding="utf-8").read()
        source_hash = sha_file(R2_REFACTORED_PATH)
        sem_hash = logic_hash(src, RULE_FNS)
        R2 = load_mod("v1r2_r2_refactored", R2_REFACTORED_PATH)
        ns_after = R2.ns_v3
        if getattr(ns_after, "__closure__", None) is not None:
            print("FATAL: ns_v3 still a closure (not module-level)")
            sys.exit(2)
        hist_out = [ns_after(r) for r in hist]
        tick_out = [ns_after(r) for r in tick]
        before = json.load(open(BEFORE_EV, encoding="utf-8"))
        diff_hist = sum(1 for a, b in zip(before["hist_outputs"], hist_out) if a != b)
        diff_tick = sum(1 for a, b in zip(before["tick_outputs"], tick_out) if a != b)
        sem_eq = (sem_hash == before["semantic_rule_hash"])
        logic_change = "DETECTED" if (not sem_eq or diff_hist or diff_tick) else "NONE"
        audit = {"task": "V1_R2_NS_V3_REFACTOR_AUDIT", "refactor": "ns_v3 moved from main() closure to module level "
                   "(groups_of/rule_mu/rule_variant already module-level); function bodies byte-identical",
                 "DATASET_VARIANT": "TICK_ONLY",
                 "SOURCE_HASH_BEFORE": before["source_hash"], "SOURCE_HASH_AFTER": source_hash,
                 "semantic_rule_hash_before": before["semantic_rule_hash"],
                 "semantic_rule_hash_after": sem_hash,
                 "semantic_equality": sem_eq,
                 "hist_rows": len(hist), "tick_rows": len(tick),
                 "DIFF_ROWS_HIST": diff_hist, "DIFF_ROWS_TICK": diff_tick, "DIFF_ROWS": diff_hist + diff_tick,
                 "hist_outputs_hash_before": before["hist_outputs_hash"], "hist_outputs_hash_after": sha_obj(hist_out),
                 "tick_outputs_hash_before": before["tick_outputs_hash"], "tick_outputs_hash_after": sha_obj(tick_out),
                 "REFACTOR_LOGIC_CHANGE": logic_change,
                 "SEMANTIC_EQUIVALENCE": "PASS" if (sem_eq and diff_hist == 0 and diff_tick == 0) else "FAIL",
                 "ts_utc": datetime.now(timezone.utc).isoformat()}
        wjson(AFTER_EV, {"stage": "after", "source_hash": source_hash, "semantic_rule_hash": sem_hash,
                          "hist_outputs": hist_out, "tick_outputs": tick_out,
                          "ts_utc": audit["ts_utc"]})
        wjson(os.path.join(REPORTS, "V1_R2_NS_V3_REFACTOR_AUDIT.json"), audit)
        print("STAGE=after")
        print("SOURCE_HASH_AFTER =", source_hash)
        print("SEMANTIC_RULE_HASH_AFTER =", sem_hash)
        print("DIFF_ROWS_HIST =", diff_hist, "| DIFF_ROWS_TICK =", diff_tick)
        print("SEMANTIC_EQUIVALENCE =", audit["SEMANTIC_EQUIVALENCE"])
        print("REFACTOR_LOGIC_CHANGE =", logic_change)
        if audit["SEMANTIC_EQUIVALENCE"] != "PASS":
            sys.exit(1)
        print("REFACTOR AUDIT WRITTEN ->", os.path.join(REPORTS, "V1_R2_NS_V3_REFACTOR_AUDIT.json"))
        return

    print("unknown stage:", stage)
    sys.exit(2)


if __name__ == "__main__":
    main()
