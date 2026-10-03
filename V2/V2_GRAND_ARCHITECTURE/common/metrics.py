"""Evaluation metrics + statistical tests (bootstrap / permutation / FDR).

All metrics are computed on cost-adjusted net returns in PRICE units unless a
helper says otherwise. Nothing here redefines a metric after seeing results.
"""
from __future__ import annotations
import numpy as np


def effective_n(signal: np.ndarray) -> int:
    """Number of non-zero (traded) signals = number of positions opened."""
    return int(np.count_nonzero(np.asarray(signal, dtype=np.float64)))


def precision(signal: np.ndarray, net: np.ndarray) -> float:
    m = (signal != 0) & np.isfinite(net)
    if m.sum() == 0:
        return float("nan")
    return float((net[m] > 0).mean())


def expectancy(signal: np.ndarray, net: np.ndarray) -> float:
    m = (signal != 0) & np.isfinite(net)
    if m.sum() == 0:
        return float("nan")
    return float(net[m].mean())


def total_return(signal: np.ndarray, net: np.ndarray) -> float:
    m = (signal != 0) & np.isfinite(net)
    if m.sum() == 0:
        return float("nan")
    return float(net[m].sum())


def mfe_mae(signal: np.ndarray, mid: np.ndarray, h: int) -> tuple[float, float]:
    """Mean max favourable / adverse excursion over horizon h (price units)."""
    n = len(mid)
    fav, adv = [], []
    for i in np.nonzero(signal)[0]:
        if i + h >= n:
            continue
        seg = mid[i + 1:i + 1 + h] - mid[i]
        if signal[i] > 0:
            fav.append(seg.max()); adv.append(-seg.min())
        else:
            fav.append(-seg.min()); adv.append(seg.max())
    if not fav:
        return float("nan"), float("nan")
    return float(np.mean(fav)), float(np.mean(adv))


def sharpe_like(net: np.ndarray) -> float:
    x = net[np.isfinite(net)]
    if x.size < 2 or x.std() == 0:
        return float("nan")
    return float(x.mean() / x.std() * np.sqrt(x.size))


def stability(series: np.ndarray, n_blocks: int = 4) -> float:
    """Sign-consistency of block means: fraction of blocks agreeing in sign
    with the overall mean. Low = unstable across time."""
    x = series[np.isfinite(series)]
    if x.size < n_blocks * 2:
        return float("nan")
    blocks = np.array_split(x, n_blocks)
    means = np.array([b.mean() for b in blocks])
    overall = x.mean()
    if overall == 0:
        return float("nan")
    agree = (np.sign(means) == np.sign(overall)).mean()
    return float(agree)


def block_bootstrap_ci(x: np.ndarray, n_boot: int = 2000, block: int = 10,
                       alpha: float = 0.05, seed: int = 20261003) -> tuple[float, float, float]:
    """Stationary-ish block bootstrap CI for the mean. Returns (mean, lo, hi)."""
    x = np.asarray(x, dtype=np.float64)
    x = x[np.isfinite(x)]
    n = x.size
    if n < block * 2:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block))
    starts = rng.integers(0, n - block, size=(n_boot, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n_boot, -1)[:, :n]
    samples = x[idx].mean(axis=1)
    return float(x.mean()), float(np.quantile(samples, alpha / 2)), float(np.quantile(samples, 1 - alpha / 2))


def permutation_pvalue(signal: np.ndarray, gross: np.ndarray, net_stat: float,
                       n_perm: int = 2000, seed: int = 20261003) -> float:
    """One-sided permutation test: shuffle the SIGN of the traded returns.
    p = fraction of permutations with mean >= observed (for positive edge)."""
    m = (signal != 0) & np.isfinite(gross)
    x = gross[m]
    if x.size < 10:
        return float("nan")
    rng = np.random.default_rng(seed)
    signs = rng.choice([-1.0, 1.0], size=(n_perm, x.size))
    perm = (signs * x[None, :]).mean(axis=1)
    return float((perm >= net_stat).mean())


def benjamini_hochberg(pvalues: list[float], q: float = 0.05) -> list[bool]:
    """BH FDR control. NaN p-values are treated as non-significant."""
    n = len(pvalues)
    order = sorted(range(n), key=lambda i: (np.inf if not np.isfinite(pvalues[i]) else pvalues[i]))
    cutoff = [False] * n
    k_max = -1
    for rank, i in enumerate(order, start=1):
        p = pvalues[i]
        if np.isfinite(p) and p <= q * rank / n:
            k_max = rank
    for rank, i in enumerate(order, start=1):
        if rank <= k_max:
            cutoff[i] = True
    return cutoff
