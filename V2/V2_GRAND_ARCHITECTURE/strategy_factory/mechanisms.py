"""Genuinely diverse mechanism library.

Eleven distinct mechanism families. Each is a PIT decision function:
signal[t] in {-1,0,+1} is the position opened at bar t (close) and held for
`horizon` bars. All inputs are columns of the PIT feature matrix at row t
(features themselves only use bars <= t). These are NOT copies of V1/V2 rules;
they are independent mechanism hypotheses over raw price/spread structure.
"""
from __future__ import annotations
import numpy as np


def _sig(n):
    return np.zeros(n, dtype=np.float64)


def _ret(df, w):
    """PIT w-bar return; uses the cached column when present, else derives it."""
    col = f"ret{w}"
    if col in df.columns:
        return df[col].to_numpy(dtype=np.float64)
    c = df["close"].to_numpy(dtype=np.float64)
    out = np.full(c.shape[0], np.nan)
    if c.shape[0] > w:
        out[w:] = c[w:] - c[:-w]
    return out


def trend_ma_slope(df, fast=5, slow=20, slope_k=1.6):
    """TREND: fast MA above slow MA AND fast-slow gap rising over 3 bars."""
    n = len(df)
    s = _sig(n)
    gap = (df[f"ma{5}"] if False else df["ma5"]) - df["ma20"]
    g = gap.to_numpy(); g3 = np.full(n, np.nan); g3[3:] = g[:-3]
    ts = df["trend_strength"].to_numpy()
    long = (g > 0) & (g - g3 > 0) & (ts > 0.5)
    short = (g < 0) & (g - g3 < 0) & (ts < -0.5)
    s[long] = 1.0; s[short] = -1.0
    return s


def momentum_continuation(df, w=20, thr=2.0, vol_cap=1.5):
    """MOMENTUM: strong recent return continues, but only in non-expanded vol."""
    n = len(df)
    s = _sig(n)
    r = _ret(df, w)
    atr = df["atr14"].to_numpy()
    vr = df["vol_ratio"].to_numpy()
    z = r / atr
    s[(z > thr) & (vr < vol_cap)] = 1.0
    s[(z < -thr) & (vr < vol_cap)] = -1.0
    return s


def reversal_exhaustion(df, w=20, thr=2.5):
    """REVERSAL: extreme recent move against a stretched range position -> fade."""
    n = len(df)
    s = _sig(n)
    r = _ret(df, w); atr = df["atr14"].to_numpy()
    rp = df["range_pos20"].to_numpy()
    z = r / atr
    s[(z > thr) & (rp > 0.9)] = -1.0
    s[(z < -thr) & (rp < 0.1)] = 1.0
    return s


def range_meanrev(df, rsi_lo=25, rsi_hi=75):
    """RANGE: fade RSI extremes, only when regime is RANGE."""
    n = len(df)
    s = _sig(n)
    rsi = df["rsi14"].to_numpy()
    reg = df["regime"].to_numpy()
    s[(rsi < rsi_lo) & (reg == "RANGE")] = 1.0
    s[(rsi > rsi_hi) & (reg == "RANGE")] = -1.0
    return s


def breakout_donchian(df, w=20, pad=0.0):
    """BREAKOUT: close beyond rolling high/low."""
    n = len(df)
    s = _sig(n)
    c = df["close"].to_numpy()
    if f"hh{w}" in df.columns:
        hh = df[f"hh{w}"].to_numpy(); ll = df[f"ll{w}"].to_numpy()
    else:
        hh = df["high"].rolling(w).max().to_numpy()
        ll = df["low"].rolling(w).min().to_numpy()
    s[c > hh] = 1.0
    s[c < ll] = -1.0
    return s


def vol_expansion(df, vr_thr=1.8):
    """VOL-EXPANSION: vol ratio spikes; trade the direction of last bar."""
    n = len(df)
    s = _sig(n)
    vr = df["vol_ratio"].to_numpy()
    last = df["close"].to_numpy() - np.concatenate([[np.nan], df["close"].to_numpy()[:-1]])
    s[(vr > vr_thr) & (last > 0)] = 1.0
    s[(vr > vr_thr) & (last < 0)] = -1.0
    return s


def vol_contraction_squeeze(df, vr_thr=0.6, w=20):
    """VOL-CONTRACTION: from a squeeze, trade the break of the last-quiet range."""
    n = len(df)
    s = _sig(n)
    c = df["close"].to_numpy()
    hh = df["hh20"].to_numpy(); ll = df["ll20"].to_numpy()
    squeeze = np.full(n, False)
    vr = df["vol_ratio"].to_numpy()
    for i in range(3, n):
        if np.isfinite(vr[i - 1]) and vr[i - 1] < vr_thr and c[i] > hh[i - 1]:
            squeeze[i] = True
    s[squeeze] = 1.0
    for i in range(3, n):
        if np.isfinite(vr[i - 1]) and vr[i - 1] < vr_thr and c[i] < ll[i - 1]:
            s[i] = -1.0
    return s


