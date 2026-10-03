# -*- coding: utf-8 -*-
"""V1-R3 HERMES MARKET FORECAST ENGINE — REGISTRY FREEZE (§44, §53, §77, §105, §4).

Creates the R3 workspace and freezes: context schema, time semantics, Hermes prompt, model registry,
evaluation registry, baseline registry, ablation registry, blind split. All sha256-pinned BEFORE any
forecast is produced. Read-only on frozen upstream artifacts. Writes ONLY under v1_r3_hermes_market_forecast/.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

REPO = r"C:\AIQuant"
ROOT = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r3_hermes_market_forecast")
R2 = os.path.join(REPO, "research", "hermes", "trader_v1", "v1_r2_full_optimization")
NOW = datetime.now(timezone.utc).isoformat()
DIRS = ["registry", "context", "prompt", "model", "forecasts", "evaluation", "blind", "ablation",
        "replay", "audit", "ledger", "reports", "tests", "baselines"]

HERMES_PROMPT = """You are HERMES, a market-structure forecasting engine for XAUUSD.

You are given a point-in-time (PIT) market context. You must reason ONLY from that context.
You have NO access to any future information, labels, outcomes, returns, PnL or directional answers.
If the context is insufficient or self-contradictory, you MUST abstain rather than guess.

Answer these ten questions in order, then emit the forecast JSON.

A. What is happening?            Describe the current market from the evidence given.
B. What is the dominant structure? Name the prevailing price structure and why.
C. What pressures are building?  Name the pressures (directional, volatility, liquidity-proxy).
D. What mechanisms could explain it? Propose the candidate mechanisms and say whether each is supported.
E. What is the strongest evidence? List the strongest supporting observations.
F. What is the strongest counter-evidence? Actively search for evidence AGAINST your own reading.
G. What could happen next?       State the PRIMARY scenario.
H. What is the alternative?      State at least one ALTERNATIVE scenario.
I. What would invalidate the forecast? Give explicit, checkable invalidation conditions.
J. What would change your mind?  Give explicit evidence that would flip your judgement.

RULES
- Directions allowed: UP, DOWN, NEUTRAL, UNDEFINED, NO_DIRECTIONAL_EDGE. You are NOT required to give a
  direction; a clear structural/scenario forecast with NO_DIRECTIONAL_EDGE is a valid answer.
- Timing allowed: IMMEDIATE, SHORT_TERM, INTRADAY, HIGHER_TIMEFRAME, or TIMING_UNCERTAIN.
- Confidence is YOUR SUBJECTIVE confidence in [0,1]. It is NOT a statistical probability; do not present it as one.
- You may ABSTAIN (abstain=true) with a reason. Abstention is a capability, not a failure.
- NEVER invent data that is not in the context. Respect every data_quality tag (DIRECT/DERIVED/PROXY/UNKNOWN).
- UST10Y is a PROXY (^TNX); never treat it as an official yield series.

