# -*- coding: utf-8 -*-
"""features/trend.py — 趋势特征（§5）。lookback = window（slope 同）。"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .price import returns


def sma(bars: pd.DataFrame, window: int = 60) -> pd.Series:
    c = bars["close"]
    return c.rolling(window).mean().rename(f"sma_{window}")


def ema(bars: pd.DataFrame, window: int = 60) -> pd.Series:
    c = bars["close"]
    return c.ewm(span=window, adjust=False, min_periods=window).mean().rename(f"ema_{window}")


def momentum(bars: pd.DataFrame, window: int = 30) -> pd.Series:
    """window 期动量（不含当前 bar 的收盘价信息使用：c(t)/c(t-window)-1）。"""
    c = bars["close"]
    return (c / c.shift(window) - 1.0).rename(f"mom_{window}")


def slope(bars: pd.DataFrame, window: int = 30) -> pd.Series:
    """收盘价对时间的最小二乘斜率（以 bar 数归一化 → 每 bar 的价格变化）。"""
    c = bars["close"]
    x = np.arange(window, dtype=float)
    xm = x.mean()
    denom = ((x - xm) ** 2).sum()

    def _slope(arr: np.ndarray) -> float:
        return float(np.sum((arr - arr.mean()) * (x - xm)) / denom)

    return c.rolling(window).apply(_slope, raw=True).rename(f"slope_{window}")


def fast_slow_ratio(bars: pd.DataFrame, fast: int = 15, slow: int = 60) -> pd.Series:
    """快/慢 EMA 比值 − 1（趋势强度代理，=0 无趋势）。lookback=slow。"""
    fe = ema(bars, fast)
    se = ema(bars, slow)
    return (fe / se - 1.0).rename(f"ema_ratio_{fast}_{slow}")
