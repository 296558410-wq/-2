"""Tick flow: signed up/down tick counts and quote arrival intensity (L1-only)."""
from __future__ import annotations

import numpy as np


def up_down_counts(mid):
    m = np.asarray(mid, float)
    d = np.sign(np.diff(m))
    return {"n_up": int((d > 0).sum()), "n_dn": int((d < 0).sum()), "n_flat": int((d == 0).sum())}


def tick_rule_flow(mid, window=20):
    """(n_up - n_dn)/window over a rolling window. Name: FLOW_PROXY."""
    m = np.asarray(mid, float)
    d = np.sign(np.diff(m, prepend=m[0]))
    up = np.concatenate([[0.0], np.cumsum(d > 0)])
    dn = np.concatenate([[0.0], np.cumsum(d < 0)])
    w = int(window)
    out = np.full(len(m), np.nan)
    out[w - 1:] = ((up[w:] - up[:-w]) - (dn[w:] - dn[:-w])) / w
    return out, "FLOW_PROXY"
