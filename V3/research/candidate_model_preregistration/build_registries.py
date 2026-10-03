"""Build registries + hashes for V3-HFT-PREREG-001.

PREREGISTRATION_ONLY / READ_ONLY. Writes only under candidate_model_preregistration/.
Computes: document hashes, the preregistration manifest, model + parameter registries, SHA256SUMS.
No experiment, no training, no MT5.
"""
from __future__ import annotations

import hashlib
import json
import os

H = os.path.dirname(os.path.abspath(__file__))
GEN = "2026-09-22T06:25:00Z"
PREREG_ID = "V3-HFT-PREREG-001"
SNAPSHOT_ID = "V3-SNAP-20260922T025312Z"
SNAPSHOT_SHA = "a036a808d5d924a7a99c5941919971ff00ce9e28c804e8e91860b6ffd7fa61b5"


def sha256(p):
    if not os.path.exists(p):
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def jload(p):
    return json.load(open(p, encoding="utf-8"))


def jdump(p, o):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(o, f, indent=1)
    print("wrote", os.path.relpath(p, H))


MODELS = [
 {"model_id": "LEVEL-0", "level": 0, "name": "Cost-Only Baseline", "role": "BASELINE",
  "inputs": ["decision_timestamp", "bid", "ask", "historical_move_stats", "cost_constants"],
  "outputs": ["cost_to_move", "coverage", "TRADABLE_BY_COST|BLOCKED_BY_COST"],
  "decision_vocabulary": ["REPORT_ONLY"], "directional": False, "trades": False,
  "protocol": "protocol/LEVEL_0_COST_BASELINE.md", "status": "PREREGISTERED",
  "forbidden_inputs": ["CAND-001 signal", "CAND-003 decay", "future markout", "future realised PnL"]},
 {"model_id": "CAND-002", "level": 1, "name": "Spread-State Execution", "role": "SECONDARY",
  "inputs": ["bid", "ask", "mid", "spread_usd", "spread_bp", "spread_change_200t",
              "quote_arrival_1s", "recent_return_1s", "recent_volatility_50t"],
  "outputs": ["TRADEABLE", "NOT_TRADEABLE", "UNKNOWN"],
  "decision_vocabulary": ["TRADEABLE", "NOT_TRADEABLE", "UNKNOWN"], "directional": False, "trades": False,
  "hypothesis": "H002 ECONOMIC_GATE_HYPOTHESIS", "protocol": "protocol/CAND-002_PROTOCOL.md",
  "status": "PREREGISTERED"},
 {"model_id": "CAND-001", "level": 2, "name": "Execution-Aware L1 Markout Gate", "role": "PRIMARY",
  "inputs": ["15 registered PREDICTIVE features (data/DATA_SCHEMA.md)"],
  "outputs": ["expected_gross_edge", "expected_cost", "expected_adverse_selection", "net_edge",
               "uncertainty", "TAKE|WAIT"],
  "decision_vocabulary": ["TAKE", "WAIT"], "directional": True, "trades": True,
  "structure": "EXPECTED_GROSS_EDGE - EXPECTED_EXECUTION_COST - EXPECTED_ADVERSE_SELECTION = NET_EDGE",
  "protocol": "protocol/CAND-001_PROTOCOL.md", "status": "PREREGISTERED"},
 {"model_id": "CAND-003", "level": 3, "name": "Adverse-Selection Conditional Exit", "role": "EXPLORATORY",
  "inputs": ["state at each decision instant", "position", "elapsed time", "exit cost estimate"],
  "outputs": ["EXPECTED_REMAINING_EDGE", "HOLD|EXIT", "failure class"],
  "decision_vocabulary": ["HOLD", "EXIT"], "directional": False, "trades": False,
  "structure": "EXIT iff E[remaining_edge] - EXIT_COST - MARGIN < 0 ; E(t)=E0*exp(-lambda t) [ASSUMPTION]",
  "taxonomy": ["ENTRY_WRONG", "EDGE_DECAY", "ADVERSE_SELECTION", "COST_EROSION", "UNCLASSIFIED"],
  "protocol": "protocol/CAND-003_PROTOCOL.md", "status": "PREREGISTERED"},
]

