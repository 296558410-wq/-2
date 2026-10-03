# -*- coding: utf-8 -*-
"""Phase 9 discovery — M1 layer detectors: registry drift + synthetic math tests.

Runs from repo root:  .venv\\Scripts\\python.exe -m pytest tests/test_phase9_m1.py -q
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from research.phase9.discovery import run_config as rc                     # noqa: E402
from research.phase9.discovery import data_m1                              # noqa: E402
from research.phase9.discovery.detectors.m1_p1p2p4 import (                # noqa: E402
    P1_M1_CFG, P2_M1_CFG, P4_M1_CFG, run_p1_m1_family, run_p2_m1_family,
    run_p4_m1_family,
)
from research.phase9.discovery.detectors.m1_p3 import (                    # noqa: E402
    P3_M1_CFG, run_p3_m1_family,
)
from research.phase9.discovery.detectors.m1_p5p6 import (                  # noqa: E402
    P5_M1_CFG, P6_M1_CFG, run_p5_m1_family, run_p6_m1_family,
)

M1_REGISTRY_IDS = [
    "P1_disp_z_3m", "P1_accel_jerk_1m", "P2_fail_1m_M1",
    "P3_accept_3m", "P3_reject_3m", "P3_accept_5m", "P3_reject_5m",
    "P4_exhaust_fade_1m_M1", "P5_release_1m", "P5_release_3m",
    "P5_release_5m", "P6_hi_act_dir_1m", "P6_burst_spread_fade_3m",
    "P6_contraction_spike_10m",
]

T0 = pd.Timestamp("2026-06-01 00:00:00", tz="UTC").value


def make_bars(closes, volumes=None, ranges=None, open_=None, t0=T0):
    """1m BarSlice from a per-minute close path (continuous path: minute open =
    previous close; optional explicit wick `ranges` for P5-style tests)."""
    closes = np.asarray(closes, dtype=np.float64)
    n = len(closes)
    if open_ is None:
        opens = np.empty(n)
        opens[0] = closes[0] - 0.01
        opens[1:] = closes[:-1]
    else:
        opens = np.asarray(open_, dtype=np.float64)
    if ranges is None:
        wick = 0.001
        high = np.maximum(opens, closes) + wick
        low = np.minimum(opens, closes) - wick
    else:
        rng = np.asarray(ranges, dtype=np.float64)
        mid = (opens + closes) / 2
        high = mid + rng / 2
        low = mid - rng / 2
    ts = t0 + np.arange(n) * 60_000_000_000
    vol = np.full(n, 100.0) if volumes is None else np.asarray(volumes, float)
    spread = np.full(n, 0.15)
    return data_m1.BarSlice(ts, opens, high, low, closes, vol, spread,
                            ts[0], ts[-1] + 600_000_000_000)


def _alt(level_usd, base=4000.0):
    """Minute closes alternating around `base` by +/- level_usd."""
    out = []
    for k in range(300):
        out.append(base + level_usd * (1 if k % 2 == 0 else -1))
    return out


# ---------------------------------------------------------------- registry drift
def test_m1_registry_drift_configs():
    """Frozen code configs must mirror the frozen registry M1 texts."""
    reg_ids = {d["detector_id"] for d in rc.load_registry()["detectors"]
               if d["layer"] == "M1"}
    assert reg_ids == set(M1_REGISTRY_IDS)
    cfg_sets = [set(P1_M1_CFG), set(P2_M1_CFG), set(P4_M1_CFG), set(P3_M1_CFG),
                set(P5_M1_CFG), set(P6_M1_CFG)]
    assert set(M1_REGISTRY_IDS) == set().union(*cfg_sets)
    # P1
    for det_id, cfg in P1_M1_CFG.items():
        d = rc.get_detector(det_id)
        assert d["family"] == "P1" and d["layer"] == "M1"
        assert f"{cfg['z']:.2f}" in str(d["6_threshold"])
        assert cfg["scale"] in str(d["5_sampling_frequency"])
        assert str(cfg["hold_bars"]) in str(d["12_holding_period"])
    # P2 M1 fail
    cfg = P2_M1_CFG["P2_fail_1m_M1"]
    d = rc.get_detector("P2_fail_1m_M1")
    assert d["family"] == "P2" and d["layer"] == "M1"
    assert f"{cfg['z']:.2f}" in str(d["6_threshold"])
    assert "50%" in str(d["6_threshold"]) and "0.30" in str(d["6_threshold"])
    # P3
    for det_id, cfg in P3_M1_CFG.items():
        d = rc.get_detector(det_id)
        assert d["family"] == "P3" and d["layer"] == "M1"
        assert str(cfg["S"]) in str(d["1_mathematical_definition"]) \
            or f"S={cfg['S']}" in str(d["4_lookback"])
        assert str(cfg["hold_bars"]) in str(d["12_holding_period"])
        cls = cfg["cls"]
        assert ("accept" in det_id) == (cls == "accept")
    # P4
    cfg = P4_M1_CFG["P4_exhaust_fade_1m_M1"]
    d = rc.get_detector("P4_exhaust_fade_1m_M1")
    assert d["family"] == "P4" and d["layer"] == "M1"
    assert str(cfg["z"]) in str(d["6_threshold"])
    assert str(cfg["decay"]) in str(d["6_threshold"])
    assert "0.30" in str(d["6_threshold"])
    # P5
    for det_id, cfg in P5_M1_CFG.items():
        d = rc.get_detector(det_id)
        assert d["family"] == "P5" and d["layer"] == "M1"
        assert str(cfg["q_c"]) in str(d["6_threshold"])
        assert str(cfg["q_rel"]) in str(d["6_threshold"])
        assert str(cfg["hold_bars"]) in str(d["12_holding_period"])
    # P6
    for det_id, cfg in P6_M1_CFG.items():
        d = rc.get_detector(det_id)
        assert d["family"] == "P6" and d["layer"] == "M1"
        assert str(cfg["pct_thr"]) in str(d["6_threshold"])
        assert cfg["scale"] in str(d["5_sampling_frequency"])
        assert str(cfg["hold_bars"]) in str(d["12_holding_period"])


def test_m1_windows_and_holding_parse():
    reg = rc.load_registry()
    d = rc.get_detector("P1_disp_z_3m")
    assert "2026-05-26T00:00Z" in str(d["17_discovery_period"])
    assert "2026-08-03T23:59Z" in str(d["17_discovery_period"])
    assert rc.M1_DISCOVERY_START == "2026-05-26T00:00:00Z"
    assert rc.M1_DISCOVERY_END == "2026-08-03T23:59:59Z"
    # M1 holding texts -> seconds
    assert rc.parse_holding_s("6m (2 bars)") == 360.0
    assert rc.parse_holding_s("3m (3 bars)") == 180.0
    assert rc.parse_holding_s("3 bars (3m)") == 180.0
    assert rc.parse_holding_s("3 bars (9m)") == 540.0
    assert rc.parse_holding_s("3 bars (15m)") == 900.0
    assert rc.parse_holding_s("5 bars (5m)") == 300.0
    assert rc.parse_holding_s("2 bars (20m)") == 1200.0
    # tick holding texts unchanged
    assert rc.parse_holding_s("30s (1 x W_I)") == 30.0
    assert rc.parse_holding_s("90s (1 x W_I)") == 90.0
    assert rc.parse_holding_s("60s (2 windows)") == 60.0


# ---------------------------------------------------------------- synthetic P1
def test_p1_accel_jerk_crossing_1m():
    """Flat quiet then one accelerating minute -> a_t/sigma_a crossing, dir=+1."""
    closes = [4000.0] * 100 + [4000.40, 4000.40 + 0.01] + [4000.41] * 20
    # velocity spike at bar 100 (+0.40); acceleration a = +0.40/4000 -> z huge
    bar = make_bars(closes)
    res = run_p1_m1_family(bar)
    ev = res["P1_accel_jerk_1m"]["events"]
    assert len(ev) >= 1
    assert (ev["direction"] > 0).all()
    # entry strictly after the signal-bar close: entry_ts > close of sig bar
    opens = data_m1.resample_bars(bar, "1m")["ts_open"].to_numpy(np.int64)
    for _, row in ev.iterrows():
        sig = int(row["sig_idx"])
        assert row["entry_ts"] > opens[sig] + 60_000_000_000


def test_p1_disp_z_3m_crossing():
    """Alternating +/-0.001 3m buckets (|z| ~ 1) then a +0.60 USD 3m bar ->
    |z| >= 2.15 first crossing with dir = +1."""
    # 3m bucket closes alternate by 0.001; then one bucket up +0.60
    closes = []
    for k in range(62):
        level = 4000.0 + 0.001 * (1 if k % 2 == 0 else -1)
        closes += [level] * 3
    big = closes[-1] + 0.60
    closes += [big] * 3
    closes += [closes[-1]] * 12          # tail so an entry bar exists
    bar = make_bars(closes)
    res = run_p1_m1_family(bar)
    ev = res["P1_disp_z_3m"]["events"]
    assert len(ev) >= 1
    assert (ev["direction"] > 0).all()


# ---------------------------------------------------------------- synthetic P2
def test_p2_fail_1m_retrace():
    """Up-impulse (3 x +0.35 USD minutes) then a close retracing >= 50% ->
    fail event with dir = -1, signal on the confirming bar."""
    quiet = _alt(0.001, 4000.0)                     # 300 alternating minutes
    imp = [quiet[-1] + 0.35, quiet[-1] + 0.70, quiet[-1] + 1.05]
    retr = [imp[-1] - 0.60]                         # close below the 50% level
    closes = quiet + imp + retr + [imp[-1] - 0.60] * 30
    bar = make_bars(closes)
    res = run_p2_m1_family(bar)
    ev = res["P2_fail_1m_M1"]["events"]
    uni = res["P2_fail_1m_M1"]["universe"]
    assert len(uni) >= 1                            # impulse universe non-empty
    assert len(ev) >= 1
    assert (ev["direction"] < 0).all()              # fade the up impulse
    assert (ev["D_log"] > 0).all()


# ---------------------------------------------------------------- synthetic P3
def _p3_closes(level_jump, after):
    """Quiet plateau 4000 for 20+ 3m buckets, break bar +1.0, then `after`
    per-bucket closes (3 minutes each)."""
    closes = []
    for k in range(22):
        closes += [4000.0] * 3
    closes += [4001.0] * 3                          # break bar t
    for c in after:
        closes += [c] * 3
    closes += [closes[-1]] * 9                      # tail
    return closes


def test_p3_accept_3m():
    """Break above the 20-close max; close_{t+3} still >= level -> accept +1."""
    closes = _p3_closes(1.0, [4000.5, 4000.3, 4000.8])
    bar = make_bars(closes)
    res = run_p3_m1_family(bar)
    ev = res["P3_accept_3m"]["events"]
    assert len(ev) >= 1
    assert (ev["direction"] > 0).all()
    assert (ev["break_dir"] > 0).all()
    # acceptance confirms on the O-th bar after the break
    for _, row in ev.iterrows():
        assert int(row["break_idx"]) + 3 == int(row["sig_idx"])


def test_p3_reject_3m():
    """Break above the level then a close below L_hi within O bars -> reject -1
    (the up-break rejection row; a down-break mirror may fire later and is
    allowed to appear with direction +1 in the same pooled sample)."""
    closes = _p3_closes(1.0, [3999.5, 4000.2, 4000.4])
    bar = make_bars(closes)
    res = run_p3_m1_family(bar)
    ev = res["P3_reject_3m"]["events"]
    up_rej = ev[(ev["break_dir"] > 0) & (ev["direction"] < 0)]
    assert len(up_rej) >= 1
    for _, row in up_rej.iterrows():
        assert int(row["break_idx"]) + 1 == int(row["sig_idx"])  # first bar back


# ---------------------------------------------------------------- synthetic P4
def test_p4_exhaust_fade_1m():
    """5-minute decelerating up-impulse (0.40/0.30/0.20/0.10/0.05 USD):
    decay <= 0.5 -> fade event dir = -1 at t5."""
    quiet = _alt(0.001, 4000.0)
    base = quiet[-1]
    steps = [0.40, 0.30, 0.20, 0.10, 0.05]
    imp = []
    acc = base
    for s in steps:
        acc = acc + s
        imp.append(acc)
    tail = [imp[-1] - 0.001, imp[-1], imp[-1] - 0.001, imp[-1]] * 5
    closes = quiet + imp + tail
    bar = make_bars(closes)
    res = run_p4_m1_family(bar)
    ev = res["P4_exhaust_fade_1m_M1"]["events"]
    uni = res["P4_exhaust_fade_1m_M1"]["universe"]
    assert len(uni) >= 1
    assert len(ev) >= 1
    assert (ev["direction"] < 0).all()
    assert (ev["decay"] <= 0.5).all()


# ---------------------------------------------------------------- synthetic P5
def test_p5_release_1m_after_compression():
    """>=10 compressed 1m bars (small range) then a directional expansion bar ->
    release event, dir = sign(body) = +1."""
    n_hi = 40
    opens, closes, ranges = [], [], []
    # moderate-range quiet bars: range 0.008 -> rfrac ~ 2e-6
    for k in range(n_hi):
        opens.append(4000.0)
        closes.append(4000.0)
        ranges.append(0.008)
    # compressed bars: range 0.0016 -> rfrac ~ 4e-7 (<= 0.5 x median while the
    # 20-bar median still reflects the quiet phase)
    for k in range(10):
        opens.append(4000.0)
        closes.append(4000.0)
        ranges.append(0.0016)
    # release bar: strong up body, small wicks
    opens.append(4000.0)
    closes.append(4000.60)
    ranges.append(0.62)
    # tail
    for k in range(15):
        opens.append(4000.60)
        closes.append(4000.60)
        ranges.append(0.0016)
    bar = make_bars(np.asarray(closes), ranges=np.asarray(ranges),
                    open_=np.asarray(opens))
    res = run_p5_m1_family(bar)
    ev = res["P5_release_1m"]["events"]
    assert len(ev) >= 1, "no release event after a 10-bar compression run"
    assert (ev["direction"] > 0).all()


# ---------------------------------------------------------------- synthetic P6
def _volume_cycle(level_a, level_b, level_c, n):
    """Deterministic 3-level volume pattern with controlled percentile ranks."""
    pat = [level_a, level_b, level_a]
    return np.tile(pat, int(np.ceil(n / 3)))[:n]


def test_p6_contraction_spike_10m():
    """Long quiet 10m history, sustained rvol20 <= 0.5 contraction, then a high
    pct_act spike bar -> the spike bar itself is an event (dir = body sign).
    Activity is a trailing percentile rank: local volume maxima inside the
    contraction also rank >= 0.9 and appear as events — the spike row (sig_idx
    == 260, the 10m bar with volume 1900) must be among them with dir = +1."""
    # history: 10m bucket closes alternate +/- 0.05 -> sigma_200 ~ 1.25e-5
    closes, vols = [], []
    big_buckets = 230
    for k in range(big_buckets):
        level = 4000.0 + 0.05 * (1 if k % 2 == 0 else -1)
        closes += [level] * 10
        vols += list(_volume_cycle(100.0, 50.0, 100.0, 10))
    # contraction: +/- 0.005 -> sigma_20 ~ 1.25e-6, rvol20 ~ 0.1
    n_small = 30
    for k in range(n_small):
        level = closes[-1] + 0.005 * (1 if k % 2 == 0 else -1)
        closes += [level] * 10
        vols += list(_volume_cycle(100.0, 50.0, 100.0, 10))
    # spike 10m bar: tiny price move (stays low-vol), big tick volume, up body
    spike_close = closes[-1] + 0.01
    closes += [spike_close] * 10
    vols += [1000.0] + [100.0] * 9
    for k in range(6):                              # tail
        level = closes[-1] + 0.005 * (1 if k % 2 == 0 else -1)
        closes += [level] * 10
        vols += list(_volume_cycle(100.0, 50.0, 100.0, 10))
    bar = make_bars(np.asarray(closes), volumes=np.asarray(vols))
    res = run_p6_m1_family(bar)
    ev = res["P6_contraction_spike_10m"]["events"]
    assert len(ev) >= 1, "no contraction-spike event found"
    assert (ev["pct_act"] >= 0.9).all()
    assert (ev["rvol20"] <= 0.5).all()
    spike = ev[ev["sig_idx"] == 260]
    assert len(spike) >= 1, "spike bar itself did not fire"
    assert (spike["direction"] > 0).all()


def test_p6_hi_act_dir_1m():
    """High pct_act + rvol20 >= 1.0 expansion minutes -> events with dir =
    sign(close_t - close_{t-3})."""
    closes, vols = [], []
    for k in range(250):                            # quiet 1m history
        closes.append(4000.0 + 0.002 * (1 if k % 2 == 0 else -1))
    vols += list(_volume_cycle(100.0, 50.0, 100.0, 250))
    base = closes[-1]
    for k in range(60):                             # expansion minutes
        closes.append(base + 0.02 * (1 if k % 2 == 0 else -1))
    vols += list(_volume_cycle(150.0, 100.0, 150.0, 60))
    for k in range(30):
        closes.append(closes[-1] + 0.002 * (1 if k % 2 == 0 else -1))
    vols += list(_volume_cycle(100.0, 50.0, 100.0, 30))
    bar = make_bars(np.asarray(closes), volumes=np.asarray(vols))
    res = run_p6_m1_family(bar)
    ev = res["P6_hi_act_dir_1m"]["events"]
    assert len(ev) >= 1, "no high-activity expansion event found"
    assert (ev["pct_act"] >= 0.8).all()
    assert (ev["rvol20"] >= 1.0).all()
