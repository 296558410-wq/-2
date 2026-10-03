# -*- coding: utf-8 -*-
"""V1-R8-B SCENARIO BLIND VALIDATION — SCAFFOLD (read-only on R3..R8-A; adds only v1_r8_b_validation/).

Builds a fresh pre-registered PIT sample (EFFECTIVE_N >= 30), its contexts (via the frozen R3 builder,
read-only) and the ground-truth SCENARIO family at t+H for evaluation only.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

REPO = r"C:\AIQuant"
BASE = os.path.join(REPO, "research", "hermes", "trader_v1")
ROOT = os.path.join(BASE, "v1_r8_b_validation")
R3 = os.path.join(BASE, "v1_r3_hermes_market_forecast")
R5 = os.path.join(BASE, "v1_r5_hermes_forecast_discipline")
R8A = os.path.join(BASE, "v1_r8_target_redesign")
CACHE = os.path.join(BASE, "v1_r2_full_optimization", "states", "state_v2_series.parquet")
LEDGER = os.path.join(ROOT, "ledger", "v1_r8_b_ledger.jsonl")
NOW = datetime.now(timezone.utc).isoformat()
H = 4
FROZEN = {k: os.path.join(BASE, v) for k, v in {
    "R3": "v1_r3_hermes_market_forecast", "R4": "v1_r4_hermes_audit", "R5": "v1_r5_hermes_forecast_discipline",
    "R5_1": "v1_r5_1_subagent_persistence", "R6": "v1_r6_hermes_validation", "R7": "v1_r7_information_diagnostic",
    "R8_A": "v1_r8_target_redesign"}.items()}
DIRS = ["registry", "context", "prompt", "forecasts", "outcomes", "evaluation", "ledger", "reports", "tests", "audit", "staging"]


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def wjson(rel, o):
    p = os.path.join(ROOT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(o, open(p, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False, default=str)
    return p


def ledger_append(entries):
    prev, seq = "0" * 64, 0
    if os.path.exists(LEDGER):
        for line in open(LEDGER, encoding="utf-8"):
            line = line.strip()
            if line:
                prev = json.loads(line)["current_hash"]; seq += 1
    with open(LEDGER, "a", encoding="utf-8", newline="\n") as fh:
        for e in entries:
            seq += 1
            rec = {"seq": seq, "ts_utc": NOW, **e, "previous_hash": prev}
            rec["current_hash"] = sha_obj({k: v for k, v in rec.items() if k != "current_hash"})
            prev = rec["current_hash"]
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return seq


def main():
    for d in DIRS:
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)
    bl = {}
    for k, v in FROZEN.items():
        files = {}
        for dp, _, fs in os.walk(v):
            for f in fs:
                fp = os.path.join(dp, f)
                if os.path.isfile(fp):
                    files[os.path.relpath(fp, v).replace("\\", "/")] = sha_file(fp)
        bl[k] = files
    reg8 = json.load(open(os.path.join(R8A, "registry", "v1_r8_target_registry_v2.json"), encoding="utf-8"))
    FAMILY = reg8["scenario_definition"]["families"]
    sel_h = int(reg8["scenario_definition"]["horizon"])
    assert sel_h == H, f"frozen horizon is {sel_h}"
    # ---- fresh pre-registered sample: every 2 days at 00:00Z, 2026-07-17..2026-09-17 (new rule, not used before) ----
    days = pd.date_range("2026-07-17", "2026-09-17", freq="2D", tz="UTC")
    sample = sorted({str(d.replace(hour=0)) for d in days})
    df = pd.read_parquet(CACHE); df["ts"] = pd.to_datetime(df["ts"], utc=True)
    fam_series = df["state"].map(FAMILY)
    # ---- contexts (frozen R3 builder, read-only) ----
    spec = importlib.util.spec_from_file_location("r3ctx", os.path.join(R3, "_r3_context.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    tf, cache, xs = m.load()
    m15 = tf["M15"]; structure = m.structure_series(m15)
    pre = {name: m.precompute(d) for name, d in tf.items()}
    rows, built = [], {}
    for s in sample:
        t = pd.Timestamp(s)
        c = m.build_context(tf, cache, xs, m15, structure, t, pre)
        fn = s.replace(":", "").replace("-", "").replace("+0000", "Z").replace(" ", "T")
        built[s] = c
        with open(os.path.join(ROOT, "context", f"CTX_{fn}.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(c, fh, indent=1, ensure_ascii=False)
        # ground truth at t+H (evaluation only; NEVER given to Hermes-A)
        i = int(df.index[df["ts"] <= t][-1]) if (df["ts"] <= t).any() else None
        nxt = None
        if i is not None and i + H < len(df):
            nxt = fam_series.iloc[i + H]
            open(os.path.join(ROOT, "outcomes", f"OUTCOME_{fn}.json"), "w", encoding="utf-8", newline="\n").write(
                json.dumps({"ts": s, "H": H, "family_at_H": nxt, "state_now": df["state"].iloc[i],
                             "family_now": fam_series.iloc[i], "state_at_H": df["state"].iloc[i + H]}, ensure_ascii=False))
        rows.append({"ts": s, "file": f"CTX_{fn}.json", "outcome_file": f"OUTCOME_{fn}.json", "family_now": fam_series.iloc[i] if i is not None else None,
                      "family_at_H": nxt})
    valid = [r for r in rows if r["family_at_H"] is not None]
    a_prompt = open(os.path.join(R5, "prompt", "hermes_a_r5_prompt.txt"), encoding="utf-8").read()
    r5hash = json.load(open(os.path.join(R5, "registry", "v1_r5_registry.json"), encoding="utf-8"))["prompt_hashes"]["hermes_a_r5"]
    reg = {"task": "V1_R8_B_SCENARIO_VALIDATION", "registry_id": "v1r8b-valid-registry-r1", "frozen_at_utc": NOW,
            "read_only_on": list(FROZEN) + ["registry_v2", "AMENDMENT_1"],
            "target": {"families": FAMILY, "horizon": H, "abstain_rule": reg8["scenario_definition"]["abstention_rules"],
                        "uncertainty_rule": reg8["scenario_definition"]["uncertainty_rules"],
                        "scenario_definition_hash": reg8["scenario_definition_hash"], "registry_v2_hash": reg8["registry_hash"]},
            "sample": {"declared_n": len(valid), "rule": "every 2 days at 00:00Z inside 2026-07-17..2026-09-17 (fresh, pre-registered, no cherry-picking)",
                        "EFFECTIVE_N_target": 30, "points": [r["ts"] for r in valid]},
            "prompt": {"hermes_a_r5_reused": True, "prompt_hash": r5hash, "prompt_unchanged": hashlib.sha256(a_prompt.encode()).hexdigest() == r5hash},
            "baselines": ["MAJORITY", "PERSISTENCE", "SIMPLE_TRANSITION", "FROZEN_BASELINE"],
            "metrics": ["BALANCED_ACCURACY", "RAW_ACCURACY", "CLASS_RECALL", "ABSTENTION_RATE", "ECE"],
            "chance": 0.3333, "persistence_protocol": "R5.1 parent-authoritative, batch<=5",
            "prohibited": ["future_return", "future_PnL", "profit_score", "win_probability", "expected_profit", "trading_signal",
                            "MetaTrader5", "order_send", "order_check", "broker", "modifying the frozen target/horizon/abstain/prompt",
                            "sample cherry-picking", "changing rules after seeing results"],
            "frozen_hashes": {k: sha_obj(v) for k, v in bl.items()}}
    reg["registry_hash"] = sha_obj({k: v for k, v in reg.items() if k != "registry_hash"})
    wjson("registry/v1_r8_b_registry.json", reg)
    wjson("registry/FROZEN_BASELINES.json", {"ts_utc": NOW, "frozen": {k: {"file_count": len(v), "baseline_hash": sha_obj(v)} for k, v in bl.items()}})
    wjson("context/SAMPLE_INDEX.json", {"n": len(valid), "rows": valid})
    seq = ledger_append([{"event": "registry_frozen", "registry_hash": reg["registry_hash"],
                           "target": reg["target"], "declared_n": len(valid)}])
    print("ROOT:", ROOT)
    print("registry_hash:", reg["registry_hash"][:16], "| H:", H, "| declared n:", len(valid), "| prompt unchanged:", reg["prompt"]["prompt_unchanged"])
    print("sample:", [r["ts"] for r in valid][:5], "...", [r["ts"] for r in valid][-3:])
    print("ledger:", seq)
    for k, v in bl.items():
        print(f"  {k} frozen: {sha_obj(v)[:16]} ({len(v)} files)")


if __name__ == "__main__":
    main()
