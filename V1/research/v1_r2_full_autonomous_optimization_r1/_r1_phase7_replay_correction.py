# -*- coding: utf-8 -*-
"""V1-R2 R1 — PHASE 7 REPLAY CORRECTION (ERRATUM).

The first Phase 7-9 run compared label_series(truncated) [FROZEN labels] against stateful[:T]
[HYSTERESIS labels]. That pair is not supposed to be equal, so REPLAY_PASS=false was an INSTRUMENT
BUG, not a finding. This script recomputes the replay test correctly (frozen vs frozen on the SAME
frozen label function), records an erratum, and corrects the field in the Phase 7-9 report.
Return-free. Read-only on frozen artifacts."""
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
R1 = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_full_autonomous_optimization_r1")
C15 = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_market_reading", "c1_5_target_validation")
M1P = os.path.join(REPO, "research", "v3_alpha_discovery_r1", "xauusd_m1_histdata.parquet")
NOW = datetime.now(timezone.utc).isoformat()
TRUNC = [0.50, 0.65, 0.80]


def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    mod = load_mod("c15", os.path.join(C15, "_c1_5_run.py"))
    m = pd.read_parquet(M1P, columns=["dt_utc", "open", "high", "low", "close"])
    m["dt"] = pd.to_datetime(m["dt_utc"], utc=True)
    m = m.set_index("dt").sort_index()
    m15 = pd.DataFrame({"o": m["open"].resample("15min").first(), "h": m["high"].resample("15min").max(),
                         "l": m["low"].resample("15min").min(), "c": m["close"].resample("15min").last()}).dropna()
    n = len(m15)
    full = [r["MARKET_BEHAVIOR"] for r in mod.label_series(m15, "M15")]
    full_hash = hashlib.sha256("|".join(full).encode()).hexdigest()
    rows = []
    for f in TRUNC:
        T = int(n * f)
        tr = [r["MARKET_BEHAVIOR"] for r in mod.label_series(m15.iloc[:T], "M15")]
        same = sum(1 for a, b in zip(tr, full[:T]) if a == b)
        rows.append({"truncation_bars": T, "compared": T, "identical": same, "differences": T - same, "PASS": same == T})
    pass_all = all(r["PASS"] for r in rows)
    correction = {
        "task": "V1_R2_FULL_AUTONOMOUS_OPTIMIZATION_R1", "phase": "PHASE_7_REPLAY_CORRECTION",
        "ts_utc": NOW, "return_free": True,
        "erratum": {
            "what_was_wrong": "the first Phase 7-9 run compared label_series(truncated) [FROZEN labels] against stateful[:T] [HYSTERESIS labels]",
            "why_invalid": "the frozen label sequence and the hysteresis sequence are different objects by construction; this comparison cannot pass",
            "fix": "recomputed the SAME frozen label function on truncated vs full input and compared frozen-to-frozen",
            "corrected_evidence": "C1 V1_R2_PHASE_C1_SUMMARY.json REPLAY_TEST=PASS and C1.5 audit/REPLAY_AUDIT.json (same frozen label function)"
        },
        "corrected_replay": {"truncations": rows, "REPLAY_PASS": bool(pass_all),
                              "full_label_hash": full_hash, "full_bars": n, "mode": "frozen_vs_frozen"},
        "safety": {"ORDER_SEND": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "LIVE": "OFF",
                    "FROZEN_ARTIFACT_WRITE": 0, "FUTURE_RETURN_USED": "NO", "PNL_USED": "NO"}
    }
    cp = os.path.join(R1, "reports", "V1_R2_R1_PHASE7_REPLAY_CORRECTION.json")
    os.makedirs(os.path.dirname(cp), exist_ok=True)
    with open(cp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(correction, fh, indent=1, ensure_ascii=False)
    # correct the stale field in the Phase 7-9 report
    mp = os.path.join(R1, "reports", "V1_R2_R1_PHASE7_9_DETERMINISM_FORECAST_STRATEGY.json")
    d = json.load(open(mp, encoding="utf-8"))
    d["causal_replay"] = {"status": "CORRECTED", "mode": "frozen_vs_frozen", "truncations": rows,
                           "REPLAY_PASS": bool(pass_all),
                           "erratum": "the previously written truncations/REPLAY_PASS=false compared FROZEN labels against HYSTERESIS labels; see V1_R2_R1_PHASE7_REPLAY_CORRECTION.json"}
    d["erratum_ts_utc"] = NOW
    with open(mp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(d, fh, indent=1, ensure_ascii=False)
    with open(os.path.join(R1, "ledger", "V1_R2_R1_LEDGER.jsonl"), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"ts_utc": NOW, "phase": "PHASE_7_CORRECTION", "report": os.path.relpath(cp, REPO),
                              "REPLAY_PASS": bool(pass_all)}, ensure_ascii=False) + "\n")
    print("REPLAY_PASS:", pass_all)
    print(json.dumps(rows, ensure_ascii=False))


if __name__ == "__main__":
    main()
