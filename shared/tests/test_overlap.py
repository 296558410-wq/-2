# -*- coding: utf-8 -*-
"""test_overlap.py — overlap-aware 统计协议测试。"""
import numpy as np
import pandas as pd
import pytest

from research_engine.statistics.overlap import (block_bootstrap_ci, block_permutation_p,
                                                effective_n, ic_at_entries,
                                                non_overlap_entries)


def test_effective_n():
    assert effective_n(9000, 60) == 150


def test_non_overlap_entries_non_overlapping():
    ei = non_overlap_entries(1000, 60)
    assert len(ei) == (1000 - 60 + 59) // 60
    assert np.all(np.diff(ei) == 60)


def test_iid_vs_block_on_correlated_noise():
    """重叠强自相关序列：iid 置换应比 block 更“显著”（体现虚高）；非重叠抽样后两者接近。"""
    rng = np.random.default_rng(0)
    n = 4000
    # 强自相关噪声（随机游走差分后做标签会产生重叠结构）
    x = rng.standard_normal(n)
    y = np.convolve(x, np.ones(60) / 60, mode="same") + rng.standard_normal(n) * 0.1
    r_iid = block_permutation_p(x, y, n_iter=500, seed=1)
    # 非重叠抽样后重测（间隔 60）
    xs, ys = x[::60], y[::60]
    r_non = block_permutation_p(xs, ys, n_iter=500, seed=1)
    assert r_non["p_iid"] > r_iid["p_iid"]  # 非重叠后显著性应下降
    assert abs(r_non["p_iid"] - r_non["p_block2"]) < 0.15  # 非重叠后两口径接近


def test_ic_at_entries_runs():
    ts = pd.date_range("2026-01-01", periods=5000, freq="1min", tz="UTC")
    f = pd.Series(np.random.default_rng(1).standard_normal(5000), index=ts)
    fwd = pd.Series(np.random.default_rng(2).standard_normal(5000), index=ts)
    out = ic_at_entries(f, fwd, 60)
    assert out["n_entries"] > 0


def test_block_bootstrap_ci_shape():
    rng = np.random.default_rng(3)
    x = rng.standard_normal(800)
    y = 0.2 * x + rng.standard_normal(800)
    ci = block_bootstrap_ci(x, y, n_iter=200, seed=4)
    assert ci["ci95"][0] < ci["ic"] < ci["ci95"][1]
