# -*- coding: utf-8 -*-
"""test_market_state.py — Market Understanding 模块冒烟+性质测试。"""
import numpy as np
import pandas as pd
import pytest

from market_understanding.autopsy import autopsy_one, autopsies_markdown
from market_understanding.events import detect_events
from market_understanding.state import (build_state_features_notime, fit_states_gmm,
                                        state_profiles, transition_matrix)


@pytest.fixture(scope="module")
def df():
    n = 12000
    ts = pd.date_range("2026-01-01", periods=n, freq="1min", tz="UTC")
    rng = np.random.default_rng(0)
    vol = 1e-4 * (1 + 4 * ((np.arange(n) % 5000) > 4500))
    close = 3300 * np.exp(np.cumsum(rng.standard_normal(n) * vol))
    spread_base = 0.15 + 0.01 * rng.standard_normal(n)
    spread = np.where((np.arange(n) % 5000) > 4500, spread_base + 0.3, spread_base)
    return pd.DataFrame({
        "ts_utc": ts, "close": close, "high": close * 1.0002, "low": close * 0.9998,
        "spread": spread,
        "tick_volume": rng.integers(100, 300, n).astype(float),
    })


def test_state_features_and_fit(df):
    Z = build_state_features_notime(df, act_col="tick_volume", spread_col="spread")
    assert len(Z) > 9000
    fit = fit_states_gmm(Z, k_range=range(2, 5), seed=1)
    assert 2 <= fit["k"] <= 4
    assert len(fit["labels"]) == len(Z)
    prof = state_profiles(df.iloc[Z.index], fit["labels"])
    assert len(prof) == fit["k"]
    # 高波动状态应显示更高 fwd vol
    assert prof["fwd_vol60_med"].is_monotonic_increasing or prof["fwd_vol60_med"].max() > prof["fwd_vol60_med"].min()


def test_transition_matrix_rows_sum_to_one(df):
    Z = build_state_features_notime(df, act_col="tick_volume", spread_col="spread")
    fit = fit_states_gmm(Z, k_range=[3], seed=1)
    tr = transition_matrix(fit["labels"])
    M = np.asarray(tr["matrix"])
    np.testing.assert_allclose(M.sum(axis=1), 1.0, atol=1e-9)
    assert len(tr["mean_duration_min"]) == 3


def test_event_detection(df):
    ev = detect_events(df, window=30, k_sigma=2.5, min_gap=60)
    assert len(ev) >= 1
    assert {"t_mid", "direction", "abs_ret_pct"}.issubset(ev.columns)


def test_autopsy_runs(df):
    ev = detect_events(df, window=30, k_sigma=2.5, min_gap=60)
    md = autopsies_markdown(df, ev, max_events=2)
    assert md.startswith("# XAUUSD Market Autopsy")
    assert "## Event" in md
