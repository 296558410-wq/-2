# -*- coding: utf-8 -*-
"""alpha_engine/generator.py — 特征/标签生成（对注册的真实数据）。

- 基础特征：features/xauusd CATALOG
- 派生特征（H7/H8/H9/H10）：mom_x_vol / trend_x_vol / x_compression / H1 状态 asof 映射
- 标签：forward_return_{h}m / future_vol_{h}m（严格未来，shift(-h)）
- 输出与 bars 严格同长度对齐（返回 (X_df, y_df, meta)）
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research_engine.core.feature import FeatureSpec, build as build_features
from research_engine.features.xauusd import CATALOG


def compute_feature(name: str, bars: pd.DataFrame, params: dict | None = None) -> pd.Series:
    params = params or {}
    func, defaults = CATALOG[name]
    merged = {**defaults, **params}
    return func(bars, **merged)


def compute_derived(name: str, bars: pd.DataFrame, X: pd.DataFrame) -> pd.Series:
    """派生/交互特征。命名约定见 hypothesis.py。"""
    if name == "mom_10_x_vol30":
        return (X["mom_10"] * X["vol_30"].rank(pct=True)).rename(name)
    if name == "mom_60_x_vol30":
        return (X["mom_60"] * X["vol_30"].rank(pct=True)).rename(name)
    if name == "trend_str_x_vol30":
        return (X["trend_str"] * X["vol_30"].rank(pct=True)).rename(name)
    if name == "mom_10_x_compression":
        return (X["mom_10"] * X["compression_60"]).rename(name)
    if name == "mom_60_x_compression":
        return (X["mom_60"] * X["compression_60"]).rename(name)
    raise KeyError(f"未知派生特征: {name}")


def add_h1_state(m1: pd.DataFrame, h1: pd.DataFrame) -> pd.DataFrame:
    """把 H1 状态 asof 映射到 M1（每个 M1 bar 使用 ≤t 的最新已收盘 H1 bar）。"""
    h1 = h1.sort_values("ts_utc").set_index("ts_utc")
    m1 = m1.sort_values("ts_utc")
    h1_c = h1["close"]
    h1_ret4 = h1_c / h1_c.shift(4) - 1.0
    h1_vol = h1_c.pct_change().rolling(24).std(ddof=1)
    h1_hi = h1["high"].shift(1).rolling(4).max()
    h1_lo = h1["low"].shift(1).rolling(4).min()
    state = pd.DataFrame({
        "h1_mom_4": h1_ret4,
        "h1_vol_ratio": h1_c.pct_change().rolling(4).std(ddof=1) / h1_vol,
        "h1_breakout": np.where(h1_c > h1_hi, 1.0, np.where(h1_c < h1_lo, -1.0, 0.0)),
    })
    # asof 映射前先做“可用性延迟”：H1 bar ts=t 要到 t+1h 才收盘 → 决策时刻只能用
    # 已收盘 H1 bar（index+1h 后再 ffill）。修复 lookahead（2026-09-04 第二轮发现：
    # 未延迟时 H10 IC≈0.25 系未来泄漏，延迟后应大幅回落）。
    known = state.copy()
    known.index = known.index + pd.Timedelta(hours=1)
    idx = m1["ts_utc"]
    mapped = known.reindex(known.index.union(idx)).ffill().reindex(idx)
    return mapped


def build_matrix(m1: pd.DataFrame, h1: pd.DataFrame | None = None,
                 base_features: list[str] | None = None) -> tuple[pd.DataFrame, dict]:
    """计算基础特征 + 派生特征；返回 (X, {name: lookback})。"""
    base = base_features or _needed_base()
    specs = []
    for n in base:
        func, defaults = CATALOG[n]
        specs.append(FeatureSpec(n, func, defaults))
    fm = build_features(m1, specs)
    X = fm.X
    lookbacks = {s.name: s.effective_lookback() for s in fm.specs}
    # 派生
    for n in ("mom_10_x_vol30", "mom_60_x_vol30", "trend_str_x_vol30",
              "mom_10_x_compression", "mom_60_x_compression"):
        if n == "mom_10_x_vol30" and "mom_10" in X and "vol_30" in X:
            X[n] = compute_derived(n, m1, X)
            lookbacks[n] = max(lookbacks["mom_10"], lookbacks["vol_30"])
        elif n == "mom_60_x_vol30" and "mom_60" in X and "vol_30" in X:
            X[n] = compute_derived(n, m1, X)
            lookbacks[n] = max(lookbacks["mom_60"], lookbacks["vol_30"])
        elif n == "trend_str_x_vol30" and "trend_str" in X and "vol_30" in X:
            X[n] = compute_derived(n, m1, X)
            lookbacks[n] = max(lookbacks["trend_str"], lookbacks["vol_30"])
        elif n == "mom_10_x_compression" and "mom_10" in X and "compression_60" in X:
            X[n] = compute_derived(n, m1, X)
            lookbacks[n] = max(lookbacks["mom_10"], lookbacks["compression_60"])
        elif n == "mom_60_x_compression" and "mom_60" in X and "compression_60" in X:
            X[n] = compute_derived(n, m1, X)
            lookbacks[n] = max(lookbacks["mom_60"], lookbacks["compression_60"])
    return X, lookbacks


def _needed_base() -> list[str]:
    return ["mom_5", "mom_10", "mom_20", "mom_60", "zscore_60", "dist_mean_60",
            "dist_ema_60", "breakout_60", "dist_hi_60", "dist_lo_60",
            "vol_30", "atr_14", "rvol_60", "vol_ratio_15_60", "vol_shock_5_60",
            "sma_dist_60", "ema_dist_60", "trend_str", "slope_60",
            "session_enc", "hour", "compression_60", "range_width_60",
            "ret_1", "logret_1", "range_1", "body_1", "wick_1", "close_pos_1"]


def add_labels(m1: pd.DataFrame, horizons=(5, 15, 30, 60, 240)) -> pd.DataFrame:
    bars = m1.set_index("ts_utc") if "ts_utc" in m1.columns else m1
    close = bars["close"]
    r = close.pct_change()
    out = pd.DataFrame(index=bars.index)
    for h in horizons:
        out[f"forward_return_{h}m"] = close.shift(-h) / close - 1.0
        out[f"future_vol_{h}m"] = r.rolling(h).std(ddof=1).shift(-h)
    return out
