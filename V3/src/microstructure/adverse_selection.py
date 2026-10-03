"""adverse_selection — locked AS definition for V3 research.

Task: V3-HFT-DATA-EXECUTION-GAP-CLOSURE-001 (task XIX/XX/XXI/XXII/XXIII).

SIGN_CONVENTION
===============
    LONG_AS_h  = entry_execution_price - future_mid
    SHORT_AS_h = future_mid - entry_execution_price

    AS > 0  =>  price moved AGAINST the filled position after the fill  (adverse)
    AS < 0  =>  price moved in FAVOUR of the filled position            (favorable)

    AS is exactly the negative of EXECUTION_MARKOUT (see markout.py).
    `entry_execution_price` is the real ask for a long and the real bid for a short.

CENSORING
=========
    HORIZON_ELIGIBLE : a real tick exists at/after t+h
    HORIZON_CENSORED : not eligible; the tail of the sample can never be evaluated
                       for long horizons. Censored samples are EXCLUDED, never 0.

STATISTICS: mean, median, std, p10, p25, p75, p90, effective_n are reported together;
CENTRAL_TENDENCY vs TAIL_EFFECT must be read separately (the mean may be fat-tail driven).
"""
from __future__ import annotations

import numpy as np

HORIZONS_MS = [100, 250, 500, 1000, 2000, 5000, 10000, 30000]
ELIGIBLE = "HORIZON_ELIGIBLE"
CENSORED = "HORIZON_CENSORED"


def adverse_selection(ts_ms, mid_arr, bid, ask, idx, h_ms, direction):
    direction = int(direction)
    if direction not in (-1, 1):
        raise ValueError("direction must be +1 (long) or -1 (short)")
    t = np.asarray(ts_ms, np.int64)
    m = np.asarray(mid_arr, float)
    j = np.searchsorted(t, t[idx] + int(h_ms), side="left")
    eligible = j < len(t)
    jj = np.clip(j, 0, len(t) - 1)
    entry_exec = np.asarray(ask if direction == 1 else bid, float)[idx]
    future_mid = m[jj]
    as_bp = np.full(len(idx), np.nan)
    if direction == 1:
        val = (entry_exec - future_mid) / entry_exec * 1e4
    else:
        val = (future_mid - entry_exec) / entry_exec * 1e4
    as_bp = np.where(eligible, val, np.nan)
    return {"direction": direction, "h_ms": int(h_ms), "AS_bp": as_bp,
            "eligibility": np.where(eligible, ELIGIBLE, CENSORED),
            "eligible_n": int(eligible.sum()), "censored_n": int((~eligible).sum()),
            "entry_execution_price": entry_exec, "future_mid": future_mid}


def stats(as_bp, cost_bp=None):
    v = np.asarray(as_bp, float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {"effective_n": 0, "status": "DATA_INSUFFICIENT"}
    mean, med, sd = float(np.mean(v)), float(np.median(v)), float(np.std(v))
    return {"effective_n": int(v.size),
            "mean": mean, "median": med, "std": sd,
            "p10": float(np.percentile(v, 10)), "p25": float(np.percentile(v, 25)),
            "p75": float(np.percentile(v, 75)), "p90": float(np.percentile(v, 90)),
            "CENTRAL_TENDENCY_bp": med, "TAIL_EFFECT_bp": mean - med,
            "tail_dominated": bool(abs(mean - med) > 0.1 * sd),
            "fraction_adverse": float(np.mean(v > 0)), "fraction_favorable": float(np.mean(v < 0))}


def self_test():
    """Artificial data: prove adverse -> AS>0 and favourable -> AS<0. Task FAILs if not."""
    # t=0,1000(idx) in ms; mid 100; ask 100.1 bid 99.9
    ts = np.array([0, 1000], np.int64)
    mid = np.array([100.0, 100.0])
    bid = np.array([99.9, 99.9])
    ask = np.array([100.1, 100.1])
    idx = np.array([0])
    out = {}
    # LONG + price up (future mid 101) -> favorable -> AS < 0
    up = np.array([100.0, 101.0]); dn = np.array([100.0, 99.0])
    r = adverse_selection(ts, up, bid, ask, idx, 1000, +1); out["LONG_price_up"] = float(r["AS_bp"][0])
    r = adverse_selection(ts, dn, bid, ask, idx, 1000, +1); out["LONG_price_down"] = float(r["AS_bp"][0])
    r = adverse_selection(ts, up, bid, ask, idx, 1000, -1); out["SHORT_price_up"] = float(r["AS_bp"][0])
    r = adverse_selection(ts, dn, bid, ask, idx, 1000, -1); out["SHORT_price_down"] = float(r["AS_bp"][0])
    checks = {
        "LONG_price_up_AS_negative": out["LONG_price_up"] < 0,
        "LONG_price_down_AS_positive": out["LONG_price_down"] > 0,
        "SHORT_price_up_AS_positive": out["SHORT_price_up"] > 0,
        "SHORT_price_down_AS_negative": out["SHORT_price_down"] < 0,
    }
    return {"values": out, "checks": checks, "result": "PASS" if all(checks.values()) else "TASK_FAIL"}
