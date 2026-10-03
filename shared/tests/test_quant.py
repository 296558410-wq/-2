"""test_quant.py — 量化基础统计量测试（与手算/已知性质对照）。"""
import numpy as np
import pytest


def returns_from_prices(prices):
    return np.diff(prices) / prices[:-1]


def test_returns():
    p = np.array([100.0, 110.0, 99.0])
    r = returns_from_prices(p)
    np.testing.assert_allclose(r, [0.1, -0.1], atol=1e-12)


def test_volatility():
    r = np.full(1000, 0.01)
    assert abs(r.std(ddof=1)) < 1e-12
    # 已知序列方差
    r2 = np.array([0.01, -0.01] * 500)
    assert abs(r2.std(ddof=1) - 0.0100005) < 1e-4


def test_drawdown():
    cum = np.array([1.0, 1.2, 1.1, 1.3, 1.0, 1.4])
    dd = float((cum / np.maximum.accumulate(cum) - 1).min())
    assert abs(dd - (1.0 / 1.3 - 1)) < 1e-9


def test_sharpe_annualized():
    r = np.random.default_rng(0).normal(0.0005, 0.01, 5000)
    sr = r.mean() / r.std() * np.sqrt(252)
    assert 0 < sr < 1.0


def test_bootstrap_sanity():
    from research_engine.validation import permutation_test, shuffle_test, benjamini_hochberg, seed_all
    seed_all(1)
    x = np.random.default_rng(2).normal(0, 1, 2000)
    res = permutation_test(x, n_iter=500, seed=3)
    # 零均值数据 → p 值不应太小（保守断言）
    assert res["p_value"] > 0.01
    # 有真实信号 → p 显著
    y = np.random.default_rng(4).normal(0.5, 1, 2000)
    res2 = permutation_test(y, n_iter=500, seed=5)
    assert res2["p_value"] < 0.05

    sig = np.sign(np.random.default_rng(6).normal(0, 1, 500))
    rets = np.random.default_rng(7).normal(0, 1, 500)
    sh = shuffle_test(sig, rets, n_iter=300, seed=8)
    assert 0 <= sh["p_value"] <= 1

    pvals = np.array([0.001, 0.01, 0.04, 0.2, 0.5])
    bh = benjamini_hochberg(pvals, alpha=0.05)
    assert sum(bh["reject"]) == 2  # 0.001 与 0.01 通过 BH(0.05)
    q = np.array(bh["q_values"])
    assert q.max() <= 1.0 and q.min() >= 0
