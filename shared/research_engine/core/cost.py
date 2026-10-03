# -*- coding: utf-8 -*-
"""core/cost.py — 成本模型（§12）。

支持 spread / commission / slippage，单边成本（以价格 bp 计）：
  one_way_bps = spread/2 + commission + slippage
乘子 1x/2x/3x：cost_stress 通过 multiplier 整体放大成本。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class CostModel:
    spread_bps: float = 0.9       # 全点差（bp）
    commission_bps: float = 0.35  # 单边佣金（bp）
    slippage_bps: float = 0.2     # 单边滑点（bp）

    @property
    def one_way_bps(self) -> float:
        return self.spread_bps / 2.0 + self.commission_bps + self.slippage_bps

    @property
    def one_way_cost(self) -> float:
        """单边换手成本（收益单位，即 bps/10000）。"""
        return self.one_way_bps / 10000.0

    def cost_series(self, turnover: pd.Series, multiplier: float = 1.0) -> pd.Series:
        """turnover = |Δposition|（每次换手按单边成本计）。"""
        return turnover * self.one_way_cost * multiplier

    def round_trip_bps(self) -> float:
        return 2.0 * self.one_way_bps

    def to_dict(self) -> dict:
        return {"spread_bps": self.spread_bps, "commission_bps": self.commission_bps,
                "slippage_bps": self.slippage_bps, "one_way_bps": round(self.one_way_bps, 4),
                "one_way_cost": round(self.one_way_cost, 8)}
