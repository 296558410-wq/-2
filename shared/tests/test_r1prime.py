# -*- coding: utf-8 -*-
"""R1' G1 tests: parity, params integrity, state-machine conformance,
truncation invariance, FVT engine == replay daily series."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from research.r1prime.r1_params import PARAMS, params_sha256            # noqa: E402
from research.r1prime.replay_phase5 import replay_comparison            # noqa: E402
from research.r1prime.data import load_h1                               # noqa: E402
from research.r1prime.features import bar_features, day_snapshot        # noqa: E402
from research.r1prime.machine import StateMachine                       # noqa: E402
from research.r1prime import evaluate as ev                             # noqa: E402

MC = PARAMS["machine"]


# ---------------------------------------------------------------- parity
def test_fvt_parity_exact():
    res = replay_comparison()
    assert res["all_ok"]
    for w in res["windows"].values():
        assert max(w["diffs"].values()) <= 1e-9  # byte-exact replay


def test_fvt_engine_equals_replay_daily():
    """Leg engine with mu=1 must reproduce Phase-5 FVT daily strat series."""
    df = load_h1("XAUUSD_H1_MT5-FXTM-Live_20260904_v001")
    ow = ev.oneway_bp(PARAMS["cost"]["fxtm_spread_bp"])
    s = ev.fvt_size_h1(df)
    daily = ev.apply_policy(df, s, np.ones(len(df)), ow)["ret"]
    # replay path daily (phase5 pattern)
    r = df["close"].pct_change()
    vf = np.sqrt(r.pow(2).ewm(halflife=12, min_periods=12).mean()).shift(1) * np.sqrt(365 * 24)
    size = np.clip(0.10 / vf, 0.0, 2.0)
    cost = np.abs(np.diff(np.concatenate([[0.0], size.values]))) * ow / 1e4
    strat_h1 = size.shift(1).values * r.values - cost
    dd = pd.DataFrame({"ret": strat_h1,
                       "day": pd.DatetimeIndex(df["ts_utc"]).date}).groupby("day").sum()
    dd.index = pd.to_datetime(dd.index, utc=True)
    pd.testing.assert_series_equal(daily, dd["ret"], check_names=False)


# ---------------------------------------------------------------- params integrity
def test_params_complete():
    assert PARAMS["meta"]["registry_id"] == "R1'_PARAMS_V1"
    assert PARAMS["label"]["E_quantile_days"] == 252
    assert PARAMS["machine"]["rho"] == 0.5
    assert PARAMS["adpc"]["tiers_target_vol"] == [0.05, 0.10, 0.15]
    assert params_sha256()


# ---------------------------------------------------------------- state machine
def _run(gate, vf_high, kill=None, days=40):
    idx = pd.date_range("2026-01-01", periods=days, freq="D", tz="UTC")
    g = pd.Series(gate, index=idx)
    v = pd.Series(vf_high, index=idx)
    k = pd.Series(kill if kill is not None else [False] * days, index=idx)
    return StateMachine(g, v, k).run()


def test_sm_reduced_entry_exit():
    gate = [0] * 40
    gate[5] = 1  # single day
    st = _run(gate, [0] * 40)
    # REDUCED on day5, exit after 3 clear days (day9)
    assert st["mode"].iloc[5] == "REDUCED"
    assert st["mode"].iloc[6] == "REDUCED"          # min hold 1 + clear count <3
    assert st["mode"].iloc[8] == "FULL"             # 3 clear days (d6..d8)
    assert st["mu"].iloc[5] == MC["rho"]


def test_sm_stop_requires_two_days_and_vol():
    gate = [0] * 40
    vh = [0] * 40
    for i in (5, 6, 7):
        gate[i] = 1
    for i in (5, 6):
        vh[i] = 1
    st = _run(gate, vh)
    assert st["mode"].iloc[5] == "REDUCED"           # 1st day not enough for STOP
    assert st["mode"].iloc[6] == "STOPPED"           # 2 consecutive + vf_high
    assert st["mode"].iloc[9] == "STOPPED"           # min hold 2; clear d8..
    assert st["mode"].iloc[10] == "FULL"             # 3 clear days (8,9,10)


def test_sm_vf_high_alone_insufficient():
    vh = [1] * 40
    st = _run([0] * 40, vh)
    assert (st["mode"] == "FULL").all()


def test_sm_kill_override():
    kill = [False] * 40
    kill[10] = True
    st = _run([0] * 40, [0] * 40, kill)
    assert st["mode"].iloc[10] == "STOPPED"


def test_sm_churn_penalty():
    """Exit then re-trigger within 3 days -> next STOPPED exit needs 5 clear days."""
    gate = [0] * 40
    vh = [0] * 40
    for i in (4, 5):            # STOPPED after 2 consecutive days with vf_high
        gate[i] = 1
        vh[i] = 1
    # exit: clear d6..d8 -> FULL d8 (s_out=3)
    for i in (9, 10):           # re-trigger within 3 days -> churn armed
        gate[i] = 1
        vh[i] = 1
    st = _run(gate, vh)
    assert st["mode"].iloc[5] == "STOPPED"
    assert st["mode"].iloc[8] == "FULL"
    assert st["mode"].iloc[10] == "STOPPED"
    # churn: exit needs 5 clear days: cleared d11..d15 -> FULL d15
    assert st["mode"].iloc[14] == "STOPPED"
    assert st["mode"].iloc[15] == "FULL"


# ---------------------------------------------------------------- truncation invariance
def test_truncation_invariance():
    """Truncating future data must not change past decision-time features."""
    df = load_h1("XAUUSD_H1_MT5-FXTM-Live_20260904_v001")
    feats_full = bar_features(df)
    days = sorted(set(pd.DatetimeIndex(df["ts_utc"]).date))
    cut = pd.Timestamp(days[120]).tz_localize("UTC") + pd.Timedelta(days=1)
    sub = df[pd.DatetimeIndex(df["ts_utc"]) < cut].copy()
    feats_sub = bar_features(sub)
    snap_full = day_snapshot(df, feats_full)
    snap_sub = day_snapshot(sub, feats_sub)
    common = snap_full.index.intersection(snap_sub.index)
    assert len(common) >= 100
    cols = ["G", "A_gate", "vf_high", "rv", "vf", "act", "adpc_target", "vf_up"]
    for c in cols:
        a = snap_full.loc[common, c].astype(float)
        b = snap_sub.loc[common, c].astype(float)
        pd.testing.assert_series_equal(a, b, check_names=False)
