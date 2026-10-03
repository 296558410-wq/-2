# -*- coding: utf-8 -*-
"""statistics/overlap.py — Overlap-aware 时间序列统计协议（Phase 5 核心升级）。

背景：Phase 4 证明 overlapping labels 使 iid permutation/CI 功效严重虚高
（同一规则 n≈9k 重叠 p=0.0000 → n≈200 非重叠 p=0.28）。
规则：
  * 任何前瞻 horizon 检验必须提供 effective sample size = 非重叠入场点数
  * iid 结果仅作对照，不作最终证据
  * 提供：非重叠抽样 / 非重叠置换 p / block bootstrap CI / effective_n
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def non_overlap_entries(n: int, horizon: int, start: int = 0) -> np.ndarray:
    """每 horizon 个位置取一个入场点（非重叠前瞻窗）。"""
    return np.arange(start, n - horizon, horizon)


def effective_n(n_obs: int, horizon: int) -> int:
    """重叠样本的有效样本量 ≈ n/horizon（一阶近似）。"""
    return max(1, int(n_obs / horizon))


def ic_at_entries(feature: pd.Series, forward: pd.Series, horizon: int,
                  train_frac: float = 0.6) -> dict:
    """在非重叠入场点上的 OOS IC。feature/forward 同索引（forward 已含 h 前移）。"""
    m = pd.concat([feature, forward], axis=1).dropna()
    n = len(m)
    ei = non_overlap_entries(n, horizon)
    if len(ei) < 30:
        return {"n": 0, "ic_oos": np.nan, "note": "非重叠样本不足"}
    cut = int(len(ei) * train_frac)
    te = ei[cut:]
    ic = float(spearmanr(m.iloc[te, 0].values, m.iloc[te, 1].values).statistic)
    return {"n_entries": int(len(ei)), "n_oos": int(len(te)),
            "eff_n": effective_n(n, horizon), "ic_oos": ic}


def block_permutation_p(x: np.ndarray, y: np.ndarray, n_iter: int = 2000,
                        seed: int = 1) -> dict:
    """非重叠块置换 p：把 y 按 horizon 块洗牌？简单版：独立置换 + 说明。

    对非重叠样本序列，时间依赖已大幅消除 → iid 置换近似合理；
    本函数额外报告保守的 block(2) 置换作为对照。
    """
    rng = np.random.default_rng(seed)
    n = len(x)
    if n < 20:
        return {"p_iid": 1.0, "p_block2": 1.0, "n": n}
    obs = float(spearmanr(x, y).statistic)
    d_iid = np.empty(n_iter)
    d_blk = np.empty(n_iter)
    for i in range(n_iter):
        pi = rng.permutation(y)
        d_iid[i] = float(spearmanr(x, pi).statistic)
        # block(2)：打乱长度为 2 的块
        nb = n // 2
        yb = y[: nb * 2].reshape(nb, 2)
        yb = yb[rng.permutation(nb)].reshape(-1)
        d_blk[i] = float(spearmanr(x[: len(yb)], yb).statistic)
    return {"p_iid": float((np.abs(d_iid) >= abs(obs)).mean()),
            "p_block2": float((np.abs(d_blk) >= abs(obs)).mean()), "n": n,
            "ic": obs}


def block_bootstrap_ci(x: np.ndarray, y: np.ndarray, n_iter: int = 2000,
                       seed: int = 2) -> dict:
    """块(2) bootstrap 的 IC 95% CI。"""
    rng = np.random.default_rng(seed)
    n = len(x)
    obs = float(spearmanr(x, y).statistic)
    nb = n // 2
    xb = x[: nb * 2].reshape(nb, 2)
    yb = y[: nb * 2].reshape(nb, 2)
    dist = np.empty(n_iter)
    for i in range(n_iter):
        idx = rng.integers(0, nb, nb)
        dist[i] = float(spearmanr(xb[idx].reshape(-1), yb[idx].reshape(-1)).statistic)
    return {"ic": obs, "ci95": [float(np.percentile(dist, 2.5)),
                                float(np.percentile(dist, 97.5))], "n_iter": n_iter}
