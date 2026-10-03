# -*- coding: utf-8 -*-
"""features/labels.py — Label 引擎（§6）。

严格约定：label(t) 只使用 ts > t 的 bar（shift(-h) / 未来窗口），
绝不使用 t 及之前的任何未来信息。
forward_return_h:   close(t+h)/close(t) − 1
direction_15m:      sign(forward_return_15m)
future_volatility_h: (t, t+h] 区间 M1 收益的已实现波动率
mfe_h / mae_h:      未来 h 根 bar 的 high/low 相对 close(t) 的最大有利/不利偏移
                     （路径极端值，仅用于评估入口质量，不做交易信号）
"""
from __future__ import annotations

import numpy as np
import pandas as pd

_HORIZONS = (5, 15, 30, 60, 240)


def add_forward_labels(bars: pd.DataFrame, horizons=_HORIZONS,
                       vol_horizon: int = 60) -> pd.DataFrame:
    """返回 labels DataFrame（索引与 bars 对齐）。"""
    b = bars.set_index("ts_utc") if "ts_utc" in bars.columns else bars
    close = b["close"]
    out = pd.DataFrame(index=b.index)
    for h in horizons:
        out[f"forward_return_{h}m"] = close.shift(-h) / close - 1.0
    out["direction_15m"] = np.sign(out["forward_return_15m"])
    # 未来波动率（严格未来：滚动窗在 t+h 计算，覆盖 (t, t+h]）
    r = close.pct_change()
    out[f"future_vol_{vol_horizon}m"] = r.rolling(vol_horizon).std(ddof=1).shift(-vol_horizon)
    # MFE / MAE（未来 h 根 bar 内的高/低 vs 当前 close）
    hi = b["high"]
    lo = b["low"]
    h = 60
    out["mfe_60m"] = hi.rolling(h).max().shift(-h) / close - 1.0
    out["mae_60m"] = lo.rolling(h).min().shift(-h) / close - 1.0
    return out


def future_volatility(bars: pd.DataFrame, horizon: int = 60) -> pd.Series:
    """未来 horizon 根 bar 的收益标准差（严格未来，滚动窗 shift(-h)）。"""
    b = bars.set_index("ts_utc") if "ts_utc" in bars.columns else bars
    r = b["close"].pct_change()
    return r.rolling(horizon).std(ddof=1).shift(-horizon).rename(f"future_vol_{horizon}m")


def mfe_mae(bars: pd.DataFrame, horizon: int = 60) -> pd.DataFrame:
    """未来路径极值（相对当前收盘），严格未来。"""
    b = bars.set_index("ts_utc") if "ts_utc" in bars.columns else bars
    hi = b["high"].rolling(horizon).max().shift(-horizon)
    lo = b["low"].rolling(horizon).min().shift(-horizon)
    close = b["close"]
    return pd.DataFrame({"mfe": hi / close - 1.0, "mae": lo / close - 1.0})
