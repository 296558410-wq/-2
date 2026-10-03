# -*- coding: utf-8 -*-
"""validation/walk_forward.py — Rolling / Expanding Walk-Forward（§11）。

walk_forward_folds: 生成 (train_idx, test_idx) 折叠（支持 train/val/test 三段制：
  每次折叠前 min_train 根做 warmup，其后接 val 调参，最后为 OOS test）。
walk_forward_evaluate: 对固定信号（无拟合）在每折 OOS 段评估净收益与 Sharpe。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import pandas as pd

from ..core.backtest import compute_metrics


@dataclass
class WFFold:
    k: int
    train: slice
    val: slice
    test: slice


def walk_forward_folds(n: int, n_folds: int = 5, min_train: int = 300,
                       val_frac: float = 0.2, mode: str = "rolling",
                       embargo: int = 0) -> list[WFFold]:
    """train 比例随 fold 增长（expanding）或固定（rolling）；每折带 val 与 test。

    embargo: test 起点前额外剔除根 bar（避免近邻泄漏）。
    """
    if mode not in ("rolling", "expanding"):
        raise ValueError(mode)
    if n_folds < 1:
        raise ValueError("n_folds >= 1")
    usable = n - min_train
    if usable <= 0:
        raise ValueError("样本不足")
    test_len = usable // n_folds
    folds: list[WFFold] = []
    for k in range(n_folds):
        test_end = n if k == n_folds - 1 else min_train + (k + 1) * test_len
        test_start = min_train + k * test_len + embargo
        if test_start >= test_end:
            continue
        val_len = max(1, int((test_start - min_train) * val_frac))
        if mode == "expanding":
            tr_end = test_start - val_len - embargo
        else:
            tr_end = test_start - val_len - embargo
            tr_start = max(0, tr_end - (test_start - min_train))
        val_start = tr_end + embargo if mode == "expanding" else tr_end + embargo
        if tr_end <= 0:
            continue
        train = slice(0, tr_end) if mode == "expanding" else slice(tr_start, tr_end)
        folds.append(WFFold(k=k, train=train,
                            val=slice(val_start, val_start + val_len),
                            test=slice(test_start, test_end)))
    return folds


def walk_forward_evaluate(returns: np.ndarray, positions: np.ndarray,
                          folds: list[WFFold], one_way_cost: float = 0.0,
                          periods_per_year: float = 365 * 1440.0) -> dict:
    """对固定信号逐折 OOS 评估；one_way_cost>0 时按换手扣费。"""
    out = []
    for fold in folds:
        te = slice(fold.test.start + 1, fold.test.stop)  # 收益从第 2 根起算
        pos = positions[fold.test.start: fold.test.stop - 1]
        r = returns[te]
        if len(pos) != len(r):
            m = min(len(pos), len(r))
            pos, r = pos[:m], r[:m]
        gross = pos * r
        turnover = np.abs(np.diff(np.concatenate([[0.0], pos])))
        cost = turnover * one_way_cost
        net = gross - cost
        met = compute_metrics(net, gross, cost, pos, periods_per_year)
        out.append({"fold": fold.k, **{k: met[k] for k in
                     ("net_total_return", "sharpe_annualized", "max_drawdown", "n_trades", "n_bars")}})
    return {"n_folds": len(out), "folds": out,
            "oos_sharpe_mean": float(np.mean([f["sharpe_annualized"] for f in out])),
            "oos_positive_folds": int(sum(1 for f in out if f["sharpe_annualized"] > 0)),
            "oos_total_return": float(np.prod([1 + f["net_total_return"] for f in out]) - 1)}
