"""Microprice — requires bid/ask SIZES.

On the FXTM L1-quote-only feed `volume`/`volume_real`/`last` are identically 0,
so microprice is DATA_GAP. Never substitute mid for microprice.
"""
from __future__ import annotations

import numpy as np


def microprice(bid, ask, bid_size, ask_size):
    """Size-weighted microprice. Returns (None, reason) when sizes are absent/degenerate."""
    if bid_size is None or ask_size is None:
        return None, "DATA_GAP(no sizes)"
    bv = np.asarray(bid_size, float)
    av = np.asarray(ask_size, float)
    den = bv + av
    if not np.any(den > 0) or not np.any(bv != av):
        return None, "DATA_GAP(sizes identically zero / no imbalance information)"
    b = np.asarray(bid, float)
    a = np.asarray(ask, float)
    return (b * av + a * bv) / np.where(den > 0, den, 1.0), "OK"


def microprice_status(volume_nonzero_frac, last_nonzero_frac):
    if volume_nonzero_frac == 0 and last_nonzero_frac == 0:
        return "DATA_GAP(sizes and prints identically zero -> L1_QUOTE_ONLY)"
    if volume_nonzero_frac == 0:
        return "DATA_GAP(no sizes)"
    return "AVAILABLE"
