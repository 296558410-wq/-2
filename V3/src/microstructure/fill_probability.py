"""Fill-probability framework (task XII) — INTERFACE ONLY.

No real L2 queue data exists on this feed, so a genuine P(fill|state) is DATA_GAP.
This module exposes the interface and an explicit SIMULATION scaffold; it never
claims a measured fill probability.
"""
from __future__ import annotations

INPUTS_REQUIRED = ["spread", "volatility", "quote_arrival_rate", "queue_position",
                   "imbalance", "latency", "time_to_fill", "cancellation_rate"]


def availability():
    return {"measured_fill_probability": "DATA_GAP(L2 queue + order-level data absent)",
            "requires": INPUTS_REQUIRED,
            "interface": "P(fill | state) — scaffold only"}


def p_fill_scaffold(state: dict):
    """Placeholder. Intentionally returns DATA_GAP rather than a fabricated number."""
    missing = [k for k in INPUTS_REQUIRED if k not in state]
    return {"status": "DATA_GAP", "missing_inputs": missing,
            "note": "model interface only; no real fill probability is claimed"}
