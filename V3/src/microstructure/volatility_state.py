"""Volatility state from rolling returns (L1-computable)."""
from __future__ import annotations

import numpy as np


def rolling_vol_bp(mid, window=50):
    m = np.asarray(mid, float)
    r = np.full(len(m), np.nan)
    r[1:] = (m[1:] / m[:-1] - 1.0) * 1e4
    out = np.full(len(m), np.nan)
    w = int(window)
    if len(m) > w:
        c1 = np.concatenate([[0.0], np.cumsum(np.nan_to_num(r))])
        c2 = np.concatenate([[0.0], np.cumsum(np.nan_to_num(r) ** 2)])
        mean = (c1[w:] - c1[:-w]) / w
        m2 = (c2[w:] - c2[:-w]) / w
        out[w - 1:] = np.sqrt(np.maximum(m2 - mean * mean, 0.0))
    return out


def state_labels(values, q=(0.33, 0.66)):
    """low / mid / high by empirical quantiles of a finite sample."""
    v = np.asarray(values, float)
    fin = np.isfinite(v)
    if fin.sum() < 10:
        return np.full(len(v), "DATA_GAP", dtype=object), None
    lo, hi = np.quantile(v[fin], q)
    lab = np.full(len(v), "mid", dtype=object)
    lab[np.isfinite(v) & (v <= lo)] = "low"
    lab[np.isfinite(v) & (v > hi)] = "high"
    lab[~fin] = "DATA_GAP"
    return lab, {"q33": float(lo), "q66": float(hi)}
