# -*- coding: utf-8 -*-
"""test_dataset.py — Synthetic 数据集 + 已知答案结构检查。

在生成数据上验证：
  1. 模型结构自洽（bar 由 tick 聚合；OHLC 单调性）
  2. 已知答案存在：趋势 regime 的 M1 漂移显著、冲击期波动更高
  3. pure_rw 模式均值≈0（供实验 A）
"""
import numpy as np
import pandas as pd
import pytest

from research_engine.core.dataset import SyntheticXAUUSDGenerator


@pytest.fixture(scope="module")
def ds():
    return SyntheticXAUUSDGenerator(seed=42).generate(days=3)


@pytest.fixture(scope="module")
def ds_shock():
    """含足够多 shock 分钟的短数据集（自动搜索种子）。"""
    gen = SyntheticXAUUSDGenerator(seed=0)
    for seed in range(40):
        gen.seed = seed
        d = gen.generate(days=4)
        if d.ground_truth_m1["in_shock"].sum() >= 30:
            return d
    return gen.generate(days=8)


def test_bars_consistent_with_ticks(ds):
    ticks = ds.ticks
    m1 = ds.bars["1min"]
    assert len(m1) == 3 * 1440
    # OHLC 单调性
    assert (m1["high"] >= m1[["open", "close"]].max(axis=1)).all()
    assert (m1["low"] <= m1[["open", "close"]].min(axis=1)).all()
    # M1 收盘 = 该分钟最后一笔 mid
    t = m1.iloc[100]["ts_utc"]
    last_mid = ticks[ticks["ts_utc"] < t + pd.Timedelta(minutes=1)].iloc[-1]["mid"]
    assert abs(last_mid - m1.iloc[100]["close"]) < 1e-9
    # spread 结构
    assert (ticks["ask"] >= ticks["bid"]).all()
    assert (ticks["buy_volume"] <= ticks["volume"]).all()


def test_ground_truth_aligned(ds):
    gt = ds.ground_truth_m1
    assert len(gt) == len(ds.bars["1min"])
    assert gt["regime"].isin(["trend_up", "trend_down", "range", "high_vol"]).all()


def test_known_answer_trend_present(ds):
    """已知答案 B：趋势 regime 内 M1 收益应有显著漂移。"""
    m1 = ds.bars["1min"].sort_values("ts_utc").reset_index(drop=True)
    gt = ds.ground_truth_m1.sort_values("ts_utc").reset_index(drop=True)
    r = m1["close"].pct_change()
    up = r[gt["regime"] == "trend_up"]
    dn = r[gt["regime"] == "trend_down"]
    assert len(up) > 100 and len(dn) > 100
    assert up.mean() > 0
    assert dn.mean() < 0
    # 分组 t 检验近似：均值差 > 0
    assert up.mean() - dn.mean() > 0


def test_known_answer_vol_shock(ds_shock):
    """已知答案 C：shock 期 M1 波动显著高于非 shock 期。"""
    m1 = ds_shock.bars["1min"].sort_values("ts_utc").reset_index(drop=True)
    gt = ds_shock.ground_truth_m1.sort_values("ts_utc").reset_index(drop=True)
    r = m1["close"].pct_change()
    sh = r[gt["in_shock"]]
    ns = r[~gt["in_shock"]]
    assert len(sh) > 20
    assert sh.std(ddof=1) > ns.std(ddof=1) * 1.3


def test_pure_rw_no_drift():
    ds = SyntheticXAUUSDGenerator(seed=1).generate(days=1, pure_rw=True)
    r = ds.bars["1min"]["close"].pct_change().dropna()
    # 均值应在噪声范围（1 天 M1 ≈ 1440 样本；|mean| < 2*std/sqrt(n) 的宽松断言）
    assert abs(r.mean()) < 2 * r.std() / np.sqrt(len(r))
    assert (ds.ground_truth_m1["regime"] == "rw").all()
    assert not ds.ground_truth_m1["in_shock"].any()
