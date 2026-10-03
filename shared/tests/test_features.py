# -*- coding: utf-8 -*-
"""test_features.py — 特征/标签引擎：对齐纪律与无前视属性测试。"""
import numpy as np
import pandas as pd
import pytest

from research_engine.core.dataset import SyntheticXAUUSDGenerator
from research_engine.core.feature import FeatureSpec, build as build_features, assert_no_lookahead
from research_engine.core.signal import make_signal, positions_from_thresholds
from research_engine.features import (atr, ema, momentum, realised_vol, rolling_std,
                                      sma, volatility_ratio)
from research_engine.features.labels import add_forward_labels, mfe_mae


@pytest.fixture(scope="module")
def m1():
    gen = SyntheticXAUUSDGenerator(seed=3)
    ds = gen.generate(days=2)
    return ds.bars["1min"].sort_values("ts_utc").reset_index(drop=True)


def test_price_features_shapes(m1):
    fm = build_features(m1, [FeatureSpec("mom30", momentum, {"window": 30}),
                             FeatureSpec("rv60", realised_vol, {"window": 60}),
                             FeatureSpec("atr14", atr, {"window": 14}),
                             FeatureSpec("sma60", sma, {"window": 60}),
                             FeatureSpec("ema30", ema, {"window": 30}),
                             FeatureSpec("vr", volatility_ratio, {"short": 15, "long": 120})])
    assert fm.lookback_max == 120
    X = fm.drop_warmup().X
    assert len(X) == len(m1) - 120
    assert X.notna().all().all()


def test_no_lookahead_property(m1):
    specs = [FeatureSpec("mom30", momentum, {"window": 30}),
             FeatureSpec("rv60", realised_vol, {"window": 60})]
    res = assert_no_lookahead(m1, specs, probes=6, seed=5)
    assert res["passed"], res["mismatches"]


def test_momentum_manual(m1):
    c = m1["close"]
    mom = momentum(m1, 30)
    i = 100
    assert np.isclose(mom.iloc[i], c.iloc[i] / c.iloc[i - 30] - 1)


def test_labels_strictly_future(m1):
    labels = add_forward_labels(m1)
    # 与未来 close 直接对照
    c = m1["close"]
    i = 500
    h = 60
    assert np.isclose(labels["forward_return_60m"].iloc[i], c.iloc[i + h] / c.iloc[i] - 1)
    # future_vol 等于未来窗口收益 std
    r = c.pct_change()
    assert np.isclose(labels["future_vol_60m"].iloc[i], r.iloc[i + 1: i + 1 + 60].std(ddof=1), atol=1e-12)
    # 尾部应为 NaN（无未来）
    assert labels["forward_return_240m"].iloc[-1] != labels["forward_return_240m"].iloc[-1]  # NaN
    # mfe/mae 正确性
    fwd_hi = m1["high"].iloc[i + 1: i + 1 + 60].max()
    assert np.isclose(mfe_mae(m1, 60)["mfe"].iloc[i], fwd_hi / c.iloc[i] - 1)


def test_signal_positions():
    s = pd.Series([-2.0, -0.1, 0.0, 0.1, 2.0])
    pos = positions_from_thresholds(s, long_th=0.0, short_th=0.0)
    np.testing.assert_array_equal(pos.values, [-1, -1, 0, 1, 1])
    sig = make_signal(s, rule="sign")
    np.testing.assert_array_equal(sig.positions.values, [-1, -1, 0, 1, 1])
    assert sig.n_trades == 3
