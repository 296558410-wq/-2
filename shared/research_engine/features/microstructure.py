# -*- coding: utf-8 -*-
"""features/microstructure.py — 微观结构特征（§5 placeholder→ 轻量真实实现）。

接口（未来可替换为真实 tick 数据源）：
  TickMicrostructure: 统一的 tick→bar 聚合接口。
轻量实现基于合成/真实 tick 数据（bid/ask/spread/volume/buy_volume）。
时间对齐：bar t 的特征只聚合 [T_t-1min, T_t) 区间内的 tick（即 bar t 收盘前已发生）。
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd


def bar_spread(bars: pd.DataFrame) -> pd.Series:
    """若 bars 已含 spread_mean（bar 级聚合），直接输出（单位：价格）。"""
    if "spread_mean" in bars.columns:
        return bars["spread_mean"].rename("bar_spread")
    raise ValueError("bars 需要 spread_mean 列（由 tick 聚合）")


def tick_volume(bars: pd.DataFrame) -> pd.Series:
    if "tick_count" in bars.columns:
        return bars["tick_count"].rename("tick_count")
    if "volume" in bars.columns:
        return bars["volume"].rename("bar_volume")
    raise ValueError("bars 需要 volume/tick_count 列")


def buy_volume(bars: pd.DataFrame) -> pd.Series:
    if "buy_volume" in bars.columns:
        return bars["buy_volume"].rename("bar_buy_volume")
    raise ValueError("bars 需要 buy_volume 列（由 tick 聚合）")


def imbalance(bars: pd.DataFrame) -> pd.Series:
    """买方成交量占比 − 0.5（订单流不平衡代理，[-0.5, 0.5]）。"""
    if "buy_volume" in bars.columns and "volume" in bars.columns:
        v = bars["volume"].replace(0, np.nan)
        return ((bars["buy_volume"] / v) - 0.5).rename("bar_imbalance")
    raise ValueError("bars 需要 buy_volume 与 volume 列")


class TickMicrostructure(ABC):
    """tick → M1 bar 微观结构特征接口。实现类只需提供 _aggregate(tick_df)。"""

    @abstractmethod
    def _aggregate(self, ticks: pd.DataFrame) -> pd.DataFrame:
        """输入 tick（ts_utc 索引/列，含 bid/ask/volume/buy_volume），输出 bar 级 DataFrame。"""

    def compute(self, ticks: pd.DataFrame, rule: str = "1min") -> pd.DataFrame:
        df = ticks.copy()
        if "ts_utc" in df.columns:
            df = df.set_index("ts_utc")
        df = df.sort_index()
        bars = self._aggregate(df, rule)
        return bars


class SimpleTickMicrostructure(TickMicrostructure):
    """轻量实现：把 tick 聚合成 bar 级 spread/volume/imbalance（用于合成数据与联调）。"""

    def _aggregate(self, df: pd.DataFrame, rule: str = "1min") -> pd.DataFrame:
        g = df.groupby(pd.Grouper(freq=rule))
        out = pd.DataFrame({
            "spread_mean": g["spread"].mean(),
            "tick_count": g["spread"].count(),
            "volume": g["volume"].sum(),
            "buy_volume": g["buy_volume"].sum() if "buy_volume" in df.columns else np.nan,
        }).dropna(subset=["tick_count"])
        return out
