# -*- coding: utf-8 -*-
"""Phase 9 discovery — P1/P4/P5 tick detectors: registry drift + math tests."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from research.phase9.discovery import run_config as rc                     # noqa: E402
from research.phase9.discovery.detectors.p1p4p5 import (                   # noqa: E402
    P1_TICK_CFG, P4_TICK_CFG, P5_TICK_CFG, run_p1_family, run_p4_family,
    run_p5_family,
)


def make_ticks(times_s, prices):
    ts = (np.asarray(times_s) * 1e9).astype(np.int64)
    return ts, np.asarray(prices, dtype=np.float64)


def test_registry_drift():
    reg = rc.load_registry()
    for det_id, cfg in P1_TICK_CFG.items():
        d = rc.get_detector(det_id)
        assert d["family"] == "P1" and d["layer"] == "TICK"
        assert f"{cfg['z']:.2f}" in str(d["6_threshold"])
        assert f"{cfg['hold_s']:.0f}s" in str(d["12_holding_period"])
    for det_id, cfg in P4_TICK_CFG.items():
        d = rc.get_detector(det_id)
        assert d["family"] == "P4" and d["layer"] == "TICK"
        assert f"{cfg['z']:.2f}" in str(d["6_threshold"])
        assert str(cfg["decay"]) in str(d["6_threshold"]) or "0.5" in str(d["6_threshold"])
        assert f"{cfg['hold_s']:.0f}s" in str(d["12_holding_period"])
    d = rc.get_detector("P5_release_30s")
    cfg = P5_TICK_CFG["P5_release_30s"]
    assert d["family"] == "P5" and d["layer"] == "TICK"
    assert str(cfg["q_c"]) in str(d["6_threshold"])
    assert str(cfg["q_rel"]) in str(d["6_threshold"])
    assert f"{cfg['hold_s']:.0f}s" in str(d["12_holding_period"])


def _quiet(rng, t, m, secs, center, noise=0.001, dt=0.1):
    for _ in range(int(secs / dt)):
        t.append(t[-1] + dt if len(t) else 0.0)
        m.append(center + rng.normal(0, noise))
    return t, m


def test_p1_event_detection():
    """A strong single 30s window move >= 2.79 sigma yields a sign(z) event."""
    rng = np.random.default_rng(3)
    base = 4000.0
    t, m = [], []
    tt = 0.0
    for _ in range(8000):                      # quiet warm-up 800s (>=20 30s-win)
        t.append(tt); m.append(base + rng.normal(0, 0.002)); tt += 0.1
    # one strong 30s window up-move of ~0.25 USD (>> 2.79 sigma)
    for k in range(300):
        t.append(tt); m.append(base + 0.25 * k / 300); tt += 0.1
    for _ in range(100):                        # short tail
        t.append(tt); m.append(base + 0.25 + rng.normal(0, 0.002)); tt += 0.1
    ts, mid = make_ticks(t, m)
    res = run_p1_family(ts, mid)
    ev = res["P1_disp_z_30s"]["events"]
    assert len(ev) >= 1
    assert (ev["direction"] > 0).all()


def test_p4_exhaustion_decay():
    """Decelerating impulse (v3 <= 0.5 v1, aligned) yields a fade event."""
    rng = np.random.default_rng(4)
    base = 4000.0
    t, m = [], []
    tt = 0.0
    for _ in range(4000):
        t.append(tt); m.append(base + rng.normal(0, 0.001)); tt += 0.1
    # impulse over 3x10s with deceleration: +0.4, +0.2, +0.1
    for k, (mv, dur) in enumerate([(0.4, 10.0), (0.2, 10.0), (0.1, 10.0)]):
        n = int(dur * 10)
        for j in range(n):
            t.append(tt); m.append(m[-1] + mv / n); tt += 0.1
    for _ in range(100):
        t.append(tt); m.append(m[-1] + rng.normal(0, 0.001)); tt += 0.1
    ts, mid = make_ticks(t, m)
    res = run_p4_family(ts, mid)
    ev = res["P4_exhaust_fade_10s"]["events"]
    assert len(ev) >= 1
    assert (ev["direction"] < 0).all()          # fade the up impulse
    assert (ev["decay"] <= 0.5).all()


def test_p5_release_after_compression():
    """>=10 full 30s compressed windows then a directional expansion -> release."""
    rng = np.random.default_rng(5)
    base = 4000.0
    t, m = [], []
    tt = 0.0
    for _ in range(8100):                        # warm-up 810s -> w0..w26 exact
        t.append(tt); m.append(base + rng.normal(0, 0.01)); tt += 0.1
    # exactly 10 compressed 30s windows w27..w36 (range ~1e-3); the frozen rule
    # self-limits runs near 10-11 (median tips to comp level), so the release
    # must follow the 10th window to trigger.
    for k in range(3000):
        t.append(tt); m.append(base + rng.normal(0, 0.001)); tt += 0.1
    # release 30s window w37: strong up body (+0.06 over the window)
    for k in range(300):
        t.append(tt); m.append(base + 0.06 * (k + 1) / 300); tt += 0.1
    # tail so the entry tick (strictly after signal) exists
    for _ in range(60):
        t.append(tt); m.append(base + 0.06); tt += 0.1
    ts, mid = make_ticks(t, m)
    res = run_p5_family(ts, mid)
    ev = res["P5_release_30s"]["events"]
    assert len(ev) >= 1, "no release event found"
    assert (ev["direction"] > 0).all()