OUTPUT: exactly one JSON object, no prose outside it, with these keys:
forecast_id, timestamp, current_state, dominant_structure, current_pressure,
primary_scenario{scenario,confidence,horizon,trigger,invalidation},
alternative_scenario{scenario,confidence,horizon,trigger,invalidation},
third_scenario (optional, same shape or null),
direction_bias (UP|DOWN|NEUTRAL|UNDEFINED|NO_DIRECTIONAL_EDGE),
expected_state_transition, time_horizon, confidence,
supporting_evidence[], counter_evidence[], trigger, invalidation, change_my_mind[],
abstain (bool), abstain_reason, reasoning_trace[], questions{A..J}"""

CONTEXT_SCHEMA = {
    "schema_id": "HERMES_MARKET_CONTEXT", "version": "v1r3-r1",
    "layers": {
        "L1_PRICE_KLINE": {"timeframes": ["M1", "M5", "M15", "H1", "H4"], "per_bar": ["timestamp", "open", "high", "low", "close", "range", "body", "upper_wick", "lower_wick", "body_ratio", "range_percentile", "atr", "volatility"], "sequence": "last N bars per timeframe", "labels": ["RAW", "DERIVED"]},
        "L2_PRICE_STRUCTURE": {"fields": ["swing_high", "swing_low", "support", "resistance", "level_id", "level_origin", "level_age", "touch_count", "last_touch", "break_status", "reclaim_status", "retest", "rejection", "acceptance"], "labels": ["DERIVED"]},
        "L3_MARKET_BEHAVIOUR": {"fields": ["TREND", "RANGE", "COMPRESSION", "EXPANSION", "ROTATION", "REJECTION", "ACCEPTANCE", "EXHAUSTION", "BREAKOUT", "FAILED_BREAKOUT", "REVERSAL_ATTEMPT", "CONTINUATION"], "labels": ["OBSERVED", "DERIVED", "INFERRED"]},
        "L4_MARKET_MECHANISM": {"fields": ["trend_continuation", "range_rotation", "breakout_pressure", "failed_breakout", "volatility_repricing", "macro_repricing", "liquidity_withdrawal_proxy", "exhaustion", "reversal_pressure"], "per_mechanism": ["supporting_evidence", "counter_evidence", "invalidation", "data_quality"]},
        "L5_STATE_HISTORY": {"fields": ["current_state", "past_states", "durations", "transitions", "sequence"]},
        "L6_MULTI_TIMEFRAME": {"timeframes": ["M5", "M15", "H1", "H4"], "fields": ["each_tf_state", "agreement", "conflict", "transition"]},
        "L7_CROSS_MARKET": {"series": ["DXY", "VIX", "UST10Y_PROXY_TNX"], "absent": ["GLD", "GC", "COT", "ETF_FLOWS", "NEWS", "MACRO_EVENTS"], "per_series": ["value", "change", "quality", "source", "timestamp"], "rule": "quality in DIRECT|DERIVED|PROXY|UNKNOWN; UST10Y is PROXY and must never be upgraded"},
    },
    "historical_analog": {"fields": ["analog_id", "t0_state", "state_evolution", "similarity_method", "similarity", "retrieval_timestamp"], "forbidden": ["future_return", "future_pnl", "future_win_rate", "future_direction_label"]},
    "forbidden_keys": ["future", "future_return", "future_pnl", "pnl", "profit", "win", "loss", "win_rate", "ground_truth", "actual_next_state", "NEXT_STATE_LABEL", "future_state", "future_direction", "forward_return", "sharpe"],
    "allowed_similar_keys": ["historical_state_evolution", "state_transition_history"]
}

TIME_SEMANTICS = {
    "XAUUSD": {"source": "HistData.com M1 (BID)", "timezone": "EST UTC-5 FIXED (VERIFIED)", "dst": "NOT_APPLICABLE",
                "timestamp_definition": "bar open time, EST fixed; converted to UTC for this engine",
                "bar_close_definition": "UNKNOWN (vendor not documented) -> treated as bar close = tradable, PIT OK",
                "availability_definition": "bar available at its close time", "quality": "DERIVED"},
    "DXY": {"source": "Yahoo chart API DX-Y.NYB", "timezone": "UTC epoch", "timestamp_definition": "bar open time (Yahoo convention UNKNOWN)",
             "bar_close_definition": "UNKNOWN", "availability_definition": "UNKNOWN -> treated as available at bar time", "quality": "PROXY"},
    "VIX": {"source": "Yahoo ^VIX", "timezone": "UTC epoch", "timestamp_definition": "bar open (UNKNOWN)", "bar_close_definition": "UNKNOWN",
             "availability_definition": "UNKNOWN", "quality": "PROXY"},
    "UST10Y_PROXY_TNX": {"source": "Yahoo ^TNX", "timezone": "UTC epoch", "timestamp_definition": "intraday bars land on a :20 grid offset",
                           "bar_close_definition": "UNKNOWN", "availability_definition": "UNKNOWN", "quality": "PROXY",
                           "note": "^TNX is a CBOE yield INDEX proxy, NOT the official Treasury constant-maturity yield; never call it DIRECT UST10Y"},
    "grid_rule": "XAUUSD M15 bars on :00/:15/:30/:45; cross-market 5m floored to 15m grid; NO silent time shift; offsets documented",
    "no_silent_shift": True
}

EVALUATION = {
    "ground_truth_generator": "independent module; uses bars <= t+H only; NEVER feeds Hermes",
    "targets": {"ACTUAL_NEXT_STATE": "STATE_V2(t+H)", "ACTUAL_TRANSITION": "STATE_V2(t+H) != STATE_V2(t)",
                 "ACTUAL_DIRECTION": "structural direction of EVENT(t+H): UP/DOWN/NEUTRAL",
                 "ACTUAL_TIMING": "first-change bucket within 1/2/4/8/16 bars or >16",
                 "ACTUAL_INVALIDATION": "family(STATE_V2(t+H)) != family(STATE_V2(t))"},
    "H": 8, "horizons_reported": ["M5", "M15", "H1", "H4"],
    "metrics": ["accuracy", "balanced_accuracy", "macro_F1", "log_loss", "Brier", "ECE", "coverage", "abstention_accuracy", "majority_baseline_displayed"],
    "levels": {"L0": "NONE", "L1": "MARKET_READING", "L2": "STATE_RECOGNITION", "L3": "STATE_TRANSITION/SCENARIO", "L4": "DIRECTION", "L5": "TIMING", "L6": "STRATEGY_RELEVANT"},
    "decision_rules": {"A_SUPPORTED": "Hermes>baseline AND blind/null/replay/lookahead PASS", "B_INCONCLUSIVE": "Hermes>baseline but effect small",
                        "C_UNSUPPORTED": "Hermes<=baseline", "D_LAYERED": "report per level, no OVERALL_SUCCESS masking"},
    "effect_floor": {"log_loss_bits": 0.01, "balanced_accuracy": 0.02}
}

BASELINES = ["MAJORITY", "PERSISTENCE", "PREVIOUS_STATE", "SIMPLE_TRANSITION", "FROZEN_NEXT_STATE_MODEL"]

ABLATIONS = {
    "information_content": ["PRICE", "PRICE+KLINE", "PRICE+STRUCTURE", "PRICE+STATE", "PRICE+EVENT",
                             "PRICE+MTF", "PRICE+MECHANISM", "PRICE+CROSSMARKET", "FULL"],
    "hermes_context": ["HERMES_FULL", "HERMES_PRICE_ONLY", "HERMES_PRICE_KLINE"],
    "module_toggles": ["KLINE", "MTF", "CROSSMARKET", "MECHANISM", "HISTORICAL_ANALOG", "COUNTER_EVIDENCE"],
    "rule": "all ablations saved; no best-only reporting (§88)"
}

BLIND_SPLIT = {
    "design": "earlier period = DEVELOPMENT, later period = BLIND (time isolation, no random shuffle)",
    "development": ["2025-01-01T23:00Z", "2026-05-31T23:59Z"],
    "blind": ["2026-06-01T00:00Z", "2026-09-18T21:45Z"],
    "crossmarket_subwindow": ["2026-07-17T04:00Z", "2026-09-18T20:55Z"],
    "purge_bars": 480, "embargo_bars": 1,
    "rules": ["Hermes never sees labels", "OpenClaw never edits prompt after seeing blind results", "BLIND=TRUE recorded"]
}


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def wjson(rel, o):
    p = os.path.join(ROOT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, default=str)
    return p


def main():
    for d in DIRS:
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)
    ctx_h = sha_obj(CONTEXT_SCHEMA)
    ts_h = sha_obj(TIME_SEMANTICS)
    pr_h = hashlib.sha256(HERMES_PROMPT.encode("utf-8")).hexdigest()
    ev_h = sha_obj(EVALUATION)
    bs_h = sha_obj(BASELINES)
    ab_h = sha_obj(ABLATIONS)
    bl_h = sha_obj(BLIND_SPLIT)
    model = {"registry_id": "v1r3-hermes-model-r1", "model": "deepseek/deepseek-v4-flash",
              "provider": "custom-yuanyuaicloud-cn", "prompt_hash": pr_h, "context_schema_hash": ctx_h,
              "temperature": "runtime_default", "seed": "runtime_default",
              "runtime": "OpenClaw subagent (isolated context), tools disabled for forecast calls",
              "invocation": "one isolated Hermes call per (timestamp, context_variant); no shared state", "ts_utc": NOW}
    reg = {"task": "V1_R3_HERMES_MARKET_FORECAST_ENGINE", "registry_id": "v1r3-hermes-forecast-registry-r1",
            "frozen": True, "frozen_before_any_forecast": True, "frozen_at_utc": NOW,
            "context_schema": CONTEXT_SCHEMA, "time_semantics": TIME_SEMANTICS, "prompt": HERMES_PROMPT,
            "evaluation": EVALUATION, "baselines": BASELINES, "ablations": ABLATIONS, "blind_split": BLIND_SPLIT,
            "model_registry": model,
            "upstream_frozen": {"r2_final": os.path.relpath(os.path.join(R2, "reports", "V1_R2_FULL_OPTIMIZATION_FINAL.json"), REPO),
                                 "c1_ontology_hash": "8436866dfe71030ba7be036b2d73904ed2f817aa52673a5e27d583e931c354d8"},
            "hard_safety": {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
                             "V2_WRITE": 0, "V3_WRITE": 0, "BOUNDARY_VIOLATION": 0, "V1_EXECUTION_MODIFIED": 0,
                             "V1_RISK_MODIFIED": 0, "V1_ORDER_LOGIC_MODIFIED": 0}}
    reg["prompt_hash"] = pr_h
    reg["context_schema_hash"] = ctx_h
    reg["time_semantics_hash"] = ts_h
    reg["evaluation_hash"] = ev_h
    reg["baseline_hash"] = bs_h
    reg["ablation_hash"] = ab_h
    reg["blind_split_hash"] = bl_h
    reg["registry_hash"] = sha_obj({k: v for k, v in reg.items() if k != "registry_hash"})
    wjson("registry/v1_r3_hermes_forecast_registry.json", reg)
    wjson("registry/hermes_model_registry.json", model)
    wjson("prompt/hermes_market_forecast_prompt.txt", HERMES_PROMPT)
    wjson("prompt/PROMPT_FREEZE.json", {"prompt_hash": pr_h, "frozen_at_utc": NOW, "version": "v1r3-prompt-r1", "immutable": True})
    wjson("audit/REGISTRY_FREEZE.json", {"registry_hash": reg["registry_hash"], "prompt_hash": pr_h, "context_schema_hash": ctx_h,
                                           "time_semantics_hash": ts_h, "frozen_at_utc": NOW})
    print("ROOT:", ROOT)
    print("registry_hash:", reg["registry_hash"][:16], "| prompt_hash:", pr_h[:16], "| ctx_hash:", ctx_h[:16])


if __name__ == "__main__":
    main()
