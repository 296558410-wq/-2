# -*- coding: utf-8 -*-
"""test_backtest.py — 回测引擎：时序约定/成本/指标正确性。"""
import numpy as np
import pandas as pd
import pytest

from research_engine.core.backtest import BacktestEngine, compute_metrics
from research_engine.core.cost import CostModel
from research_engine.validation.cost_stress import run_cost_stress


def _close(n=1000, seed=0):
    r = np.random.default_rng(seed).normal(0, 1e-3, n)
    return pd.Series(2400 * np.exp(np.cumsum(r)))


def test_no_lookahead_execution():
    """position[t] 只影响 t+1 起的收益：扰动未来价格不影响过去收益。"""
    c = _close()
    pos = pd.Series(np.where(np.arange(len(c)) % 3 == 0, 1.0, 0.0), index=c.index)
    bt = BacktestEngine(CostModel(spread_bps=0.0, commission_bps=0.0, slippage_bps=0.0))
    r1 = bt.run(c, pos, name="a")
    c2 = c.copy()
    c2.iloc[500:] *= 1.5  # 扰动未来
    r2 = bt.run(c2, pos, name="b")
    # 前 500 根 bar 的收益序列应完全一致
    np.testing.assert_allclose(r1.df["net_r"].iloc[:500], r2.df["net_r"].iloc[:500], atol=1e-15)


def test_position_lag_one_bar():
    """常持多仓时，net_r[t] = r[t]（即 t-1 收盘决策 → 赚 t 区间收益）。"""
    c = _close()
    pos = pd.Series(1.0, index=c.index)
    bt = BacktestEngine(CostModel(0, 0, 0))
    df = bt.run(c, pos, name="long").df
    r = c.pct_change().values
    np.testing.assert_allclose(df["gross_r"].values, np.concatenate([[0.0], r[1:]]), atol=1e-15)


def test_cost_charged_on_turnover():
    cm = CostModel(spread_bps=2.0, commission_bps=0.0, slippage_bps=0.0)
    assert np.isclose(cm.one_way_bps, 1.0)          # half spread
    c = _close()
    pos = pd.Series(np.where(np.arange(len(c)) % 2 == 0, 1.0, -1.0), index=c.index)
    bt = BacktestEngine(cm)
    df = bt.run(c, pos, name="x").df
    # 每次 flip = 2 单位换手 → 期望成本 = flips*2*1e-4；用 df 内 turnover 直接核对
    np.testing.assert_allclose(df["cost_r"].values, df["turnover"].values * cm.one_way_cost, atol=1e-15)


def test_metrics_manual():
    net = np.array([0.01, -0.005, 0.02, 0.0, 0.005, -0.01, 0.015, 0.0, 0.0, 0.0])
    pos = np.array([1.0] * 10)
    gross = net.copy()
    cost = np.zeros(10)
    m = compute_metrics(net, gross, cost, pos, periods_per_year=252.0)
    assert np.isclose(m["net_total_return"], np.prod(1 + net) - 1)
    assert m["n_bars"] == 10
    assert m["n_trades"] == 1  # 初始进入
    # 恒定持仓无换手：turnover=1（初始）
    assert np.isclose(m["turnover_total"], 1.0)
    # 最大回撤手工核对
    eq = np.cumprod(1 + net)
    dd = (eq / np.maximum.accumulate(eq) - 1).min()
    assert np.isclose(m["max_drawdown"], dd)


def test_cost_stress_monotonic():
    c = _close()
    pos = pd.Series(np.where(np.arange(len(c)) % 2 == 0, 1.0, -1.0), index=c.index)
    bt = BacktestEngine(CostModel())
    df = bt.run(c, pos, name="x").df
    stress = run_cost_stress(df["gross_r"].values, df["position"].values,
                             CostModel().one_way_cost)
    s1, s2, s3 = stress["1x"]["sharpe_annualized"], stress["2x"]["sharpe_annualized"], stress["3x"]["sharpe_annualized"]
    assert s1 >= s2 >= s3  # 成本越高 Sharpe 不升


def test_convention_fields_in_config():
    c = _close(n=100)
    pos = pd.Series(0.0, index=c.index)
    bt = BacktestEngine(CostModel())
    r = bt.run(c, pos, name="x")
    cfg = r.config
    assert "signal_timestamp" in cfg and "execution_timestamp" in cfg
