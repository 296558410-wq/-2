# -*- coding: utf-8 -*-
"""alpha_engine/filters.py — 统计漏斗（§13/§15/§16）。

OOS permutation IC 检验带 GPU 分块实现（RTX A2000，4GB 安全）。
Stage 链：raw → OOS perm → BH-FDR（全局一轮）→ WF → cost → subperiod。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from research_engine.compute.common import gpu_available


def _spearman_perm_gpu(x: np.ndarray, y: np.ndarray, n_iter: int, seed: int,
                       batch: int = 128) -> tuple[float, np.ndarray]:
    """GPU 分块置换 IC。返回 (obs, dist)。统计量 = Pearson(rank(x), rank(y))。"""
    import torch
    g = torch.Generator(device="cuda").manual_seed(seed)
    xt = torch.as_tensor(x, dtype=torch.float64, device="cuda")
    yt = torch.as_tensor(y, dtype=torch.float64, device="cuda")
    # 预先计算 rank(x)（浮点，避免重复）
    rx = torch.argsort(torch.argsort(xt)).double()
    rx = (rx - rx.mean()) / (rx.std() + 1e-12)
    dist: list[float] = []
    obs = float(spearmanr(x, y).statistic)
    for b0 in range(0, n_iter, batch):
        b = min(batch, n_iter - b0)
        idx = torch.randint(0, len(y), (b, len(y)), device="cuda", generator=g)
        yp = yt[idx]
        ry = torch.argsort(torch.argsort(yp, dim=1), dim=1).double()
        ry = (ry - ry.mean(dim=1, keepdim=True)) / (ry.std(dim=1, keepdim=True) + 1e-12)
        corr = (rx * ry).mean(dim=1)
        dist.extend(corr.cpu().tolist())
        del idx, yp, ry
    torch.cuda.synchronize()
    return obs, np.asarray(dist)


def oos_permutation_p(feature: pd.Series, label: pd.Series,
                      train_frac: float = 0.6, n_iter: int = 1000,
                      seed: int = 42, backend: str = "auto") -> dict:
    """IC 的 OOS 显著性（test 段；permutation 打乱 label 时序）。"""
    m = pd.concat([feature, label], axis=1).dropna()
    if len(m) < 500:
        return {"ic_oos": 0.0, "p_value": 1.0, "n_iter": 0, "oos_n": int(len(m)),
                "note": "样本不足"}
    n = len(m)
    cut = int(n * train_frac)
    x = m.iloc[cut:, 0].values.astype(np.float64)
    y = m.iloc[cut:, 1].values.astype(np.float64)
    use_gpu = backend == "auto" and gpu_available() and len(y) > 20000 and n_iter >= 500
    if use_gpu:
        obs, dist = _spearman_perm_gpu(x, y, n_iter, seed)
    else:
        obs = float(spearmanr(x, y).statistic)
        rng = np.random.default_rng(seed)
        dist = np.empty(n_iter)
        for i in range(n_iter):
            dist[i] = float(spearmanr(x, rng.permutation(y)).statistic)
    return {"ic_oos": obs, "p_value": float((np.abs(dist) >= abs(obs)).mean()),
            "n_iter": int(n_iter), "oos_n": int(len(x)),
            "perm_mean": float(dist.mean()), "perm_std": float(dist.std()),
            "backend": "gpu" if use_gpu else "cpu"}


def bootstrap_ci_ic(feature: pd.Series, label: pd.Series, n_iter: int = 2000,
                    seed: int = 7) -> dict:
    """bootstrap CI（numpy 秩向量化，避免逐次 scipy.spearmanr 的 Python 开销）。"""
    m = pd.concat([feature, label], axis=1).dropna()
    x = m.iloc[:, 0].values
    y = m.iloc[:, 1].values
    rng = np.random.default_rng(seed)
    n = len(x)

    def _rank(a):
        order = np.argsort(a, kind="mergesort")
        ranks = np.empty(n, dtype=np.float64)
        ranks[order] = np.arange(n)
        return ranks

    def _pearson_r(ra, rb):
        ra = ra - ra.mean()
        rb = rb - rb.mean()
        return float((ra * rb).sum() / np.sqrt((ra * ra).sum() * (rb * rb).sum()))

    rx0 = _rank(x)
    obs = _pearson_r(rx0, _rank(y))
    dist = np.empty(n_iter)
    for i in range(n_iter):
        idx = rng.integers(0, n, n)
        dist[i] = _pearson_r(rx0[idx], _rank(y[idx]))
    return {"ic": obs, "ci95": [float(np.percentile(dist, 2.5)),
                                float(np.percentile(dist, 97.5))],
            "n_iter": n_iter, "ic_std": float(dist.std())}
