"""markout — locked definition for V3 research.

Task: V3-HFT-DATA-EXECUTION-GAP-CLOSURE-001 (task XVII/XVIII/XXII/XXIII).

CONVENTION: timestamps are integer **milliseconds since epoch** (declared via
`timestamp_unit_guard`; never inferred).

SIGN CONVENTION
---------------
    MARKOUT > 0  => the position moved FAVOURABLY after entry.
    MARKOUT < 0  => the position moved AGAINST the position after entry.

LOCKED FORMULAS (do not blur into one "markout")
-----------------------------------------------
    LONG :  EXECUTION_MARKOUT = future_mid - entry_execution_price
    SHORT:  EXECUTION_MARKOUT = entry_execution_price - future_mid
    MID_MARKOUT           = direction * (future_mid - entry_mid)
    COST_ADJUSTED_MARKOUT = MID_MARKOUT - cost_bp        (lump-sum round-trip cost)

CENSORING (mandatory)
---------------------
    HORIZON_ELIGIBLE : a real tick exists at/after t+h inside the same segment
    HORIZON_CENSORED : no such tick -> the sample is NOT eligible.
    A censored sample is NEVER recorded as markout = 0.
"""
from __future__ import annotations

import numpy as np

HORIZONS_MS = [100, 250, 500, 1000, 2000, 5000, 10000, 30000]
TERMINAL = "HORIZON_CENSORED"
ELIGIBLE = "HORIZON_ELIGIBLE"


def forward_mid(ts_ms, mid_arr, idx, h_ms):
    t = np.asarray(ts_ms, np.int64)
    m = np.asarray(mid_arr, float)
    j = np.searchsorted(t, t[idx] + int(h_ms), side="left")
    eligible = j < len(t)
    jj = np.clip(j, 0, len(t) - 1)
    return m[jj], eligible, jj


def _stats(v, cost_bp=None):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {"effective_n": 0, "status": "DATA_INSUFFICIENT"}
    eff_n = int(v.size)
    out = {"effective_n": eff_n,
           "mean": float(np.mean(v)), "median": float(np.median(v)), "std": float(np.std(v)),
           "p10": float(np.percentile(v, 10)), "p25": float(np.percentile(v, 25)),
           "p75": float(np.percentile(v, 75)), "p90": float(np.percentile(v, 90)),
           "mean_minus_median": float(np.mean(v) - np.median(v)),
           "tail_effect": bool(abs(np.mean(v) - np.median(v)) > np.std(v) * 0.1)}
    return out


def markout(ts_ms, mid_arr, bid, ask, idx, h_ms, direction):
    """Return MID / EXECUTION / COST_ADJUSTED markout plus censoring flags."""
    direction = int(direction)
    if direction not in (-1, 1):
        raise ValueError("direction must be +1 (long) or -1 (short)")
    fm, eligible, fwd_idx = forward_mid(ts_ms, mid_arr, idx, h_ms)
    entry_mid = np.asarray(mid_arr, float)[idx]
    entry_exec = np.asarray(ask if direction == 1 else bid, float)[idx]
    mid_mo = np.where(eligible, direction * (fm - entry_mid) / entry_mid * 1e4, np.nan)
    exec_mo = np.where(eligible, direction * (fm - entry_exec) / entry_exec * 1e4, np.nan)
    return {"direction": direction, "h_ms": int(h_ms), "fwd_idx": fwd_idx,
            "eligibility": np.where(eligible, ELIGIBLE, TERMINAL),
            "eligible_n": int(eligible.sum()), "censored_n": int((~eligible).sum()),
            "MID_MARKOUT": mid_mo, "EXECUTION_MARKOUT": exec_mo,
            "entry_mid": entry_mid, "entry_execution_price": entry_exec, "future_mid": fm}


def profile(ts_ms, mid_arr, bid, ask, idx, direction, cost_bp):
    out = {}
    for h in HORIZONS_MS:
        r = markout(ts_ms, mid_arr, bid, ask, idx, h, direction)
        ok = r["eligibility"] == ELIGIBLE
        mid_v, ex_v = r["MID_MARKOUT"][ok], r["EXECUTION_MARKOUT"][ok]
        out[f"{h}ms"] = {
            "MID_MARKOUT": _stats(mid_v),
            "EXECUTION_MARKOUT": _stats(ex_v),
            "COST_ADJUSTED_MARKOUT": _stats(mid_v - cost_bp) if mid_v.size else
            {"effective_n": 0, "status": "DATA_INSUFFICIENT"},
            "eligible_n": r["eligible_n"], "censored_n": r["censored_n"],
            "censored_fraction": (r["censored_n"] / max(1, r["censored_n"] + r["eligible_n"])),
        }
    return out
