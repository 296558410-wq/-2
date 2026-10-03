# -*- coding: utf-8 -*-
"""features — 特征与标签引擎（§5/§6）。

对齐纪律（框架级约定，禁止 look-ahead）：
  * 输入：M1 bars DataFrame，索引/列为 ts_utc（UTC，bar 收盘时刻）
  * 特征 f(t) 只使用 ts ≤ t 的已收盘 bar
  * 标签 L(t) 只使用 ts > t 的未来 bar（严格未来）
  * 每个特征声明 lookback（所需历史 bar 数），管线据此丢弃头部不完整区段
"""
from .price import returns, log_returns, bar_range, body, upper_wick, lower_wick
from .volatility import rolling_std, atr, realised_vol, volatility_ratio
from .trend import sma, ema, momentum, slope
from .microstructure import bar_spread, tick_volume, buy_volume, imbalance, TickMicrostructure
from .labels import add_forward_labels, future_volatility, mfe_mae

FEATURE_LOOKBACKS = {
    "returns": 1, "log_returns": 1, "bar_range": 1, "body": 1,
    "upper_wick": 1, "lower_wick": 1,
    "rolling_std": None, "atr": None, "realised_vol": None, "volatility_ratio": None,
    "sma": None, "ema": None, "momentum": None, "slope": None,
}

__all__ = [
    "returns", "log_returns", "bar_range", "body", "upper_wick", "lower_wick",
    "rolling_std", "atr", "realised_vol", "volatility_ratio",
    "sma", "ema", "momentum", "slope",
    "bar_spread", "tick_volume", "buy_volume", "imbalance", "TickMicrostructure",
    "add_forward_labels", "future_volatility", "mfe_mae", "FEATURE_LOOKBACKS",
]
