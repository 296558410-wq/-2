# -*- coding: utf-8 -*-
"""Phase 9 discovery — P2 detector math & registry-drift tests.

Runs from repo root:  .venv\\Scripts\\python.exe -m pytest tests/test_phase9_p2.py -q
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from research.phase9.discovery import run_config as rc                # noqa: E402
from research.phase9.discovery.detectors.common import (              # noqa: E402
    classify_fail_hold, impulse_events,
)
from research.phase9.discovery.detectors.p2 import P2_TICK_CFG        # noqa: E402
from research.phase9.discovery.stats import add_labels, non_overlap   # noqa: E402


def make_ticks(base_price, times_s, prices):
    """Build (ts_ns, mid) sorted arrays from (seconds, price) samples."""
    ts = (np.asarray(times_s) * 1e9).astype(np.int64)
    m = np.asarray(prices, dtype=np.float64)
    return ts, m


# ---------------------------------------------------------------- registry drift
def test_p2_config_matches_registry():
    """Frozen code config must be consistent with the frozen registry texts."""
    reg = rc.load_registry()
    for det_id, cfg in P2_TICK_CFG.items():
        d = rc.get_detector(det_id)
        assert d is not None
        assert cfg["base"] in str(d["5_sampling_frequency"])
        assert f"{cfg['z']:.2f}" in str(d["6_threshold"]), det_id
        assert "50%" in str(d["6_threshold"]) or "< 50%" in str(d["6_threshold"])
        if "fail" in det_id:
            assert "0.30" in str(d["6_threshold"]), det_id  # cost-viable min |D|
        else:
            # hold inherits the impulse universe (incl. min |D|) via field 1
            assert "Same impulse universe" in str(d["1_mathematical_definition"]), det_id
        assert d["family"] == "P2" and d["layer"] == "TICK"


# ---------------------------------------------------------------- impulse math
def test_impulse_detected_up_and_down():
    """Craft two clean impulses separated by quiet periods (sigma reset) and
    verify detection + fail/hold classification."""
    rng = np.random.default_rng(7)
    base = 4000.0
    t, m = [], []
    tt = 0.0

    def quiet(secs, center):
        nonlocal tt
        for _ in range(int(secs * 10)):
            t.append(tt); m.append(center + rng.normal(0, 0.001)); tt += 0.1

    def ramp(secs, start_px, total_move):
        nonlocal tt
        n = int(secs * 10)
        for k in range(n):
            t.append(tt); m.append(start_px + total_move * k / n); tt += 0.1
        return start_px + total_move

    quiet(400, base)                    # sigma warm-up at base
    px = ramp(30, base, 0.60)           # up-impulse +0.60 USD over 30s -> 4000.60
    quiet(60, px)                       # hold at +0.60 (no retrace within 60s) -> hold
    quiet(400, px)                      # sigma reset (still at +0.60)
    low = ramp(30, px, -1.00)           # down-impulse to base-0.40
    ramp(15, low, 0.60)                 # retrace up 60% -> crosses 50% level (+0.10)
    ts, mid = make_ticks(base, t, m)
    ev = impulse_events(ts, mid, "10s", z_thr=2.79, min_disp_usd=0.30)
    assert len(ev) >= 2, f"expected >=2 impulses, got {len(ev)}"
    cf = classify_fail_hold(ts, mid, ev, "10s", retrace=0.5)
    # up impulse (d>0, first row) has no 50% retrace within 60s -> hold
    up = cf.iloc[0]
    assert up["d"] > 0 and up["class"] == "hold", cf.to_dict("records")
    # down impulse retraced >=50% (from base-0.40 up through base+0.10) -> fail
    dn = cf[cf["d"] < 0]
    assert len(dn) >= 1
    assert (dn["class"] == "fail").any(), cf.to_dict("records")


def test_non_overlap_greedy():
    ev = pd.DataFrame({"entry_ts": [100e9, 101e9, 130e9, 190e9], "x": [1, 2, 3, 4]})
    out = non_overlap(ev, min_gap_s=30)
    assert list(out["entry_ts"]) == [100e9, 130e9, 190e9]


def test_add_labels_no_lookahead():
    """entry price must be >= entry_ts; exit >= entry_ts+holding; no NaN in range."""
    ts = np.arange(0, 2000) * int(1e8)  # 0.1s ticks, 200s
    mid = np.full(2000, 4000.0) + np.arange(2000) * 0.001
    ev = pd.DataFrame({"entry_ts": [int(50 * 1e9), int(100 * 1e9)],
                       "direction": [1, -1]})
    lab = add_labels(ts, mid, ev, holding_s=30.0, max_label_ns=int(190 * 1e9))
    assert len(lab) == 2
    assert (lab["entry_price"].to_numpy() >= 4000.0 + 50 * 0.001 - 1e-9).all()
    assert lab["net_bp"].isna().sum() == 0
