# -*- coding: utf-8 -*-
"""core/backtest.py — 最小回测引擎（§13）。

时序约定（杜绝 look-ahead / same-bar cheating / future-close leakage）：
  * bars 按 ts_utc 升序；r[t] = close[t]/close[t-1] − 1（区间 (t-1, t] 的收益）
  * position[t]：在 close[t] 收盘时决定（只用 ≤t 信息）
  * 生效：position[t] 赚取 r[t+1]（即从 open[t+1]≈close[t] 开始持有）
  * 换手：|position[t] − position[t-1]| 在 t+1 开盘执行并计成本
  * signal timestamp = close[t]；execution timestamp = open[t+1]（文档明确记录）
输出：每 bar 明细 df + metrics。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from .cost import CostModel

PERIODS_PER_YEAR_M1 = 365 * 1440.0


def compute_metrics(net: np.ndarray, gross: np.ndarray, cost: np.ndarray,
                    positions: np.ndarray, periods_per_year: float = PERIODS_PER_YEAR_M1) -> dict:
    net = np.asarray(net, dtype=float)
    gross = np.asarray(gross, dtype=float)
    positions = np.asarray(positions, dtype=float)
    n = len(net)
    eq = np.cumprod(1.0 + net)
    peak = np.maximum.accumulate(eq)
    dd = eq / peak - 1.0
    active = np.abs(positions[:-1]) > 0 if n > 1 else np.zeros(0, dtype=bool)
    ar = net[1:] if n > 1 else net
    a_active = np.abs(positions[:-1]) > 1e-12
    win_r = ar[a_active]
    wins = win_r[win_r > 0].sum()
    losses = -win_r[win_r < 0].sum()
    sd = net.std(ddof=1) if n > 2 else 0.0
    sharpe = float(net.mean() / sd * np.sqrt(periods_per_year)) if sd > 0 else 0.0
    return {
        "gross_total_return": float(np.prod(1 + gross) - 1) if n else 0.0,
        "net_total_return": float(np.prod(1 + net) - 1) if n else 0.0,
        "cost_total": float(cost.sum()),
        "sharpe_annualized": round(sharpe, 4),
        "max_drawdown": float(dd.min()) if n else 0.0,
        "win_rate": float((win_r > 0).mean()) if len(win_r) else 0.0,
        "profit_factor": float(wins / losses) if losses > 1e-15 else (float("inf") if wins > 0 else 0.0),
        "turnover_total": float(np.abs(np.diff(np.concatenate([[0.0], positions]))).sum()),
        "n_bars": int(n),
        "n_trades": int((np.diff(np.concatenate([[0.0], positions])) != 0).sum()),
        "mean_net": float(net.mean()) if n else 0.0,
    }


@dataclass
class BacktestResult:
    name: str
    df: pd.DataFrame                    # 每 bar 明细
    metrics: dict
    config: dict = field(default_factory=dict)

    def metrics_json(self) -> dict:
        return {"name": self.name, **self.metrics, "config": self.config}


class BacktestEngine:
    def __init__(self, cost_model: Optional[CostModel] = None,
                 periods_per_year: float = PERIODS_PER_YEAR_M1):
        self.cost_model = cost_model or CostModel()
        self.ppy = periods_per_year

    def run(self, close: pd.Series, position: pd.Series,
            cost_multiplier: float = 1.0, name: str = "bt") -> BacktestResult:
        """close/position 需同一索引（ts_utc 升序）。position[t] 在 close[t] 决定。"""
        df = pd.DataFrame({"close": close.astype(float), "position": position.astype(float)})
        df = df.dropna(subset=["close"]).sort_index()
        df["position"] = df["position"].fillna(0.0).clip(-1.0, 1.0)
        df["r"] = df["close"].pct_change().fillna(0.0)
        # 生效收益：pos[t-1] * r[t]（首行 pos 前值视为 0 → gross=0）
        df["gross_r"] = df["position"].shift(1).fillna(0.0) * df["r"]
        df["turnover"] = (df["position"].shift(1) - df["position"].shift(2)).abs().fillna(df["position"].shift(1).abs().fillna(0.0))
        df["cost_r"] = self.cost_model.cost_series(df["turnover"], multiplier=cost_multiplier)
        df["net_r"] = df["gross_r"] - df["cost_r"]
        eq = np.cumprod(1.0 + df["net_r"].values)
        df["equity_net"] = eq
        df["equity_gross"] = np.cumprod(1.0 + df["gross_r"].values)
        metrics = compute_metrics(df["net_r"].values, df["gross_r"].values,
                                  df["cost_r"].values, df["position"].values, self.ppy)
        config = {"cost_model": self.cost_model.to_dict(),
                  "cost_multiplier": cost_multiplier,
                  "periods_per_year": self.ppy,
                  "convention": "signal@close[t] -> position effective from t+1 open; turnover cost at t+1",
                  "signal_timestamp": "bar close", "execution_timestamp": "next bar open"}
        return BacktestResult(name=name, df=df, metrics=metrics, config=config)
