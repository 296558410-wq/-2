# -*- coding: utf-8 -*-
"""V1-R2 MARKET READING ARCHITECTURE R1 — FREEZE step (task §50: DEFINE -> FREEZE -> RUN).

Emits the ontology + registry ONLY, computes their hashes, and stops.
Nothing is measured here; no market data is read. GIT_COMMIT=NONE."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

ROOT = r"C:\AIQuant\research\hermes\trader_v1\v1_r2_market_reading"
ONT = os.path.join(ROOT, "ontology")
REGD = os.path.join(ROOT, "registry")
NOW = datetime.now(timezone.utc).isoformat()
ONTOLOGY_VERSION = "v1r2-mr-ontology-r1"
REGISTRY_VERSION = "v1r2-mr-registry-r1"


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def w(p, o):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, default=str)


# ------------------------------------------------------------------ L1 candle ontology
CANDLE_THRESHOLDS = {
    "DOJI_BODY_MAX_RANGE": 0.10, "MARUBOZU_BODY_MIN_RANGE": 0.95, "LONG_BODY_MIN_RANGE": 0.70,
    "LONG_WICK_WICK_OVER_BODY": 2.0, "HAMMER_WICK_OVER_BODY": 2.0, "HAMMER_OPPOSITE_WICK_MAX_BODY": 0.5,
    "SPINNING_TOP_BODY_MAX_RANGE": 0.30, "ENGULF_MIN_PREV_BODY_RANGE": 0.10,
    "STAR_MID_RETRACE": 0.50, "CONTEXT_TREND_BARS": 20,
}
CANDLE_ONTOLOGY = {
    "layer": "L1_MARKET_PERCEPTION", "name": "JAPANESE_CANDLESTICK", "version": ONTOLOGY_VERSION,
    "principle": "a candle pattern emits a CANDLE_EVENT (an OBSERVATION), never a TRADE_SIGNAL (task §4/§8)",
    "thresholds_preregistered": CANDLE_THRESHOLDS,
    "geometry_fields": ["open", "high", "low", "close", "body_size", "body_direction", "upper_wick", "lower_wick",
                         "wick_body_ratio", "close_location", "range", "true_range", "body_to_range"],
    "single_bar_events": {
        "DOJI": {"rule": "body <= DOJI_BODY_MAX_RANGE * range"},
        "MARUBOZU": {"rule": "body >= MARUBOZU_BODY_MIN_RANGE * range"},
        "LONG_BODY": {"rule": "body >= LONG_BODY_MIN_RANGE * range"},
        "LONG_WICK": {"rule": "max(upper_wick, lower_wick) >= LONG_WICK_WICK_OVER_BODY * body"},
        "SPINNING_TOP": {"rule": "body <= SPINNING_TOP_BODY_MAX_RANGE * range and upper_wick > body and lower_wick > body"},
        "HAMMER_GEOMETRY": {"rule": "lower_wick >= HAMMER_WICK_OVER_BODY*body and upper_wick <= HAMMER_OPPOSITE_WICK_MAX_BODY*body and close_location >= 0.66"},
        "INVERTED_HAMMER_GEOMETRY": {"rule": "upper_wick >= HAMMER_WICK_OVER_BODY*body and lower_wick <= HAMMER_OPPOSITE_WICK_MAX_BODY*body and close_location <= 0.34"},
    },
    "two_bar_events": {
        "BULLISH_ENGULFING": {"rule": "prev bearish and cur bullish and cur body engulfs prev body"},
        "BEARISH_ENGULFING": {"rule": "prev bullish and cur bearish and cur body engulfs prev body"},
        "INSIDE_BAR": {"rule": "high <= prev_high and low >= prev_low"},
        "OUTSIDE_BAR": {"rule": "high > prev_high and low < prev_low"},
        "HARAMI": {"rule": "inside bar and prev body contains cur body and prev body >= ENGULF_MIN_PREV_BODY_RANGE*prev_range"},
    },
    "three_bar_events": {
        "MORNING_STAR": {"rule": "bar1 bearish long, bar2 small body, bar3 bullish closing above midpoint of bar1 body"},
        "EVENING_STAR": {"rule": "bar1 bullish long, bar2 small body, bar3 bearish closing below midpoint of bar1 body"},
    },
    "context_labels_require_context": {
        "SHOOTING_STAR": {"geometry": "INVERTED_HAMMER_GEOMETRY", "required_context": "ADVANCE_CONTEXT"},
        "HANGING_MAN": {"geometry": "HAMMER_GEOMETRY", "required_context": "ADVANCE_CONTEXT"},
        "HAMMER": {"geometry": "HAMMER_GEOMETRY", "required_context": "DECLINE_CONTEXT"},
    },
    "REUSE_OF_GEOMETRY_FORBIDDEN_AS_SIGNAL": True,
    "sequence_events": ["CONSECUTIVE_UP", "CONSECUTIVE_DOWN", "BODY_EXPANDING", "BODY_CONTRACTING", "RANGE_EXPANDING",
                          "RANGE_CONTRACTING", "OVERLAP_INCREASING", "OVERLAP_DECREASING", "HH_SERIES", "HL_SERIES",
                          "LH_SERIES", "LL_SERIES"],
    "sequence_window_pre_registered": 5,
}

# ------------------------------------------------------------------ L2 behaviour ontology
BEHAVIOUR_ONTOLOGY = {
    "layer": "L2_MARKET_READING", "version": ONTOLOGY_VERSION,
    "principle": "these describe WHAT the market is doing; they never emit BUY/SELL (task §9/§17)",
    "behaviours": ["TREND", "RANGE", "COMPRESSION", "EXPANSION", "ACCELERATION", "DECELERATION", "EXHAUSTION",
                    "REJECTION", "ACCEPTANCE", "ROTATION", "BREAKOUT_ATTEMPT", "BREAKOUT_CONFIRMATION",
                    "BREAKOUT_FAILURE", "RETEST", "REVERSAL_ATTEMPT"],
    "acceptance_rejection": {
        "definition": "ACCEPTANCE = price moves beyond a level, closes beyond it, and does NOT promptly return; "
                       "REJECTION = price moves beyond a level and promptly returns into the prior range",
        "directions": ["UPWARD_ACCEPTANCE", "UPWARD_REJECTION", "DOWNWARD_ACCEPTANCE", "DOWNWARD_REJECTION"],
        "evidence_chain_required": True, "horizon_bars_pre_registered": [1, 2, 3, 5, 8],
        "not_a_direction_call": True,
    },
    "momentum_as_behaviour": {"states": ["ACCELERATING", "NORMAL", "DECELERATING", "EXHAUSTING", "TRANSITION"],
                                "forbidden_mapping": "ACCELERATING -> BUY is forbidden (task §17)"},
    "defense_strength": {
        "name": "SUPPORT_DEFENSE_STRENGTH / RESISTANCE_DEFENSE_STRENGTH",
        "inputs": ["touch_count", "rebound_amplitude", "rebound_speed_bars", "rebound_duration_bars", "retrace_depth",
                    "candle_rejection_degree", "close_position", "momentum_change", "volatility_change"],
        "output": "WEAKENING / STABLE / STRENGTHENING", "observational_only": True, "not_a_signal": True,
        "forbidden": "touch_count >= X = break is forbidden (task §12)",
    },
    "unknown_taxonomy": ["INSUFFICIENT_DATA", "CONFLICTING_EVIDENCE", "AMBIGUOUS_STATE", "UNOBSERVABLE_PREREQUISITE",
                           "NO_DEFINED_STATE", "LOW_CONFIDENCE"],
}

# ------------------------------------------------------------------ price structure ontology
PRICE_STRUCTURE_ONTOLOGY = {
    "layer": "L2_MARKET_READING", "version": ONTOLOGY_VERSION,
    "note": "REWORKED from the old state machine; NOT inherited as-is (task §10)",
    "level_lifecycle": ["UNTESTED", "APPROACH", "FIRST_TEST", "REPEATED_TEST", "BREAK_ATTEMPT", "ACCEPTANCE",
                          "REJECTION", "BREAK_CONFIRMED", "FAILED_BREAK", "RETEST", "RESOLVED"],
    "touch_classes": ["FIRST_TOUCH", "REPEATED_TOUCH", "DEEP_TEST", "SHALLOW_TEST", "REJECTION_AFTER_TOUCH",
                        "ACCEPTANCE_AFTER_TOUCH"],
    "forbidden": "touch_count += 1 as the whole model (task §11)",
    "information_lineage": {"PRICE_STRUCTURE": ["LEVEL", "TOUCH", "BREAK", "PENETRATION", "FAILED_EVENT"],
                              "raw_source": "TICK_BID -> OHLC -> level geometry"},
    "penetration_status": "STATUS_UNRESOLVED (B-R11: state justification INCONCLUSIVE, threshold justification INCONCLUSIVE) "
                            "-> retained as an OBSERVATION, not promoted",
    "break_lifecycle": ["BREAK_ATTEMPT", "BREAK_ACCEPTANCE", "BREAK_CONFIRMATION", "BREAK_FAILURE", "RECLAIM", "RETEST"],
    "break_forbidden": "close > level == breakout is forbidden (task §15)",
    "carried_dependency_findings": {"LEVEL_TOUCH_BREAK": "DERIVED (one PRICE_STRUCTURE axis)",
                                     "COUNTER_BREAK_RISK": "DERIVED (restates BREAK)",
                                     "COUNTER_DECELERATION": "DERIVED (restates MOMENTUM)"},
}

# ------------------------------------------------------------------ L3 mechanism ontology
MECHANISM_DEFS = {
    "TREND_CONTINUATION": {"support": ["regime TREND", "momentum ACCELERATING/NORMAL", "state persistence"],
                            "counter": ["momentum DECELERATING", "touch EXHAUSTION_*"],
                            "invalidation": "regime leaves TREND or momentum turns EXHAUSTING with counter evidence"},
    "BREAKOUT_ACCEPTANCE": {"support": ["close beyond level", "no prompt return", "momentum not DECELERATING"],
                             "counter": ["rising opposing wick", "prompt return"],
                             "invalidation": "close returns into the prior range"},
    "BREAKOUT_FAILURE": {"support": ["break attempt then close back inside", "opposing wick rejection"],
                          "counter": ["sustained close beyond", "momentum accelerating with the break"],
                          "invalidation": "price re-accepts beyond the level"},
    "MEAN_REVERSION": {"support": ["range regime", "touch at a boundary", "momentum decelerating"],
                        "counter": ["regime expansion", "acceptance beyond the boundary"],
                        "invalidation": "acceptance beyond the boundary"},
    "EXHAUSTION": {"support": ["repeated touches", "decreasing rebound amplitude", "decelerating momentum"],
                    "counter": ["fresh acceleration", "break confirmation"],
                    "invalidation": "break confirmation or momentum re-acceleration"},
    "LIQUIDITY_WITHDRAWAL": {"support": ["spread widening proxy"], "counter": ["spread stable/below median"],
                              "invalidation": "spread back to median while structure holds",
                              "evidence_level": "PROXY"},
    "ABSORPTION": {"support": ["efficiency decline with activity rise (PROXY_BAR)"], "counter": ["efficiency rising"],
                    "invalidation": "efficiency and activity both fall", "evidence_level": "PROXY"},
    "ROTATION": {"support": ["range regime", "alternating boundary tests"], "counter": ["one-sided acceptance"],
                  "invalidation": "acceptance outside the range"},
    "ACCUMULATION_PROXY": {"support": ["range after decline", "absorption proxy present"], "counter": ["new lows with acceleration"],
                            "invalidation": "decisive breakdown", "evidence_level": "PROXY"},
    "DISTRIBUTION_PROXY": {"support": ["range after advance", "absorption proxy among resistance tests"],
                            "counter": ["new highs with acceleration"], "invalidation": "decisive breakout", "evidence_level": "PROXY"},
}
MECHANISM_ONTOLOGY = {
    "layer": "L3_MARKET_MECHANISM", "version": ONTOLOGY_VERSION,
    "principle": "mechanisms are HYPOTHESES, not facts (task §19); each carries SUPPORTING_EVIDENCE, COUNTER_EVIDENCE and INVALIDATION_CONDITION (task §20)",
    "mechanisms": MECHANISM_DEFS,
    "competition": {"multiple_hypotheses_allowed": True, "first_match_wins": False,
                     "output_scale": ["DOMINANT", "SECONDARY", "UNCERTAIN"],
                     "probabilities_forbidden_until_calibrated": True, "calibration_status": "NO_PROBABILITY_CALIBRATION -> categorical only"},
    "evidence_hierarchy": ["DIRECT", "DERIVED", "PROXY", "UNKNOWN"],
    "evidence_record_fields": ["source", "calculation", "timestamp", "context"],
    "evidence_upgrade_forbidden": True,
    "circularity_guard": "a mechanism may not use its own output as supporting evidence",
}

# ------------------------------------------------------------------ L4 state + forecast ontology
STATE_ONTOLOGY = {
    "layer": "L4_MARKET_STATE", "version": ONTOLOGY_VERSION,
    "STATE_VECTOR": ["REGIME", "TREND", "MOMENTUM", "PRICE_STRUCTURE", "VOLATILITY", "CANDLE_STRUCTURE",
                       "MARKET_BEHAVIOR", "MECHANISM", "CONFIDENCE"],
    "single_label_forbidden": True,
    "unknown_separation": ["INSUFFICIENT_DATA", "CONFLICTING_EVIDENCE", "AMBIGUOUS_STATE", "UNOBSERVABLE_PREREQUISITE",
                             "NO_DEFINED_STATE", "LOW_CONFIDENCE"],
    "unknown_black_hole_forbidden": True,
    "transition": {"model": "CURRENT_STATE -> TRANSITION -> NEXT_STATE", "label_only_on_future_state": True,
                    "future_returns_forbidden": True},
}
FORECAST_ONTOLOGY = {
    "layer": "L4_MARKET_FORECAST", "version": ONTOLOGY_VERSION,
    "predict_first": "NEXT_MARKET_STATE (not BUY/SELL) (task §27)",
    "fields": ["NEXT_STATE", "FORECAST_HORIZON", "DIRECTION", "CONFIDENCE", "INVALIDATION"],
    "horizons": ["M5", "M15", "H1", "H4"],
    "confidence_scale": ["HIGH", "MEDIUM", "LOW", "UNCERTAIN"],
    "invalidation_is_first_class": True,
    "evaluation_stage1_only": ["STATE_PREDICTION", "TRANSITION_PREDICTION", "DIRECTION", "TIMING"],
    "evaluation_forbidden_stage1": ["PnL", "Sharpe", "Profit Factor", "Win Rate"],
    "prediction_journal": {"file": "ledger/v1_r2_market_reading_ledger.jsonl",
                            "fields": ["timestamp", "context_hash", "state_vector", "mechanism_hypotheses",
                                        "supporting_evidence", "counter_evidence", "forecast", "horizon", "confidence",
                                        "invalidation", "data_quality", "registry_hash"],
                            "outcome_field": "OBSERVED_OUTCOME", "outcome_after_prediction_only": True},
}
MARKET_READING_ONTOLOGY = {
    "layer": "L1..L4", "version": ONTOLOGY_VERSION, "task": "V1_R2_MARKET_READING_ARCHITECTURE_R1",
    "pipeline": ["MARKET_PERCEPTION", "MARKET_READING", "MARKET_BEHAVIOR", "MARKET_MECHANISM", "MARKET_STATE",
                  "MARKET_TRANSITION", "MARKET_FORECAST", "STRATEGY_SELECTION", "TRADING"],
    "frozen_principles": ["market decides the trading method, never the reverse",
                           "a candle is one language of the market, not a trade signal",
                           "structure/momentum/volatility/absorption are one vocabulary, not isolated features",
                           "a forecast must carry evidence, counter-evidence and invalidation",
                           "trading is the last layer and must not pollute market reading"],
    "layers": {"L1_MARKET_PERCEPTION": "objective observations only; no interpretation",
                "L2_MARKET_READING": "interpretation of what the price behaviour is doing",
                "L3_MARKET_MECHANISM": "competing mechanism hypotheses with support/counter/invalidation",
                "L4_MARKET_STATE": "state vector + transitions + forecast",
                "L5_STRATEGY_ADAPTER": "INTERFACE ONLY (define, do not implement trading)"},
    "five_questions_per_decision": ["WHAT_HAPPENED", "WHERE", "WHY", "WHAT_CONTRADICTS_IT", "WHAT_NEXT"],
    "multi_timeframe": {"timeframes": ["H4", "H1", "M15", "M5"], "no_single_direction_compression": True,
                          "must_express": "higher timeframe context + lower timeframe state conflict"},
    "theory_registry_required_fields": ["theory_id", "name", "definition", "formalization", "required_context",
                                          "expected_behavior", "contradicting_behavior", "data_requirements",
                                          "evidence_level", "validation_status"],
    "data_boundary": {"DOM": "UNAVAILABLE", "TRADE_DIRECTION": "UNAVAILABLE", "SPREAD": "DIRECT",
                       "TICK_VOLUME": "DIRECT_BUT_ALL_ZERO_NOT_REAL_VOLUME", "ABSORPTION": "PROXY", "LIQUIDITY": "PROXY",
                       "NO_DATA_PURCHASE": True},
    "time_rule": "any candle/state/mechanism/forecast must satisfy timestamp <= decision_time (task §46)",
}


def main():
    for d in (ONT, REGD, os.path.join(ROOT, "audit"), os.path.join(ROOT, "ledger"), os.path.join(ROOT, "reports"), os.path.join(ROOT, "tests")):
        os.makedirs(d, exist_ok=True)
    docs = {
        "market_reading_ontology.json": MARKET_READING_ONTOLOGY,
        "candle_ontology.json": CANDLE_ONTOLOGY,
        "price_structure_ontology.json": PRICE_STRUCTURE_ONTOLOGY,
        "market_behavior_ontology.json": BEHAVIOUR_ONTOLOGY,
        "market_mechanism_ontology.json": MECHANISM_ONTOLOGY,
        "market_state_ontology.json": STATE_ONTOLOGY,
        "forecast_ontology.json": FORECAST_ONTOLOGY,
    }
    hashes = {}
    for fn, obj in docs.items():
        w(os.path.join(ONT, fn), obj)
        hashes[fn] = sha_obj(obj)
    ontology_hash = sha_obj(hashes)
    registry = {
        "registry_name": "v1_r2_market_reading_registry", "version": REGISTRY_VERSION, "status": "FROZEN",
        "frozen_at_utc": NOW, "ontology_version": ONTOLOGY_VERSION, "ontology_files": hashes,
        "ontology_hash": ontology_hash,
        "candle_definitions": CANDLE_ONTOLOGY, "price_structure_definitions": PRICE_STRUCTURE_ONTOLOGY,
        "behaviour_definitions": BEHAVIOUR_ONTOLOGY, "mechanism_definitions": MECHANISM_ONTOLOGY,
        "state_definitions": STATE_ONTOLOGY, "forecast_definitions": FORECAST_ONTOLOGY,
        "transition_definitions": STATE_ONTOLOGY["transition"], "evidence_hierarchy": MECHANISM_ONTOLOGY["evidence_hierarchy"],
        "data_quality_rules": MARKET_READING_ONTOLOGY["data_boundary"], "invalidation_rules": MECHANISM_DEFS,
        "frozen_before_run": True, "no_rule_change_after_run": True, "no_data_purchase": True,
        "L5_STRATEGY_ADAPTER": {"interface_only": True, "input": ["market_state", "forecast", "horizon", "confidence", "invalidation", "market_condition"],
                                 "output": ["strategy_type"], "allowed": ["GRID", "TREND", "MEAN_REVERSION", "BREAKOUT", "REVERSAL", "EVENT", "NO_TRADE", "OTHER"],
                                 "implemented": False, "decoupling_rule": "market judgement never redefined by a chosen strategy"},
    }
    registry["registry_hash"] = sha_obj({k: v for k, v in registry.items() if k != "registry_hash"})
    w(os.path.join(REGD, "v1_r2_market_reading_registry.json"), registry)
    print(json.dumps({"ontology_hash": ontology_hash, "registry_hash": registry["registry_hash"],
                        "files": sorted(docs.keys())}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