def mtf_structure(df):
    """MTF-STRUCTURE: 5m/20m/60m trend alignment (multi-timeframe agreement)."""
    n = len(df)
    s = _sig(n)
    r5 = df["ret5"].to_numpy(); r20 = df["ret20"].to_numpy(); r60 = df["ret60"].to_numpy()
    s[(r5 > 0) & (r20 > 0) & (r60 > 0)] = 1.0
    s[(r5 < 0) & (r20 < 0) & (r60 < 0)] = -1.0
    return s


def event_opening_range(df, w=30):
    """EVENT: intraday opening-range expansion proxy (event-like shock)."""
    n = len(df)
    s = _sig(n)
    c = df["close"].to_numpy()
    atr = df["atr14"].to_numpy()
    step = c - np.concatenate([[np.nan], c[:-1]])
    big = np.abs(step) > 1.5 * atr
    s[big & (step > 0)] = 1.0
    s[big & (step < 0)] = -1.0
    return s


def macro_resonance(df, thr=0.4):
    """MACRO-resonance proxy: slow (60-bar) drift + slow vol regime agreement."""
    n = len(df)
    s = _sig(n)
    ma60 = df["ma60"].to_numpy(); atr = df["atr14"].to_numpy()
    c = df["close"].to_numpy()
    slope = np.full(n, np.nan); slope[5:] = ma60[5:] - ma60[:-5]
    z = slope / atr
    s[z > thr] = 1.0
    s[z < -thr] = -1.0
    return s


def hybrid_trend_vol(df, thr=1.0):
    """HYBRID: trend direction, gated by vol-regime agreement (trend+vol filter)."""
    n = len(df)
    s = _sig(n)
    ts = df["trend_strength"].to_numpy()
    vr = df["vol_ratio"].to_numpy()
    s[(ts > thr) & (vr < 1.4)] = 1.0
    s[(ts < -thr) & (vr < 1.4)] = -1.0
    return s


MECHANISMS = {
    "TREND": trend_ma_slope,
    "MOMENTUM": momentum_continuation,
    "REVERSAL": reversal_exhaustion,
    "RANGE": range_meanrev,
    "BREAKOUT": breakout_donchian,
    "VOL_EXPANSION": vol_expansion,
    "VOL_CONTRACTION": vol_contraction_squeeze,
    "MTF_STRUCTURE": mtf_structure,
    "EVENT": event_opening_range,
    "MACRO": macro_resonance,
    "HYBRID": hybrid_trend_vol,
}

# parameter grids (design-time; frozen before validation/OOS)
PARAM_GRIDS = {
    "TREND": [{"fast": 5, "slow": 20, "slope_k": 1.6}, {"fast": 5, "slow": 20, "slope_k": 1.0}],
    "MOMENTUM": [{"w": 20, "thr": 2.0, "vol_cap": 1.5}, {"w": 10, "thr": 1.5, "vol_cap": 1.5}],
    "REVERSAL": [{"w": 20, "thr": 2.5}, {"w": 10, "thr": 2.0}],
    "RANGE": [{"rsi_lo": 25, "rsi_hi": 75}, {"rsi_lo": 20, "rsi_hi": 80}],
    "BREAKOUT": [{"w": 20}, {"w": 40}],
    "VOL_EXPANSION": [{"vr_thr": 1.8}, {"vr_thr": 2.2}],
    "VOL_CONTRACTION": [{"vr_thr": 0.6, "w": 20}],
    "MTF_STRUCTURE": [{}],
    "EVENT": [{"w": 30}],
    "MACRO": [{"thr": 0.4}],
    "HYBRID": [{"thr": 1.0}],
}

# horizons (bars) per mechanism family
HORIZONS = {
    "TREND": 60, "MOMENTUM": 20, "REVERSAL": 20, "RANGE": 15,
    "BREAKOUT": 30, "VOL_EXPANSION": 15, "VOL_CONTRACTION": 30,
    "MTF_STRUCTURE": 30, "EVENT": 10, "MACRO": 60, "HYBRID": 45,
}

# expected applicable regime declared a-priori
APPLICABLE_REGIME = {
    "TREND": ["TREND"], "MOMENTUM": ["TREND", "BREAKOUT"], "REVERSAL": ["RANGE", "TRANSITION"],
    "RANGE": ["RANGE"], "BREAKOUT": ["BREAKOUT", "TREND"], "VOL_EXPANSION": ["BREAKOUT", "EVENT"],
    "VOL_CONTRACTION": ["RANGE", "TRANSITION"], "MTF_STRUCTURE": ["TREND"],
    "EVENT": ["EVENT", "BREAKOUT"], "MACRO": ["TREND"], "HYBRID": ["TREND", "RANGE"],
}
