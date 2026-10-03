# -*- coding: utf-8 -*-
"""validation — 样本切分 / Walk-Forward / Placebo / Cost-Stress（§11/§12/§15）。"""
import random

import numpy as np

from .split import time_split, purge_window, leakage_free_alignment
from .walk_forward import walk_forward_folds, walk_forward_evaluate
from .placebo import label_shuffle_test, run_label_shuffle
from .cost_stress import run_cost_stress

# ---- v0.1 兼容导出（旧 API 保留，新代码请用上面的名字） ----

def seed_all(seed: int = 42) -> None:
    """统一随机种子三件套。"""
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except Exception:
        pass


def permutation_test(strategy_returns, benchmark_returns=None, n_iter=2000, seed=42, stat="mean"):
    """兼容旧 API：符号翻转检验 → {stat_obs, p_value, n_iter, dist_mean, dist_std}。"""
    from ..statistics.permutation import run_permutation
    x = np.asarray(strategy_returns, dtype=float)
    if benchmark_returns is not None:
        x = x - np.asarray(benchmark_returns, dtype=float)
    r = run_permutation(x, n_iter=n_iter, seed=seed, backend="cpu")
    return {"stat_obs": r["stat_obs"], "p_value": r["p_value_two_sided"],
            "n_iter": r["n_iter"], "dist_mean": r["dist_mean"], "dist_std": r["dist_std"]}


def shuffle_test(signal, forward_returns, n_iter=2000, seed=42, stat_fn=None):
    """兼容旧 API：label shuffle → {stat_obs, p_value, n_iter, dist_mean, dist_std}。"""
    if stat_fn is None:
        stat_fn = lambda s, r: float(np.mean(s * r))
    from .placebo import label_shuffle_test as _lst
    return _lst(np.asarray(signal), np.asarray(forward_returns), n_iter, seed, stat_fn)


def benjamini_hochberg(p_values, alpha: float = 0.05):
    from ..statistics.multiple_testing import benjamini_hochberg as _bh
    return _bh(p_values, alpha=alpha)


def walk_forward_splits(n: int, n_splits: int = 5, min_train: int = 200, mode: str = "expanding"):
    """兼容旧 API：返回 list[(train_idx, test_idx)]（numpy 数组）。"""
    folds = walk_forward_folds(n, n_folds=n_splits, min_train=min_train,
                               val_frac=0.0, mode=mode, embargo=0)
    return [(np.arange(f.train.start, f.train.stop), np.arange(f.test.start, f.test.stop))
            for f in folds if f.test.stop > f.test.start]


__all__ = ["time_split", "purge_window", "leakage_free_alignment",
           "walk_forward_folds", "walk_forward_evaluate",
           "label_shuffle_test", "run_label_shuffle", "run_cost_stress",
           "seed_all", "permutation_test", "shuffle_test",
           "benjamini_hochberg", "walk_forward_splits"]
