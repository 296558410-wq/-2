# -*- coding: utf-8 -*-
"""V1-R2 FULL AUTONOMOUS OPTIMIZATION — SCAFFOLD (§58, §92, §93, §37, §23, §8, §77).

Creates the canonical directory tree, the frozen protocol registry (with hashes), the sha256-chained
append-only ledger, and files the Phase-1 diagnostic artifacts into diagnostics/.
Read-only on all frozen artifacts. Writes ONLY under v1_r2_full_optimization/."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

REPO = r"C:\AIQuant"
ROOT = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_full_optimization")
R1 = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_full_autonomous_optimization_r1")
NOW = datetime.now(timezone.utc).isoformat()
DIRS = ["registry", "diagnostics", "targets", "ontology", "events", "states", "transitions", "forecast",
        "blind_validation", "ablation", "replay", "strategy_mapping", "audit", "ledger", "reports", "tests"]


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def wjson(p, o):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, default=str)
    return p


# ---------------- sha256-chained append-only ledger (§93) ----------------
LEDGER = os.path.join(ROOT, "ledger", "v1_r2_full_optimization_ledger.jsonl")
GENESIS = "0" * 64


def ledger_last_hash():
    if not os.path.exists(LEDGER):
        return GENESIS, 0
    last = None
    seq = 0
    with open(LEDGER, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                last = json.loads(line)
                seq += 1
    return (last["this_hash"] if last else GENESIS), seq


def ledger_append(phase, event, payload=None, extra=None):
    prev, seq = ledger_last_hash()
    entry = {"seq": seq + 1, "ts_utc": NOW, "phase": phase, "event": event,
              "payload_hash": sha_obj(payload or {}), "prev_hash": prev}
    if extra:
        entry.update(extra)
    entry["this_hash"] = sha_obj({k: v for k, v in entry.items() if k != "this_hash"})
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def main():
    for d in DIRS:
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)

    # ---- §58 protocol registry (frozen before analysis) ----
    protocol = {
        "task": "V1_R2_FULL_AUTONOMOUS_OPTIMIZATION",
        "protocol_version": "v1r2-full-r1",
        "frozen": True, "frozen_before_analysis": True, "frozen_at_utc": NOW,
        "baseline": {"c1_git_head": "0f3d5d3c88a701a80b42d520b2b510f1aa07ccf3",
                      "c1_summary_hash": sha_file(os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_market_reading", "reports", "V1_R2_MARKET_READING_ARCHITECTURE_R1_SUMMARY.json")),
                      "c15_summary_hash": sha_file(os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_market_reading", "c1_5_target_validation", "reports", "V1_R2_PHASE_C1_5_SUMMARY.json")),
                      "c1_ontology_hash": "8436866dfe71030ba7be036b2d73904ed2f817aa52673a5e27d583e931c354d8",
                      "c1_label_mapping_hash": "21e0f842edc14f6feee8cade3d6d919f879b6d36a58ffb056437b382428d7cf4",
                      "c15_target_registry_hash": "58022bdb5572d33a98d93af914fe7771378fc164c5593d0759c9bbcdbd475d88"},
        "must_preserve": {"C1_STATE_RECOGNITION": "UNSUPPORTED", "C1_DIRECTION_ACCURACY": 0.69,
                           "C1_DIRECTION_MAJORITY": 0.79, "C15_TARGET_VALIDITY": "TARGET_UNCERTAIN",
                           "C15_C2_GATE": "C2_BLOCKED", "C15_PERSISTENCE_M15": 0.1447,
                           "C15_STATE_CHURN_M15": 0.6473, "C15_DURATION_MEDIAN": 1,
                           "C15_BOUNDARY_STABILITY": "UNSUPPORTED", "C15_TECHNICAL_VALIDATION": "FAIL",
                           "note": "§3/§4: these must stay reported as-is; C2_BLOCKED must not be lifted by editing history"},
        "practical_effect_floor": {"log_loss_bits": 0.01, "auc": 0.55, "accuracy_abs": 0.02, "note": "§37 pre-registered"},
        "abstention_coverage_grid": [1.0, 0.9, 0.8, 0.7, 0.6],   # §23
        "max_structural_corrections_per_question": 3,             # §8 / §105
        "max_forecast_target_classes": 4,                          # §77
        "splits": ["time", "day", "cluster"],                      # §30
        "purge_bars": 480, "embargo_bars": 1,
        "shuffle_nulls": ["label_shuffle", "time_shuffle", "sequence_shuffle"],  # §34
        "baselines": ["majority", "persistence", "previous_state", "previous_event", "random", "simple_transition"],  # §65
        "forecast_targets_ranked": ["STATE", "EVENT", "STATE_TRANSITION", "EVENT_SEQUENCE"],  # §10/§77
        "auto_failure_branch": ["STATE", "EVENT", "EVENT_SEQUENCE", "TRANSITION_PRESSURE"],   # §76
        "data_quality_levels": ["DIRECT", "DERIVED", "PROXY", "UNKNOWN"],  # §46
        "no_history_expansion": True,  # §84
        "no_data_purchase": True,      # §83
        "hard_safety": {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
                         "V2_WRITE": 0, "V3_WRITE": 0, "V1_EXECUTION_MODIFIED": 0, "V1_RISK_MODIFIED": 0,
                         "V1_ORDER_LOGIC_MODIFIED": 0, "BOUNDARY_VIOLATION": 0},
        "verdict_vocabulary": ["PREDICTION_CAPABILITY_SUPPORTED", "PARTIAL_PREDICTION_CAPABILITY_SUPPORTED",
                                "MARKET_READING_SUPPORTED_BUT_FORECAST_UNSUPPORTED", "FORECAST_TARGET_UNSUPPORTED",
                                "DATA_LIMITED"],  # §97
        "directory_tree": DIRS,  # §92
    }
    protocol["registry_hash"] = sha_obj(protocol)
    protocol["architecture_hash"] = sha_obj({"dirs": DIRS, "stages": ["diagnostic", "state_vs_event", "kline_context",
                                                                       "state_lifecycle", "event_layer", "transition_warning",
                                                                       "forecast_decomposition", "mtf", "mechanism", "counter_evidence",
                                                                       "blind", "ablation", "replay", "strategy_mapping", "final"]})
    protocol["context_hash"] = sha_obj({"data": ["xauusd_m1_histdata.parquet", "live_fxtm/ticks_*.parquet"],
                                         "tf": ["M5", "M15", "H1", "H4"], "no_expansion": True})
    wjson(os.path.join(ROOT, "registry", "registry.json"), protocol)

    # ---- §93 ledger genesis + scaffold event ----
    ledger_append("SCAFFOLD", "ledger_genesis", {"note": "canonical ledger created"},
                  extra={"registry_hash": protocol["registry_hash"]})
    ledger_append("SCAFFOLD", "directories_created", {"dirs": DIRS})

    # ---- file the Phase-1 diagnostics into diagnostics/ (copy, keep source intact) ----
    mapping = {
        "V1_R2_R1_PHASE1_DIAGNOSIS_SHORT.json": os.path.join(R1, "reports", "V1_R2_R1_PHASE1_DIAGNOSIS_SHORT.json"),
        "V1_R2_R1_PHASE1_DIAGNOSIS_LONG.json": os.path.join(R1, "reports", "V1_R2_R1_PHASE1_DIAGNOSIS_LONG.json"),
        "v1_r2_r1_phase1_preregistration.json": os.path.join(R1, "registry", "v1_r2_r1_phase1_preregistration.json"),
    }
    filed = {}
    for dst, src in mapping.items():
        if os.path.exists(src):
            d = os.path.join(ROOT, "diagnostics", dst)
            shutil.copyfile(src, d)
            filed[dst] = sha_file(d)
    # §9 A–H hypothesis mapping
    ah = {
        "A_ontology_too_fine": "PARTIAL", "B_behavior_mistaken_for_state": "CONFIRMED (§9-B: the frozen MARKET_BEHAVIOR is a per-bar classifier, not a lifecycle state)",
        "C_transition_too_sensitive": "CONFIRMED (no dwell/hysteresis)", "D_threshold_boundary_churn": "WEAK (noise 0.01*ATR -> 0.9418 agreement)",
        "E_horizon_mismatch": "REJECTED (churn ~0.61-0.67 at M5/M15/H1)", "F_market_genuine_high_freq_switch": "REJECTED (surrogate churn ~= observed)",
        "G_mtf_fusion_label_jitter": "NOT_THE_CAUSE (single-TF labeler)", "H_lifecycle_design": "CONFIRMED (dominant: k=2 -> churn 0.647->0.151)"}
    idx = {"task": "V1_R2_FULL_AUTONOMOUS_OPTIMIZATION", "stage": "DIAGNOSTIC", "ts_utc": NOW,
            "question": "Why is State duration = 1 bar? (§9)", "files": filed, "AH_mapping": ah,
            "root_cause": "the frozen labeler is memoryless per-bar; no lifecycle constraint (H) and the labeler's own randomness (F-rejected as market property) drive 1-bar duration"}
    wjson(os.path.join(ROOT, "diagnostics", "DIAGNOSTIC_INDEX.json"), idx)
    ledger_append("DIAGNOSTIC", "diagnostics_filed", {"files": list(filed.keys()), "root_cause": idx["root_cause"]})

    print("ROOT:", ROOT)
    print("registry_hash:", protocol["registry_hash"][:16], "| architecture_hash:", protocol["architecture_hash"][:16])
    print("ledger entries:", ledger_last_hash()[1])


if __name__ == "__main__":
    main()
