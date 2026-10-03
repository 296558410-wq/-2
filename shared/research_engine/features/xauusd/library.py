# -*- coding: utf-8 -*-
"""features/xauusd — 真实数据第一版特征库（Phase 2 §6）。

纪律（最高优先级）：
  * 所有特征在 bar t 收盘时刻决策，只用 ts ≤ t 的信息；
    需要“过去窗口极值”的地方一律 shift(1)（不把当前 bar high/low 泄漏进决策）
  * 每个特征声明 lookback（=所需历史 bar 数），管线据此丢头部并做截断重算验证
目录 CATALOG：{name: (func, default_params)}，generator 据此展开参数网格。
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _frame(bars: pd.DataFrame) -> pd.DataFrame:
    if "ts_utc" in bars.columns:
        return bars.set_index("ts_utc")
    return bars


# ---------------- Price ----------------
def returns(bars, window=1):
    c = _frame(bars)["close"]
    return (c / c.shift(window) - 1.0).rename(f"ret_{window}")


def log_returns(bars, window=1):
    c = _frame(bars)["close"]
    return np.log(c / c.shift(window)).rename(f"logret_{window}")


def bar_range(bars, window=1):
    """(high-low)/close 的 window 均值。"""
    f = _frame(bars)
    r = (f["high"] - f["low"]) / f["close"]
    return r.rolling(window).mean().rename(f"range_{window}")


def body(bars, window=1):
    f = _frame(bars)
    b = (f["close"] - f["open"]) / f["close"]
    return b.rolling(window).mean().rename(f"body_{window}")


def wick_ratio(bars, window=1):
    """上影+下影 / 全幅（window 均值）。"""
    f = _frame(bars)
    rng = (f["high"] - f["low"]).replace(0, np.nan)
    wick = ((f["high"] - f[["open", "close"]].max(axis=1)) +
            (f[["open", "close"]].min(axis=1) - f["low"]))
    return (wick / rng).rolling(window).mean().rename(f"wick_{window}")


def close_position(bars, window=1):
    """close 在 (low,high) 内的位置 ∈[0,1]（window 均值）。"""
    f = _frame(bars)
    rng = (f["high"] - f["low"]).replace(0, np.nan)
    cp = (f["close"] - f["low"]) / rng
    return cp.rolling(window).mean().rename(f"close_pos_{window}")


# ---------------- Momentum ----------------
def momentum(bars, window=5):
    c = _frame(bars)["close"]
    return (c / c.shift(window) - 1.0).rename(f"mom_{window}")


# ---------------- Trend ----------------
def sma_dist(bars, window=60):
    """close 相对 SMA 的偏离（%）。"""
    c = _frame(bars)["close"]
    sma = c.rolling(window).mean()
    return (c / sma - 1.0).rename(f"sma_dist_{window}")


def ema_dist(bars, window=60):
    c = _frame(bars)["close"]
    ema = c.ewm(span=window, adjust=False, min_periods=window).mean()
    return (c / ema - 1.0).rename(f"ema_dist_{window}")


def slope(bars, window=60):
    """收盘价线性回归斜率（%/bar，以 close 归一）。"""
    c = _frame(bars)["close"]
    x = np.arange(window, dtype=float)
    xm = x.mean()
    denom = ((x - xm) ** 2).sum()

    def _s(arr):
        return float(np.sum((arr - arr.mean()) * (x - xm)) / denom) / float(arr.mean())

    return c.rolling(window).apply(_s, raw=True).rename(f"slope_{window}")


def trend_strength(bars, fast=15, slow=60):
    """EMA(fast)/EMA(slow)−1 的绝对值归一化趋势强度（0~∞）。"""
    c = _frame(bars)["close"]
    fe = c.ewm(span=fast, adjust=False, min_periods=slow).mean()
    se = c.ewm(span=slow, adjust=False, min_periods=slow).mean()
    return (fe / se - 1.0).rename(f"trend_str_{fast}_{slow}")


# ---------------- Volatility ----------------
def rolling_vol(bars, window=30):
    r = _frame(bars)["close"].pct_change()
    return r.rolling(window).std(ddof=1).rename(f"vol_{window}")


def atr(bars, window=14):
    f = _frame(bars)
    pc = f["close"].shift(1)
    tr = pd.concat([(f["high"] - f["low"]), (f["high"] - pc).abs(), (f["low"] - pc).abs()], axis=1).max(axis=1)
    return (tr.rolling(window).mean() / pc).rename(f"atr_{window}")


def realised_vol(bars, window=60):
    r = _frame(bars)["close"].pct_change()
    return r.rolling(window).std(ddof=1).rename(f"rvol_{window}")


def vol_ratio(bars, short=15, long=60):
    r = _frame(bars)["close"].pct_change()
    s = r.rolling(short).std(ddof=1)
    l = r.rolling(long).std(ddof=1)
    return (s / l).rename(f"vol_ratio_{short}_{long}")


def volatility_shock(bars, short=5, long=60, th=3.0):
    """vol_ratio 超过历史分布 → 冲击强度（标准化）。"""
    r = _frame(bars)["close"].pct_change()
    s = r.rolling(short).std(ddof=1)
    l = r.rolling(long).std(ddof=1)
    vr = s / l
    mu = vr.rolling(long).mean()
    sd = vr.rolling(long).std(ddof=1)
    return ((vr - mu) / sd).rename(f"vol_shock_{short}_{long}")


# ---------------- Mean Reversion ----------------
def zscore(bars, window=60):
    c = _frame(bars)["close"]
    mu = c.rolling(window).mean()
    sd = c.rolling(window).std(ddof=1)
    return ((c - mu) / sd).rename(f"zscore_{window}")


def distance_from_mean(bars, window=60):
    return sma_dist(bars, window).rename(f"dist_mean_{window}")


def distance_from_ema(bars, window=60):
    return ema_dist(bars, window).rename(f"dist_ema_{window}")


# ---------------- Time ----------------
def hour(bars, window=1):
    return _frame(bars).index.hour.astype(float).rename("hour")


def minute(bars, window=1):
    return _frame(bars).index.minute.astype(float).rename("minute")


def session(bars, window=1):
    idx = _frame(bars).index
    h = idx.hour
    s = pd.Series(0.0, index=idx)
    s[(h >= 0) & (h < 7)] = 1.0    # asia
    s[(h >= 7) & (h < 12)] = 2.0   # london
    s[(h >= 12) & (h < 16)] = 3.0  # london/ny overlap
    s[(h >= 16) & (h < 21)] = 4.0  # ny
    return s.rename("session_enc")


def day_of_week(bars, window=1):
    return _frame(bars).index.dayofweek.astype(float).rename("dow")


# ---------------- Market Structure ----------------
def breakout(bars, window=60):
    """close 突破过去 window 根 bar 的最高价 → +1；跌破最低价 → -1；否则 0。
    关键：只用 shift(1) 之前的 high/low（决策在收盘，当前 bar 极值未知）。"""
    f = _frame(bars)
    prior_hi = f["high"].shift(1).rolling(window).max()
    prior_lo = f["low"].shift(1).rolling(window).min()
    out = pd.Series(0.0, index=f.index)
    out[f["close"] > prior_hi] = 1.0
    out[f["close"] < prior_lo] = -1.0
    return out.rename(f"breakout_{window}")


def range_width(bars, window=60):
    """过去 window 根 bar 的 (high-low)/close 均值（波动包络宽度）。"""
    f = _frame(bars)
    r = (f["high"] - f["low"]) / f["close"]
    return r.rolling(window).mean().rename(f"range_width_{window}")


def rolling_high_dist(bars, window=60):
    """close 距过去 window 高点的距离（<0 表示未创新高）。"""
    f = _frame(bars)
    prior_hi = f["high"].shift(1).rolling(window).max()
    return (f["close"] / prior_hi - 1.0).rename(f"dist_hi_{window}")


def rolling_low_dist(bars, window=60):
    f = _frame(bars)
    prior_lo = f["low"].shift(1).rolling(window).min()
    return (f["close"] / prior_lo - 1.0).rename(f"dist_lo_{window}")


def compression(bars, window=60):
    """当前 bar 振幅 / 过去 window 平均振幅（<1 = 压缩）。"""
    f = _frame(bars)
    cur = (f["high"] - f["low"]) / f["close"]
    avg = cur.rolling(window).mean()
    return (cur / avg).rename(f"compression_{window}")


# ---------------- Catalog（generator 展开用） ----------------
def _lb_from_params(params: dict) -> int:
    for key in ("window", "long", "slow"):
        if key in params:
            return int(params[key])
    return 1


CATALOG: dict[str, tuple] = {
    # name: (func, default_params)
    "ret_1": (returns, {"window": 1}),
    "logret_1": (log_returns, {"window": 1}),
    "range_1": (bar_range, {"window": 1}),
    "body_1": (body, {"window": 1}),
    "wick_1": (wick_ratio, {"window": 1}),
    "close_pos_1": (close_position, {"window": 1}),
    "mom_5": (momentum, {"window": 5}),
    "mom_10": (momentum, {"window": 10}),
    "mom_20": (momentum, {"window": 20}),
    "mom_60": (momentum, {"window": 60}),
    "sma_dist_60": (sma_dist, {"window": 60}),
    "ema_dist_60": (ema_dist, {"window": 60}),
    "slope_60": (slope, {"window": 60}),
    "trend_str": (trend_strength, {"fast": 15, "slow": 60}),
    "vol_30": (rolling_vol, {"window": 30}),
    "atr_14": (atr, {"window": 14}),
    "rvol_60": (realised_vol, {"window": 60}),
    "vol_ratio_15_60": (vol_ratio, {"short": 15, "long": 60}),
    "vol_shock_5_60": (volatility_shock, {"short": 5, "long": 60}),
    "zscore_60": (zscore, {"window": 60}),
    "dist_mean_60": (distance_from_mean, {"window": 60}),
    "dist_ema_60": (distance_from_ema, {"window": 60}),
    "hour": (hour, {}),
    "minute": (minute, {}),
    "session_enc": (session, {}),
    "dow": (day_of_week, {}),
    "breakout_60": (breakout, {"window": 60}),
    "range_width_60": (range_width, {"window": 60}),
    "dist_hi_60": (rolling_high_dist, {"window": 60}),
    "dist_lo_60": (rolling_low_dist, {"window": 60}),
    "compression_60": (compression, {"window": 60}),
}


def spec_lookback(name: str, params: dict) -> int:
    """由参数推导 lookback（时间类=0，窗口类=window）。"""
    if name in ("hour", "minute", "session_enc", "dow"):
        return 0
    return _lb_from_params(params)
