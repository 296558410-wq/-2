# -*- coding: utf-8 -*-
"""statistics/bootstrap.py — Bootstrap 置信区间（§10）。

run_bootstrap：统一 auto/cpu/gpu（经 compute.dispatcher，记录后端与耗时）。
bootstrap_ci：对任意统计量做 bootstrap 百分位 CI / 基本 CI（numpy，CPU）。
"""
from __future__ import annotations

from typing import Callable, Optional

import numpy as np

from ..compute.dispatcher import run_bootstrap as _dispatch_bootstrap


def bootstrap_ci(x: np.ndarray, stat_fn: Callable[[np.ndarray], float],
                 n_iter: int = 5000, seed: int = 42, alpha: float = 0.05,
                 ci_method: str = "percentile") -> dict:
    """对样本 x 的统计量 stat_fn 计算 bootstrap CI。

    ci_method: "percentile"（百分位）| "basic"（基本法 2θ̂-θ*）。
    返回 {est, ci_low, ci_high, dist_mean, dist_std, n_iter, method}。
    """
    rng = np.random.default_rng(seed)
    xa = np.asarray(x, dtype=float)
    n = len(xa)
    est = float(stat_fn(xa))
    idx = rng.integers(0, n, size=(n_iter, n))
    dist = np.array([stat_fn(xa[i]) for i in idx])
    lo, hi = 100.0 * alpha / 2.0, 100.0 * (1.0 - alpha / 2.0)
    if ci_method == "percentile":
        ci_low, ci_high = float(np.percentile(dist, lo)), float(np.percentile(dist, hi))
    elif ci_method == "basic":
        ci_low, ci_high = 2 * est - float(np.percentile(dist, hi)), 2 * est - float(np.percentile(dist, lo))
    else:
        raise ValueError(f"ci_method={ci_method}")
    return {"est": est, "ci_low": ci_low, "ci_high": ci_high,
            "dist_mean": float(dist.mean()), "dist_std": float(dist.std()),
            "n_iter": n_iter, "method": ci_method, "alpha": alpha}


def run_bootstrap(x, n_iter: int = 2000, stat: str = "mean",
                  backend: str = "auto", seed: int = 42) -> dict:
    """统一 bootstrap（记录 backend/elapsed/seed）。stat: mean|std|median。"""
    return _dispatch_bootstrap(x, n_iter=n_iter, stat=stat, backend=backend, seed=seed)
