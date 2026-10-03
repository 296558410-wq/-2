"""Execution quality + failure taxonomy (task XXVI).

Taxonomy labels (bare WIN/LOSS remain forbidden):

    TYPE1_DIRECTION_WRONG
    TYPE2_SPREAD_ERASED_EDGE
    TYPE3_SLIPPAGE_ERASED_EDGE
    TYPE4_LATENCY_ERASED_EDGE
    TYPE5_ADVERSE_SELECTION
    TYPE6_FILL_FAILURE
    TYPE7_EXECUTION_COST_FAILURE

HARD RULE: only a type whose underlying field is observable may be counted as
confirmed. Because this study assumes perfect fill and injects neither slippage nor
latency (see execution/observability.py), TYPE5/TYPE6/TYPE7 are `NOT_TESTED`,
never 0.
"""
from __future__ import annotations

T1 = "TYPE1_DIRECTION_WRONG"
T2 = "TYPE2_SPREAD_ERASED_EDGE"
T3 = "TYPE3_SLIPPAGE_ERASED_EDGE"
T4 = "TYPE4_LATENCY_ERASED_EDGE"
T5 = "TYPE5_ADVERSE_SELECTION"
T6 = "TYPE6_FILL_FAILURE"
T7 = "TYPE7_EXECUTION_COST_FAILURE"
WIN = "WIN"
NOT_TESTED = "NOT_TESTED"

TAXONOMY = [T1, T2, T3, T4, T5, T6, T7]
CONFIRMED_STATUS = {T1: "CONFIRMED", T2: "CONFIRMED", T3: "NOT_TESTED",
                    T4: "NOT_TESTED", T5: "NOT_TESTED", T6: "NOT_TESTED",
                    T7: "NOT_TESTED"}


def classify_confirmed(gross_bp, net_bp, spread_cost_bp):
    """Only uses OBSERVABLE quantities: gross (mid-to-mid), net, spread cost.

    slippage / latency / fill are NOT injected here, therefore TYPE3/4/5/6/7 cannot
    be issued by this function; they are reported as NOT_TESTED by `taxonomy_status()`.
    """
    if gross_bp <= 0:
        return T1
    if net_bp > 0:
        return WIN
    return T2


def taxonomy_status():
    return {"confirmed_types": [k for k, v in CONFIRMED_STATUS.items() if v == "CONFIRMED"],
            "not_tested_types": [k for k, v in CONFIRMED_STATUS.items() if v == "NOT_TESTED"],
            "explanation": ("fill assumed perfect; slippage and latency not injected => "
                            "TYPE5/TYPE6/TYPE7 = NOT_TESTED, never 0"),
            "counts_are_zero_only_if": "the mechanism was actually observed, which it was not"}


def quality_metrics(signed_slippage_list, filled_flags):
    n = len(filled_flags)
    if n == 0:
        return {"status": "DATA_GAP", "n": 0}
    fills = sum(1 for f in filled_flags if f)
    fav = sum(1 for s in signed_slippage_list if s is not None and s < 0)
    unf = sum(1 for s in signed_slippage_list if s is not None and s > 0)
    return {"n": n, "fill_rate": fills / n,
            "favourable_slippage_frac": fav / n, "unfavourable_slippage_frac": unf / n,
            "note": "slippage reported SIGNED; abs(slippage) is never used as cost"}
