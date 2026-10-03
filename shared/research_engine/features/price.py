# -*- coding: utf-8 -*-
"""features/price.py — 价格类特征（§5）。

约定：输入 bars 必须含 open/high/low/close；返回与输入等长、索引一致的 Series。
lookback：本文件全部为单 bar 特征，lookback=1（当前 bar 收盘后才可知）。
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _req(bars: pd.DataFrame) -> pd.DataFrame:
    need = {"open", "high", "low", "close"}
    miss = need - set(bars.columns)
    if miss:
        raise ValueError(f"bars 缺少列: {miss}")
    return bars


def returns(bars: pd.DataFrame) -> pd.Series:
    """close-to-close 简单收益。"""
    b = _req(bars)
    return b["close"].pct_change().rename("return_1m")


def log_returns(bars: pd.DataFrame) -> pd.Series:
    b = _req(bars)
    return np.log(b["close"] / b["close"].shift(1)).rename("log_return_1m")


def bar_range(bars: pd.DataFrame) -> pd.Series:
    """(high - low) / prev_close —— 波动宽度（单位收益）。"""
    b = _req(bars)
    return ((b["high"] - b["low"]) / b["close"].shift(1)).rename("range_1m")


def body(bars: pd.DataFrame) -> pd.Series:
    """(close - open) / prev_close。"""
    b = _req(bars)
    return ((b["close"] - b["open"]) / b["close"].shift(1)).rename("body_1m")


def upper_wick(bars: pd.DataFrame) -> pd.Series:
    b = _req(bars)
    return ((b["high"] - np.maximum(b["open"], b["close"])) / b["close"].shift(1)).rename("upper_wick_1m")


def lower_wick(bars: pd.DataFrame) -> pd.Series:
    b = _req(bars)
    return ((np.minimum(b["open"], b["close"]) - b["low"]) / b["close"].shift(1)).rename("lower_wick_1m")
