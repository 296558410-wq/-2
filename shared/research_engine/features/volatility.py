# -*- coding: utf-8 -*-
"""features/volatility.py — 波动率特征（§5）。

所有滚动窗口以 lookback 个已完成 bar 计算（含当前 bar，即 t 时刻信息）；
窗口滚动均不越过 t。lookback = window。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .price import returns


def _ret(bars: pd.DataFrame) -> pd.Series:
    return returns(bars).dropna()


def rolling_std(bars: pd.DataFrame, window: int = 30) -> pd.Series:
    """窗口内简单收益的滚动标准差（样本）。"""
    r = _ret(bars)
    return r.rolling(window).std(ddof=1).rename(f"roll_std_{window}")


def atr(bars: pd.DataFrame, window: int = 14) -> pd.Series:
    """平均真实波幅（Wilder 简化版：rolling mean of TR / prev_close）。"""
    b = bars
    pc = b["close"].shift(1)
    tr = pd.concat([(b["high"] - b["low"]), (b["high"] - pc).abs(), (b["low"] - pc).abs()], axis=1).max(axis=1)
    return (tr.rolling(window).mean() / pc).rename(f"atr_{window}")


def realised_vol(bars: pd.DataFrame, window: int = 60, annualize: bool = False) -> pd.Series:
    """已实现波动率 = 窗口内收益标准差；annualize=True 时按 M1 bar 年化。"""
    r = _ret(bars)
    out = r.rolling(window).std(ddof=1)
    if annualize:
        out = out * np.sqrt(365 * 1440)
    return out.rename(f"realised_vol_{window}")


def volatility_ratio(bars: pd.DataFrame, short: int = 15, long: int = 120) -> pd.Series:
    """短/长窗波动率比（>1 表示波动扩张）。"""
    s = _ret(bars).rolling(short).std(ddof=1)
    l = _ret(bars).rolling(long).std(ddof=1)
    return (s / l).rename(f"vol_ratio_{short}_{long}")
