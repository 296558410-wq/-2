"""Quote arrival rate / intensity (L1-computable).

CONVENTION: ts arrays are **milliseconds since epoch**.
"""
from __future__ import annotations

import numpy as np


def arrival_rate_hz(ts_ms, window_s=1.0):
    t = np.asarray(ts_ms, np.int64)
    n = len(t)
    if n < 2:
        return np.array([]), "DATA_GAP"
    w = int(window_s * 1000)          # seconds -> ms
    left = np.searchsorted(t, t - w, side="left")
    rate = (np.arange(n) - left) / float(window_s)
    return rate, "OK"