PARAMS = [
 # parameter_id, model_id, name, value, unit, source, category
 ("P-001", "ALL", "PRIMARY_HORIZONS", [5000, 10000, 30000, 60000, 300000], "ms", "labels/HORIZON_POLICY.md", "FIXED"),
 ("P-002", "ALL", "REFERENCE_ONLY_HORIZONS", [1000, 2000], "ms", "labels/HORIZON_POLICY.md", "FIXED"),
 ("P-003", "ALL", "FORBIDDEN_HORIZONS", [50, 200], "ms", "labels/HORIZON_POLICY.md", "FIXED"),
 ("P-004", "ALL", "SAMPLE_GRID", 1000, "ms", "data/DATA_SCHEMA.md", "FIXED"),
 ("P-005", "ALL", "SAMPLE_FRESHNESS", 5000, "ms", "data/DATA_SCHEMA.md", "FIXED"),
 ("P-006", "ALL", "PURGE", 300000, "ms", "oos/PURGE_EMBARGO_POLICY.md", "FIXED"),
 ("P-007", "ALL", "EMBARGO", 300000, "ms", "oos/PURGE_EMBARGO_POLICY.md", "FIXED"),
 ("P-008", "ALL", "MIN_RAW_N", 500, "observations", "statistics/POWER_PLAN.md", "FIXED"),
 ("P-009", "ALL", "MIN_EFFECTIVE_N", {"5000": 274, "10000": 494, "30000": 1439, "60000": 2679, "300000": 13069},
   "effective observations", "statistics/POWER_PLAN.md", "FIXED"),
 ("P-010", "ALL", "COST_TIERS_USD", [0.40, 0.50, 0.60, 0.80, 1.00], "USD/RT", "cost/COST_POLICY.md", "FIXED"),
 ("P-011", "ALL", "COST_ANCHOR_BP", 0.914, "bp", "cost/COST_POLICY.md", "FIXED"),
 ("P-012", "ALL", "FDR_METHOD_AND_Q", "BH q=0.05 (m=20)", "-", "statistics/FDR_PLAN.md", "FIXED"),
 ("P-013", "ALL", "BOOTSTRAP", "moving block, 2000 resamples, block=max(50,10*rho), seed 20260922",
   "-", "statistics/BOOTSTRAP_PLAN.md", "FIXED"),
 ("P-014", "ALL", "MIN_MARKOUT_HORIZON_MS", 500, "ms", "labels/LABEL_DEFINITIONS.md", "FIXED"),
 ("P-015", "ALL", "DECISION_MARGIN_RULE", "95% block-bootstrap CI half-width of expected net edge",
   "bp", "protocol/CAND-001_PROTOCOL.md", "ESTIMATED_ON_TRAIN"),
 ("P-016", "CAND-002", "STATE_FORM", "CONTINUOUS (COST_MULTIPLE)", "-", "protocol/CAND-002_PROTOCOL.md", "FIXED"),
 ("P-017", "CAND-002", "COST_MULTIPLE_THRESHOLD", 1.0, "ratio", "cost identity (NOT data-derived)",
   "FIXED"),
 ("P-018", "CAND-002", "EXPLORATORY_THRESHOLD", 0.5, "ratio", "protocol/CAND-002_PROTOCOL.md", "FIXED"),
 ("P-019", "CAND-002", "WINDOW_W_TICKS", 200, "ticks", "protocol/CAND-002_PROTOCOL.md", "FIXED"),
 ("P-020", "CAND-002", "WINDOW_WV_TICKS", 50, "ticks", "protocol/CAND-002_PROTOCOL.md", "FIXED"),
 ("P-021", "CAND-002", "EXPECTED_MOVE_ESTIMATOR", "median |move| on TRAIN, same horizon + session bucket",
   "-", "protocol/CAND-002_PROTOCOL.md", "ESTIMATED_ON_TRAIN"),
 ("P-022", "CAND-001", "MODEL_CLASS", ["ridge", "decision_tree(depth<=3)"], "-",
   "protocol/CAND-001_PROTOCOL.md", "FIXED"),
 ("P-023", "CAND-001", "RIDGE_ALPHA", 1.0, "-", "protocol/CAND-001_PROTOCOL.md (fixed default, not searched)",
   "FIXED"),
 ("P-024", "CAND-001", "TREE_MAX_DEPTH", 3, "-", "protocol/CAND-001_PROTOCOL.md", "FIXED"),
 ("P-025", "CAND-001", "ADVERSE_SELECTION_ESTIMATOR", "lagged PIT entry-cohort drift estimate",
   "-", "protocol/CAND-001_PROTOCOL.md", "ESTIMATED_ON_TRAIN"),
 ("P-026", "CAND-003", "DECAY_FORM", "exponential (MODEL_ASSUMPTION)", "-",
   "protocol/CAND-003_PROTOCOL.md", "FIXED"),
 ("P-027", "CAND-003", "LAMBDA", "log-linear OLS on the TRAIN markout curve", "1/ms",
   "protocol/CAND-003_PROTOCOL.md", "ESTIMATED_ON_TRAIN"),
 ("P-028", "CAND-003", "E0", "TRAIN markout curve intercept", "bp", "protocol/CAND-003_PROTOCOL.md",
   "ESTIMATED_ON_TRAIN"),
 ("P-029", "CAND-003", "EXIT_COST_MODEL", "one further spread crossing + commission", "bp",
   "cost/COST_POLICY.md", "FIXED"),
 ("P-030", "ALL", "ESTIMATE_ON_TEST", False, "-", "oos/OOS_POLICY.md", "NOT_ALLOWED_TO_ESTIMATE_ON_TEST"),
]

