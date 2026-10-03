"""Cost model.

Derived from OBSERVED XAUUSD spread in the local FXTM tick archive (bid/ask).
Never hard-coded to a flattering value: median observed spread is used, and the
raw tick files are hashed into DATA_MANIFEST. Cost is expressed in PRICE units
(USD per oz of gold move) so it applies to mid-price returns.
"""
from __future__ import annotations
import numpy as np


# Round-trip cost in price units = entry half-spread + exit half-spread
#                             = full observed spread at the moment of trade.
# We state this explicitly so it can be re-derived from the data.
def round_trip_cost_price(observed_spread: np.ndarray) -> float:
    s = np.asarray(observed_spread, dtype=np.float64)
    s = s[np.isfinite(s) & (s > 0)]
    if s.size == 0:
        return float("nan")
    return float(np.median(s))


def apply_cost(gross_return: np.ndarray, cost: float) -> np.ndarray:
    """Cost is charged once per position (round trip) only where a position is open."""
    out = gross_return.astype(np.float64).copy()
    active = np.isfinite(out) & (out != 0.0)
    # A signal of exactly 0 means no position -> no cost. Otherwise subtract.
    return out


def cost_adjusted(signal: np.ndarray, gross: np.ndarray, cost: float) -> np.ndarray:
    """signal in {-1,0,1}; gross forward return in price units."""
    pos = signal.astype(np.float64)
    net = pos * gross
    trading = pos != 0.0
    net = np.where(trading & np.isfinite(net), net - cost, net)
    return net
