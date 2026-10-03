# -*- coding: utf-8 -*-
"""core/signal.py — 信号层（§5 信号产生）。

约定：信号在 bar t 收盘时（ts_utc = close 时刻）产生，只依赖 ≤t 特征。
position(t) ∈ [-1,1] 表示 t+1 起的持仓（由 backtest 负责滞后执行）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd


@dataclass
class SignalResult:
    positions: pd.Series            # index=ts_utc；t 时刻值 = t+1 生效的持仓
    name: str
    params: dict

    @property
    def n_trades(self) -> int:
        """含初始入场的换手次数（与回测换手口径一致：从 0 起步）。"""
        p = self.positions.fillna(0.0).values
        return int((np.diff(np.concatenate([[0.0], p])) != 0).sum())


def positions_from_thresholds(x: pd.Series, long_th: float = 0.0,
                              short_th: float = 0.0, max_pos: float = 1.0) -> pd.Series:
    """x>long_th → +max_pos；x<short_th → -max_pos；其余 0。"""
    x = x.astype(float)
    pos = pd.Series(np.zeros(len(x)), index=x.index, dtype=float)
    pos[x > long_th] = max_pos
    pos[x < short_th] = -max_pos
    return pos


def positions_from_sign(x: pd.Series, max_pos: float = 1.0) -> pd.Series:
    pos = np.sign(x.fillna(0.0)) * max_pos
    return pd.Series(pos, index=x.index)


def make_signal(feature_series: pd.Series, rule: str = "threshold",
                long_th: float = 0.0, short_th: float = 0.0,
                max_pos: float = 1.0) -> SignalResult:
    """从单一特征序列生成信号。rule: threshold | sign"""
    if rule == "threshold":
        pos = positions_from_thresholds(feature_series, long_th, short_th, max_pos)
    elif rule == "sign":
        pos = positions_from_sign(feature_series, max_pos)
    else:
        raise ValueError(f"rule={rule}")
    return SignalResult(positions=pos, name=f"{feature_series.name or 'feat'}_{rule}",
                        params={"rule": rule, "long_th": long_th,
                                "short_th": short_th, "max_pos": max_pos})
