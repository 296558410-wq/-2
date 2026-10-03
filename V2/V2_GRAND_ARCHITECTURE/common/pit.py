"""PIT (point-in-time) helpers.

A feature computed at bar index t MUST only use information available at or
before t. Forward returns are computed strictly from t+1..t+h and are only used
as evaluation labels, never as inputs to a decision at t.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def forward_return(mid: np.ndarray, h: int) -> np.ndarray:
    """Signed forward return over h bars; value at t uses mid[t+h]-mid[t].

    The last h entries are NaN (no future available) -> not evaluable.
    """
    out = np.full(mid.shape[0], np.nan, dtype=np.float64)
    if h < mid.shape[0]:
        out[:-h] = mid[h:] - mid[:-h]
    return out


def shift_lag(series: np.ndarray, lag: int = 1) -> np.ndarray:
    """Return series shifted so value at t is the value at t-lag (PIT-safe)."""
    out = np.full(series.shape[0], np.nan, dtype=np.float64)
    if lag <= 0:
        raise ValueError("lag must be >= 1")
    out[lag:] = series[:-lag]
    return out


def time_split(dates: pd.Series, splits: dict[str, tuple[str, str]]) -> dict[str, np.ndarray]:
    """Boolean masks per named split. Splits are contiguous, non-overlapping UTC dates."""
    d = pd.to_datetime(dates, utc=True).dt.date
    masks = {}
    for name, (lo, hi) in splits.items():
        lo_d = pd.Timestamp(lo).date()
        hi_d = pd.Timestamp(hi).date()
        masks[name] = ((d >= lo_d) & (d <= hi_d)).to_numpy()
    return masks


def assert_no_overlap(masks: dict[str, np.ndarray]) -> None:
    names = list(masks)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            inter = np.logical_and(masks[names[i]], masks[names[j]]).sum()
            if inter:
                raise AssertionError(f"split overlap {names[i]} x {names[j]} = {inter}")
