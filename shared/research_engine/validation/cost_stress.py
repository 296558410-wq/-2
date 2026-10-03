# -*- coding: utf-8 -*-
"""validation/cost_stress.py — 成本压力测试（§12）：1x/2x/3x 成本下指标。

输入：gross 收益序列与持仓序列；在多个成本倍率下输出净收益与 Sharpe。
"""
from __future__ import annotations

import numpy as np

from ..core.backtest import compute_metrics


def run_cost_stress(gross_returns: np.ndarray, positions: np.ndarray,
                    one_way_cost: float, multipliers=(1.0, 2.0, 3.0),
                    periods_per_year: float = 365 * 1440.0) -> dict:
    """gross_returns/positions 已按回测引擎约定对齐（pos 滞后一期）。"""
    gross = np.asarray(gross_returns, dtype=float)
    pos = np.asarray(positions, dtype=float)
    turnover = np.abs(np.diff(np.concatenate([[0.0], pos])))
    # 成本对齐：turnover[k] 发生在 pos[k-1]→pos[k]；gross[k] 对应 pos[k-1]*r[k]
    # 令 net[k] = gross[k] - cost[k-1]（执行于 k 开盘，与 gross 同期）
    out = {}
    for m in multipliers:
        cost = np.zeros_like(gross)
        cost[1:] = turnover[:-1] * one_way_cost * m
        net = gross - cost
        met = compute_metrics(net, gross, cost, pos, periods_per_year)
        out[f"{m:g}x"] = {k: met[k] for k in
                          ("gross_total_return", "net_total_return", "cost_total",
                           "sharpe_annualized", "max_drawdown", "profit_factor", "turnover_total")}
    out["_one_way_cost"] = one_way_cost
    return out
