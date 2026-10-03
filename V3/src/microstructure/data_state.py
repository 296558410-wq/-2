"""Strict data state machine.

Every field is exactly one of: AVAILABLE / PARTIAL / DATA_GAP / UNSUPPORTED.
Banned: DATA_GAP -> 0, DATA_GAP -> proxy (unless the field is explicitly *_PROXY).
"""
from __future__ import annotations

STATES = ("AVAILABLE", "PARTIAL", "DATA_GAP", "UNSUPPORTED")


def validate(state: str) -> str:
    if state not in STATES:
        raise ValueError(f"invalid data state {state!r}; allowed {STATES}")
    return state


def registry():
    """Field -> state for the FXTM L1-quote-only feed (audited 2026-09-22)."""
    return {
        "bid": "AVAILABLE", "ask": "AVAILABLE", "ts_utc": "AVAILABLE", "flags": "AVAILABLE",
        "mid": "AVAILABLE", "spread": "AVAILABLE", "spread_bp": "AVAILABLE",
        "microprice": "DATA_GAP", "true_ofi": "DATA_GAP", "size_imbalance": "DATA_GAP",
        "queue_position": "DATA_GAP", "trade_flow": "DATA_GAP", "vpin": "DATA_GAP",
        "kyle_lambda": "DATA_GAP", "fill_probability": "DATA_GAP",
        "ofi_proxy": "PARTIAL", "tick_flow_proxy": "PARTIAL",
        "volatility_state": "AVAILABLE", "arrival_rate": "AVAILABLE",
        "markout": "PARTIAL", "adverse_selection": "PARTIAL",
        "latency_profile": "PARTIAL", "cost_profile": "AVAILABLE",
    }
