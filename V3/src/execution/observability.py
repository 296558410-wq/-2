"""Execution observability registry (task XXIV/XXV).

Every execution field carries exactly one status:

    OBSERVABLE | PARTIAL | NOT_OBSERVABLE

`NOT_OBSERVABLE` must NEVER be replaced by 0. A field that is not observable makes
any statistic derived from it `NOT_TESTED` rather than 0.
"""
from __future__ import annotations

STATUSES = ("OBSERVABLE", "PARTIAL", "NOT_OBSERVABLE")

FIELDS = {
    "entry_price": "OBSERVABLE",
    "entry_bid": "OBSERVABLE",
    "entry_ask": "OBSERVABLE",
    "entry_mid": "OBSERVABLE",
    "entry_spread": "OBSERVABLE",
    "commission": "OBSERVABLE",
    "actual_latency": "PARTIAL",
    "slippage": "PARTIAL",
    "adverse_selection": "PARTIAL",
    "markout": "OBSERVABLE",
    "queue_position": "NOT_OBSERVABLE",
    "fill_probability": "NOT_OBSERVABLE",
    "market_impact": "NOT_OBSERVABLE",
    "order_book_depth": "NOT_OBSERVABLE",
    "trade_flow": "NOT_OBSERVABLE",
}

EXPECTED_FILL = "PERFECT_ASSUMED"      # not a measured fill model
SLIPPAGE_INJECTED = False
LATENCY_INJECTED = False


def registry():
    return {"schema": "v3_execution_observability/1", "fields": dict(FIELDS),
            "expected_fill": EXPECTED_FILL, "slippage_injected": SLIPPAGE_INJECTED,
            "latency_injected": LATENCY_INJECTED}


def observable(field):
    if field not in FIELDS:
        raise KeyError(field)
    return FIELDS[field]


def value_or_gap(field, value):
    """Return the value only if the field is OBSERVABLE; else 'NOT_OBSERVABLE'."""
    if FIELDS.get(field) != "OBSERVABLE":
        return "NOT_OBSERVABLE"
    return value


def cannot_claim_zero(field):
    """A statistic over a non-observable field must be reported as NOT_TESTED, not 0."""
    return FIELDS.get(field) != "OBSERVABLE"
