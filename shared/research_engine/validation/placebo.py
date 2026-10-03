# -*- coding: utf-8 -*-
"""validation/placebo.py — Placebo / Shuffle / Label Shuffle 检验（§10/§15）。

label_shuffle_test: 打乱 label 与特征对应关系（破坏任何真实关系）后重估
  策略统计量 → 经验 p 值。若随机数据常得漂亮 Sharpe → 框架有泄漏，须停下检查。
"""
from __future__ import annotations

from typing import Callable

import numpy as np


def _default_stat(signal: np.ndarray, fwd: np.ndarray) -> float:
    return float(np.mean(signal * fwd))


def label_shuffle_test(signal: np.ndarray, forward: np.ndarray,
                       n_iter: int = 2000, seed: int = 42,
                       stat_fn: Callable = _default_stat) -> dict:
    """打乱 forward（label）与 signal 的对齐 → 零假设分布。双侧经验 p。"""
    rng = np.random.default_rng(seed)
    signal = np.asarray(signal, dtype=float)
    fwd = np.asarray(forward, dtype=float)
    if len(signal) != len(fwd):
        raise ValueError("signal 与 forward 长度不一致")
    obs = float(stat_fn(signal, fwd))
    dist = np.empty(n_iter)
    for i in range(n_iter):
        perm = rng.permutation(fwd)
        dist[i] = stat_fn(signal, perm)
    return {"stat_obs": obs, "p_value": float((np.abs(dist) >= abs(obs)).mean()),
            "n_iter": n_iter, "dist_mean": float(dist.mean()),
            "dist_std": float(dist.std()), "test": "label_shuffle"}


def run_label_shuffle(signal, forward, n_iter: int = 2000, seed: int = 42) -> dict:
    return label_shuffle_test(np.asarray(signal), np.asarray(forward), n_iter, seed)
