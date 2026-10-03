# -*- coding: utf-8 -*-
"""V3 strategy evaluation (§22–§28): cost stress, blocked OOS, regime, effective n, BH-FDR, verdicts."""
from __future__ import annotations
import math

import numpy as np

COST_ANCHOR_BP_ROUND_TRIP = 0.914     # frozen V3 cost anchor (calibrated); 1x realistic
STRESS = (0.0, 1.0, 2.0, 3.0)         # §22


def hold_pnl_bp(b, i, direction, hold_bars):
    """Return (gross_bp, exec_ts, exit_ts). Execution at t+1 open; exit at t+1+hold close.
    Never uses the signal bar's own close for execution (§7 no same-bar cheating)."""
    e = i + 1
    x = e + hold_bars
    if x >= len(b):
        return None
    entry = b["mid_open"].iloc[e]
    if not np.isfinite(entry) or entry <= 0:
        return None
    exit_ = b["mid_close"].iloc[x]
    if not np.isfinite(exit_):
        return None
    sgn = 1.0 if direction == "LONG" else -1.0
    return (exit_ - entry) / entry * 1e4 * sgn, str(b["ts_utc"].iloc[e]), str(b["ts_utc"].iloc[x])


def effective_n(ts_list, horizon_min):
    """Overlap-adjusted effective sample size: signals closer than the holding horizon are not
    independent samples (§24)."""
    if not ts_list:
        return 0
    ts = sorted(ts_list)
    kept = 1
    last = ts[0]
    for t in ts[1:]:
        if (t - last).total_seconds() / 60.0 >= horizon_min:
            kept += 1
            last = t
    return kept


def stats(nets):
    if not nets:
        return {"n": 0}
    a = np.asarray(nets, dtype=float)
    wins = a[a > 0]
    losses = a[a <= 0]
    gw = float(wins.sum()); gl = float(abs(losses.sum()))
    return {"n": int(len(a)), "mean_bp": round(float(a.mean()), 3), "median_bp": round(float(np.median(a)), 3),
            "win_rate": round(float(len(wins) / len(a)), 4), "gross_bp": round(float(a.sum()), 2),
            "profit_factor": (round(gw / gl, 3) if gl > 0 else None),
            "max_dd_bp": round(float(_max_dd(a)), 2)}


def _max_dd(a):
    c = np.cumsum(a)
    peak = np.maximum.accumulate(c)
    return float((c - peak).min()) if len(c) else 0.0


def bh_fdr(pvals, q=0.05):
    """Benjamini–Hochberg (§25). Returns decisions per input order."""
    m = len(pvals)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: pvals[i])
    thresh = [(k + 1) / m * q for k in range(m)]
    kmax = -1
    for k, i in enumerate(order):
        if pvals[i] <= thresh[k]:
            kmax = k
    dec = [False] * m
    for k, i in enumerate(order):
        if k <= kmax:
            dec[i] = True
    return dec
