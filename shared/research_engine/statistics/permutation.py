# -*- coding: utf-8 -*-
"""statistics/permutation.py — Permutation / 时间置换检验（§10）。

run_permutation: 符号翻转置换（H0: 均值=0），auto/cpu/gpu 统一入口。
time_permutation: 打乱时间顺序（破坏序列结构）后重估策略统计量 ——
  用于检测“时间结构/过拟合”是否贡献了结果。
"""
from __future__ import annotations

from typing import Callable, Optional

import numpy as np

from ..compute.dispatcher import run_permutation as _dispatch_permutation


def run_permutation(x, n_iter: int = 2000, backend: str = "auto", seed: int = 42) -> dict:
    return _dispatch_permutation(x, n_iter=n_iter, backend=backend, seed=seed)


def time_permutation(returns: np.ndarray, stat_fn: Callable[[np.ndarray], float],
                     n_iter: int = 2000, seed: int = 42) -> dict:
    """时间置换：随机循环平移 / 打乱收益序列，检验策略统计量是否依赖时间顺序。

    返回 {stat_obs, p_value, n_iter, dist_mean, dist_std}（双侧经验 p）。
    """
    rng = np.random.default_rng(seed)
    r = np.asarray(returns, dtype=float)
    obs = float(stat_fn(r))
    dist = np.empty(n_iter)
    for i in range(n_iter):
        perm = rng.permutation(r)
        dist[i] = stat_fn(perm)
    p = float((np.abs(dist) >= abs(obs)).mean())
    return {"stat_obs": obs, "p_value": p, "n_iter": n_iter,
            "dist_mean": float(dist.mean()), "dist_std": float(dist.std())}
