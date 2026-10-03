"""Latency cost: price_at_decision -> price_at_execution.

CONVENTION: ts arrays are **milliseconds since epoch**.

The adverse part is a COST; a favourable drift is a (small) credit.
Never absorbed into 'slippage'; never reported as DATA_GAP when ticks exist.
"""
from __future__ import annotations

import numpy as np


def latency_cost_bp(ts_ms, mid_arr, idx, latency_ms, direction):
    t = np.asarray(ts_ms, np.int64)
    m = np.asarray(mid_arr, float)
    t0 = t[idx]
    j = np.searchsorted(t, t0 + int(latency_ms), side="left")
    ok = j < len(t)
    jj = np.clip(j, 0, len(t) - 1)
    m0 = m[idx]
    out = np.full(len(idx), np.nan)
    good = ok & np.isfinite(m0) & (m0 > 0)
    out[good] = np.asarray(direction, float) * (m[jj[good]] - m0[good]) / m0[good] * 1e4
    return out
