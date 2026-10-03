"""L1 spread primitives. Available on the FXTM feed (bid, ask, ts)."""
from __future__ import annotations

import numpy as np

BP = 1e4


def mid(bid, ask):
    return (np.asarray(bid, float) + np.asarray(ask, float)) / 2.0


def spread(bid, ask):
    return np.asarray(ask, float) - np.asarray(bid, float)


def spread_bp(bid, ask):
    m = mid(bid, ask)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(m > 0, spread(bid, ask) / m * BP, np.nan)


def spread_stats(bid, ask):
    s = spread_bp(bid, ask)
    s = s[np.isfinite(s)]
    if s.size == 0:
        return {"status": "DATA_GAP", "n": 0}
    su = spread(bid, ask)
    su = su[np.isfinite(su)]
    return {"status": "OK", "n": int(s.size),
            "median_bp": float(np.median(s)), "p90_bp": float(np.percentile(s, 90)),
            "p99_bp": float(np.percentile(s, 99)),
            "median_usd": float(np.median(su))}
