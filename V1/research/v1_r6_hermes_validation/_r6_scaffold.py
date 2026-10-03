# -*- coding: utf-8 -*-
"""V1-R6 HERMES VALIDATION — SCAFFOLD: freeze R3/R4/R5/R5.1, pre-register a >=30-point blind set,
and build its PIT contexts by REUSING the frozen R3 context-builder logic (no R3 file is touched).

Only adds v1_r6_hermes_validation/.
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

BASE = r"C:\AIQuant\research\hermes\trader_v1"
ROOT = os.path.join(BASE, "v1_r6_hermes_validation")
FROZEN = {"R3": os.path.join(BASE, "v1_r3_hermes_market_forecast"),
           "R4": os.path.join(BASE, "v1_r4_hermes_audit"),
           "R5": os.path.join(BASE, "v1_r5_hermes_forecast_discipline"),
           "R5_1": os.path.join(BASE, "v1_r5_1_subagent_persistence")}
ledger_path = os.path.join(ROOT, "ledger", "v1_r6_ledger.jsonl")
NOW = datetime.now(timezone.utc).isoformat()
DIRS = ["registry", "context", "prompt", "forecasts", "blind_audits", "adversarial_audits", "post_outcome",
        "evaluation", "ledger", "reports", "tests", "audit", "staging"]


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def wjson(rel, o):
    p = os.path.join(ROOT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, default=str)
    return p


def baseline(root):
    files = {}
    for dp, _, fs in os.walk(root):
        for f in fs:
            fp = os.path.join(dp, f)
            if os.path.isfile(fp):
                files[os.path.relpath(fp, root).replace("\\", "/")] = sha_file(fp)
    return {"file_count": len(files), "baseline_hash": sha_obj(files), "files": files}


def main():
    for d in DIRS:
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)
    frozen = {k: baseline(v) for k, v in FROZEN.items()}
    wjson("registry/FROZEN_BASELINES.json", {"ts_utc": NOW, "frozen": frozen})
    # ---- pre-registered sample: every 2 days at 12:00Z inside the cross-market-covered blind window ----
    start, end = pd.Timestamp("2026-07-18T00:00Z"), pd.Timestamp("2026-09-16T00:00Z")
    days = pd.date_range(start, end, freq="2D")
    sample = [str(d.replace(hour=12)) for d in days]
    sample = sorted(set(sample))
    # ---- build contexts by reusing the FROZEN R3 builder logic (read-only import) ----
    spec = importlib.util.spec_from_file_location("r3ctx", os.path.join(FROZEN["R3"], "_r3_context.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)              # defines functions only; main() is NOT called
    tf, cache, xs = m.load()
    m15 = tf["M15"]
    structure = m.structure_series(m15)
    pre = {name: m.precompute(df) for name, df in tf.items()}
    built = {}
    for s in sample:
        t = pd.Timestamp(s)
        built[s] = m.build_context(tf, cache, xs, m15, structure, t, pre)
    idx_hash = sha_obj(built)
    wjson("context/CONTEXT_SAMPLE_INDEX.json", {"sample": sample, "n": len(sample), "contexts_hash": idx_hash,
                                                  "rule": "every 2 days at 12:00Z inside 2026-07-18..2026-09-16 (fixed, no cherry-picking)",
                                                  "builder": "frozen R3 context builder imported read-only"})
    os.makedirs(os.path.join(ROOT, "context", "samples"), exist_ok=True)
    for s, c in built.items():
        fn = s.replace(":", "").replace("-", "").replace("+0000", "Z").replace(" ", "T")
        with open(os.path.join(ROOT, "context", "samples", f"CTX_{fn}.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(c, fh, indent=1, ensure_ascii=False)
    # ---- prompts (frozen copies; R5 Hermes-A prompt is reused verbatim) ----
    a_prompt = open(os.path.join(FROZEN["R5"], "prompt", "hermes_a_r5_prompt.txt"), encoding="utf-8").read()
    b_blind = open(os.path.join(FROZEN["R4"], "prompt", "hermes_b_blind_prompt.txt"), encoding="utf-8").read()
    b_adv = open(os.path.join(FROZEN["R5"], "prompt", "hermes_b_adversarial_r5_prompt.txt"), encoding="utf-8").read()
    for name, txt in (("hermes_a_r6.txt", a_prompt), ("hermes_b_blind_r6.txt", b_blind), ("hermes_b_adversarial_r6.txt", b_adv)):
        p = os.path.join(ROOT, "prompt", name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8", newline="\n").write(txt)
    r5_prompt_hash = json.load(open(os.path.join(FROZEN["R5"], "registry", "v1_r5_registry.json"), encoding="utf-8"))["prompt_hashes"]["hermes_a_r5"]
    reg = {"task": "V1_R6_HERMES_VALIDATION", "registry_id": "v1r6-validation-registry-r1", "frozen": True,
            "frozen_at_utc": NOW, "r3_r4_r5_r51_immutable": True,
            "frozen_hashes": {k: v["baseline_hash"] for k, v in frozen.items()},
            "sample": {"n": len(sample), "points": sample, "EFFECTIVE_N_target": 30, "rule": "pre-registered, fixed, PIT-safe"},
            "reuse_r5_prompt": True, "r5_prompt_hash": r5_prompt_hash,
            "prompt_hashes": {"hermes_a_r6": hashlib.sha256(a_prompt.encode()).hexdigest(),
                               "hermes_b_blind_r6": hashlib.sha256(b_blind.encode()).hexdigest(),
                               "hermes_b_adversarial_r6": hashlib.sha256(b_adv.encode()).hexdigest()},
            "prompt_unchanged_vs_r5": hashlib.sha256(a_prompt.encode()).hexdigest() == r5_prompt_hash,
            "comparisons": ["R5_HERMES_A", "R6_HERMES_A", "SIMPLE_BASELINE", "R6_HERMES_B"],
            "metrics": ["STATE", "TRANSITION", "SCENARIO", "DIRECTION", "TIMING", "CONFIDENCE_CALIBRATION", "ABSTENTION", "COUNTER_EVIDENCE"],
            "persistence": "R5.1 protocol, batch <= 5, failures stay in the denominator",
            "gate_rule": "CAPABILITY_GATE stays CLOSED unless independently sufficient evidence; PREDICTION=UNSUPPORTED or INCONCLUSIVE otherwise",
            "hard_safety": {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF", "BOUNDARY_VIOLATION": 0}}
    reg["registry_hash"] = sha_obj({k: v for k, v in reg.items() if k != "registry_hash"})
    wjson("registry/v1_r6_registry.json", reg)
    # ---- ledger genesis ----
    prev, seq = "0" * 64, 0
    with open(ledger_path, "a", encoding="utf-8", newline="\n") as fh:
        rec = {"seq": 1, "ts_utc": NOW, "event": "registry_frozen", "registry_hash": reg["registry_hash"],
                "frozen_hashes": reg["frozen_hashes"], "previous_hash": prev}
        rec["current_hash"] = sha_obj({k: v for k, v in rec.items() if k != "current_hash"})
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print("ROOT:", ROOT)
    print("registry_hash:", reg["registry_hash"][:16], "| sample n:", len(sample), "| prompt_unchanged_vs_r5:", reg["prompt_unchanged_vs_r5"])
    print("sample:", sample[:6], "...", sample[-3:])
    for k, v in frozen.items():
        print(f"  {k} frozen: {v['baseline_hash'][:16]} ({v['file_count']} files)")


if __name__ == "__main__":
    main()