DOCS = ["README.md", "protocol/LEVEL_0_COST_BASELINE.md", "protocol/CAND-001_PROTOCOL.md",
        "protocol/CAND-002_PROTOCOL.md", "protocol/CAND-003_PROTOCOL.md",
        "data/DATA_SCHEMA.md", "data/SNAPSHOT_POLICY.md", "data/TEST_BOUNDARY.md",
        "labels/LABEL_DEFINITIONS.md", "labels/HORIZON_POLICY.md", "cost/COST_POLICY.md",
        "statistics/STATISTICAL_PLAN.md", "statistics/POWER_PLAN.md", "statistics/FDR_PLAN.md",
        "statistics/BOOTSTRAP_PLAN.md", "oos/OOS_POLICY.md", "oos/PURGE_EMBARGO_POLICY.md",
        "safety/LOOKAHEAD_POLICY.md", "safety/INFORMATION_TIMELINE.md",
        "comparison/MODEL_LADDER.md", "comparison/BASELINE_POLICY.md",
        "final_preregistration_report.md"]


def main():
    doc_hashes = {d: sha256(os.path.join(H, d)) for d in DOCS}

    jdump(os.path.join(H, "registries", "model_registry.json"),
          {"schema": "v3_prereg_model_registry/1", "preregistration_id": PREREG_ID, "generated_utc": GEN,
           "status_note": "PREREGISTERED only. No model has been trained, run or validated.",
           "ladder": ["LEVEL-0", "CAND-002", "CAND-001", "CAND-003"],
           "promotion_ladder": ["CANDIDATE", "EXPERIMENTAL", "OOS_SUPPORTED", "EXECUTION_VALIDATED"],
           "combination_tuning_round1": "FORBIDDEN", "models": MODELS})

    jdump(os.path.join(H, "registries", "parameter_registry.json"),
          {"schema": "v3_parameter_registry/1", "preregistration_id": PREREG_ID, "generated_utc": GEN,
           "rule": "any TBD must be resolved before the task ends; unresolvable => MODEL_NOT_READY_FOR_EXPERIMENT",
           "unresolved_tbd_count": 0,
           "categories": ["FIXED", "ESTIMATED_ON_TRAIN", "ESTIMATED_ON_DEVELOPMENT",
                           "NOT_ALLOWED_TO_ESTIMATE_ON_TEST"],
           "parameters": [{"parameter_id": i, "model_id": m, "parameter_name": n, "value": v, "unit": u,
                            "source": s, "category": c, "frozen_before_data_view": True}
                           for i, m, n, v, u, s, c in PARAMS]})

    model_spec_hash = sha_text("".join(doc_hashes[d] for d in
                                        ["protocol/LEVEL_0_COST_BASELINE.md", "protocol/CAND-001_PROTOCOL.md",
                                         "protocol/CAND-002_PROTOCOL.md", "protocol/CAND-003_PROTOCOL.md"]))
    manifest = {
      "schema": "v3_preregistration_manifest/1",
      "preregistration_id": PREREG_ID,
      "task": "V3-HFT-CANDIDATE-MODEL-PREREGISTRATION-001",
      "generated_utc": GEN,
      "mode": "PREREGISTRATION_ONLY / READ_ONLY",
      "data_snapshot_id": SNAPSHOT_ID,
      "data_snapshot_hash": SNAPSHOT_SHA,
      "test_boundary": {"rule": "first 10 usable sessions strictly after 2026-09-22T06:20:00Z",
                         "status": "RULE_LOCKED", "TEST_LOCKED_HASH": "PENDING_NOT_YET_COLLECTED",
                         "contaminated_window": "2026-09-07..2026-09-21 (DEMOTED to DEVELOPMENT_CONTAMINATED)"},
      "feature_schema_hash": doc_hashes["data/DATA_SCHEMA.md"],
      "label_schema_hash": doc_hashes["labels/LABEL_DEFINITIONS.md"],
      "cost_model_hash": doc_hashes["cost/COST_POLICY.md"],
      "cost_model_id": "CALIBRATION_20RT_20260921",
      "model_spec_hash": model_spec_hash,
      "statistical_plan_hash": doc_hashes["statistics/STATISTICAL_PLAN.md"],
      "oos_policy_hash": doc_hashes["oos/OOS_POLICY.md"],
      "lookahead_policy_hash": doc_hashes["safety/LOOKAHEAD_POLICY.md"],
      "horizon_policy_hash": doc_hashes["labels/HORIZON_POLICY.md"],
      "power_plan_hash": doc_hashes["statistics/POWER_PLAN.md"],
      "fdr_plan_hash": doc_hashes["statistics/FDR_PLAN.md"],
      "bootstrap_plan_hash": doc_hashes["statistics/BOOTSTRAP_PLAN.md"],
      "purge_embargo_hash": doc_hashes["oos/PURGE_EMBARGO_POLICY.md"],
      "baseline_policy_hash": doc_hashes["comparison/BASELINE_POLICY.md"],
      "model_ladder_hash": doc_hashes["comparison/MODEL_LADDER.md"],
      "information_timeline_hash": doc_hashes["safety/INFORMATION_TIMELINE.md"],
      "snapshot_policy_hash": doc_hashes["data/SNAPSHOT_POLICY.md"],
      "document_hashes": doc_hashes,
      "open_items": ["TEST_LOCKED_HASH pending future data collection (rule frozen)"],
      "safety_baseline": {"ORDER_SEND": 0, "CALIBRATION": 0, "FORWARD": "NO", "LIVE": "NO",
                           "EXPANSION": "LOCKED", "V1": "UNTOUCHED", "V2": "UNTOUCHED",
                           "OPENCLAW": "UNTOUCHED", "MT5_INSTANCE_COUNT": 3, "MT5_ISOLATION": "PASS",
                           "MODEL_TRAINING": "OFF", "ALPHA_SEARCH": "OFF", "FEATURE_MINING": "OFF",
                           "DATA_SNAPSHOT": "IMMUTABLE", "COST_MODEL": "CANONICAL"},
    }
    canonical = json.dumps(manifest, indent=1, sort_keys=True)
    manifest["PREREGISTRATION_SHA256"] = sha_text(canonical)
    jdump(os.path.join(H, "registries", "preregistration_manifest.json"), manifest)

    # SHA256SUMS over everything (excluding SHA256SUMS itself)
    files = []
    for dp, _, fn in os.walk(H):
        if "__pycache__" in dp:
            continue
        for f in fn:
            if f in ("SHA256SUMS",) or f.endswith(".pyc"):
                continue
            files.append(os.path.join(dp, f))
    files.sort()
    with open(os.path.join(H, "SHA256SUMS"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(f"{sha256(p)}  {os.path.relpath(p, H).replace(chr(92), '/')}" for p in files) + "\n")
    print("wrote SHA256SUMS x", len(files))
    print(json.dumps({"PREREGISTRATION_SHA256": manifest["PREREGISTRATION_SHA256"],
                       "model_spec_hash": model_spec_hash,
                       "params": len(PARAMS), "unresolved_tbd": 0}, indent=1))


if __name__ == "__main__":
    main()
