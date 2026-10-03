# -*- coding: utf-8 -*-
"""Phase 9 discovery — P7 detector math & registry-drift tests.

Runs from repo root:  .venv\\Scripts\\python.exe -m pytest tests/test_phase9_p7.py -q
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from research.phase9.discovery import run_config as rc                # noqa: E402
from research.phase9.discovery.detectors.p7 import (                  # noqa: E402
    P7_TICK_CFG, build_impact, build_qpressure, impact_bursts,
    quote_moves,
)


def quote_stream(seconds, bid_px, ask_px):
    """(ts_ns, mid, bid, ask) sorted arrays from per-tick samples."""
    ts = (np.asarray(seconds, dtype=np.float64) * 1e9).astype(np.int64)
    bid = np.asarray(bid_px, dtype=np.float64)
    ask = np.asarray(ask_px, dtype=np.float64)
    return ts, (bid + ask) / 2.0, bid, ask


# ---------------------------------------------------------------- registry drift
def test_p7_config_matches_registry():
    """Frozen code config must be consistent with the frozen registry texts."""
    reg = rc.load_registry()
    for det_id, cfg in P7_TICK_CFG.items():
        d = rc.get_detector(det_id)
        assert d is not None
        assert d["family"] == "P7" and d["layer"] == "TICK"
        assert f"{cfg['hold_s']:.0f}s" in str(d["12_holding_period"]), det_id
        if cfg["kind"] == "qpressure":
            assert f"{cfg['p_min']:.1f}" in str(d["6_threshold"]), det_id  # 0.5
            assert f"min(up,dn) >= {cfg['floor']}" in str(d["6_threshold"]), det_id
            assert cfg["base"] in str(d["5_sampling_frequency"]), det_id
            assert "P = (up - dn)/(up + dn + 1)" in str(d["1_mathematical_definition"])
            assert "sign(P)" in str(d["7_signal_direction"])
        else:
            assert "0.30" in str(d["6_threshold"]), det_id
            if cfg["cls"] == "fade":
                assert "0.4" in str(d["6_threshold"]), det_id
                assert "-sign(immediate move)" in str(d["7_signal_direction"])
                assert "rho" in str(d["1_mathematical_definition"])
            else:
                assert "0.7" in str(d["6_threshold"]), det_id
                assert "+sign(immediate move)" in str(d["7_signal_direction"])


# ---------------------------------------------------------------- quote pressure
def test_qpressure_imbalance_event_and_floors():
    """Strong quote imbalance window fires (|P|>=0.5, floor met, dir=+1); a
    balanced window (P=0) and a sub-floor window (min(up,dn)=1<3) do not."""
    t, b, a = [], [], []
    base_b, base_a = 4000.00, 4000.20

    def add(sec, bid_px, ask_px):
        t.append(sec); b.append(bid_px); a.append(ask_px)

    # 30s quiet background (unchanged quotes), 0.5s cadence
    for k in range(60):
        add(0.5 * k, base_b, base_a)
    # [60,70): 1 neutral + 14 up (bid&ask +0.02) + 4 dn (bid&ask -0.02) + neutral
    add(60.0, base_b, base_a)
    bb, ba = base_b, base_a
    for j in range(14):
        bb += 0.02; ba += 0.02
        add(60.5 + 0.5 * j, bb, ba)
    for j in range(4):
        bb -= 0.02; ba -= 0.02
        add(67.5 + 0.5 * j, bb, ba)
    add(69.5, bb, ba)                       # neutral
    # [70,80): balanced 9 up / 9 dn -> P = 0 (no event; floor ok)
    add(70.0, bb, ba)
    for j in range(9):
        bb += 0.02; ba += 0.02
        add(70.5 + 0.5 * j, bb, ba)
    for j in range(9):
        bb -= 0.02; ba -= 0.02
        add(75.0 + 0.5 * j, bb, ba)
    add(79.5, bb, ba)
    # [80,90): 6 up / 1 dn -> |P|=0.625 but min(up,dn)=1 < floor 3 -> no event
    add(80.0, bb, ba)
    for j in range(6):
        bb += 0.02; ba += 0.02
        add(80.5 + 0.5 * j, bb, ba)
    bb -= 0.02; ba -= 0.02
    add(83.5, bb, ba)
    for j in range(12):
        add(84.0 + 0.5 * j, bb, ba)
    # [90,100): quiet (provides entry ticks after the last active window)
    for j in range(20):
        add(90.0 + 0.5 * j, bb, ba)

    ts, mid, bid, ask = quote_stream(t, b, a)
    up, dn = quote_moves(ts, bid, ask)
    ev, uni = build_qpressure(ts, mid, up, dn, "10s", floor=3, p_min=0.5)

    # exactly one event: the [60,70) window, up=14 dn=4, P=10/19, dir=+1
    assert len(ev) == 1, ev.to_dict("records")
    row = ev.iloc[0]
    assert row["up"] == 14 and row["dn"] == 4
    assert abs(row["P"] - 10.0 / 19.0) < 1e-12
    assert row["direction"] == 1.0
    assert row["class"] == "press_up"
    # entry strictly after the window's last tick (69.5s -> 70.0s)
    assert row["entry_ts"] == 70.0 * 1e9
    # universe = both floor-meeting windows only ([60,70) and [70,80))
    assert len(uni) == 2, uni.to_dict("records")
    assert set(uni["up"]) == {14, 9}
    assert set(uni["dn"]) == {4, 9}


def test_qpressure_negative_imbalance_direction():
    """A dn-dominated window fires with direction -1 (symmetric short side)."""
    t, b, a = [], [], []
    base_b, base_a = 4000.00, 4000.20

    def add(sec, bid_px, ask_px):
        t.append(sec); b.append(bid_px); a.append(ask_px)

    for k in range(40):
        add(0.5 * k, base_b, base_a)
    add(20.0, base_b, base_a)
    bb, ba = base_b, base_a
    for j in range(14):                     # down first: 14 dn
        bb -= 0.02; ba -= 0.02
        add(20.5 + 0.5 * j, bb, ba)
    for j in range(4):                      # then 4 up
        bb += 0.02; ba += 0.02
        add(27.5 + 0.5 * j, bb, ba)
    add(29.5, bb, ba)
    for j in range(20):                     # quiet tail for entry ticks
        add(30.0 + 0.5 * j, bb, ba)

    ts, mid, bid, ask = quote_stream(t, b, a)
    up, dn = quote_moves(ts, bid, ask)
    ev, _ = build_qpressure(ts, mid, up, dn, "10s", floor=3, p_min=0.5)
    assert len(ev) == 1
    row = ev.iloc[0]
    assert row["up"] == 4 and row["dn"] == 14
    assert row["P"] < 0 and row["direction"] == -1.0


# ---------------------------------------------------------------- burst impact
def _quiet_and_burst(burst_rise_then_fade=True):
    """60 quiet 5s buckets, one arrival-burst bucket, then a tail.

    Quiet buckets 0..59 (0..300s): 5 flat ticks each at 4000.00.
    Burst bucket 60 [300s,305s): 50 ticks at 0.1s cadence from 300.05; mid
    rises +0.50 USD by 302s (k=20 at 4000.50), then (fade) reverts to 4000.00
    by 305s or (hold) stays at 4000.50.
    Tail buckets 61..65 (305..330s): 5 flat ticks per bucket at the post-burst
    level (fade -> 4000.00, hold -> 4000.50) so the r6 tick at t0+6s exists.
    """
    t, b, a = [], [], []

    def add(sec, px):
        t.append(sec); b.append(px); a.append(px + 0.20)

    for bk in range(60):                    # quiet 0..300s, 5 ticks/bucket
        for j in range(5):
            add(bk * 5.0 + 0.2 + 1.0 * j, 4000.00)
    px = 4000.00                            # burst bucket [300,305): 50 ticks
    for k in range(50):
        sec = 300.05 + 0.1 * k
        if 1 <= k <= 20:                    # k=20 at 302.05 -> 4000.50
            px += 0.025
        elif burst_rise_then_fade and k >= 30:   # fade back to 4000.00 by 305s
            px -= 0.025
        add(sec, px)
    tail_px = 4000.00 if burst_rise_then_fade else 4000.50
    for bk in range(61, 66):                # tail 305..330s at post level
        for j in range(5):
            add(bk * 5.0 + 0.2 + 1.0 * j, tail_px)
    ts, mid, bid, ask = quote_stream(t, b, a)
    return ts, mid, bid, ask


def test_impact_fade_rho_classification():
    """Burst with r1>=0.30 USD that fully reverts by t0+6s -> rho~0 -> fade
    class, direction = -sign(immediate up move) = -1."""
    ts, mid, bid, ask = _quiet_and_burst(burst_rise_then_fade=True)
    ev, uni = build_impact(ts, mid, "fade", r1_min=0.30, rho_max=0.4)
    assert len(uni) >= 1                     # burst universe non-empty
    assert len(ev) == 1, ev.to_dict("records")
    row = ev.iloc[0]
    assert row["class"] == "fade"
    assert abs(row["r1_usd"] - 0.50) < 1e-6
    assert row["rho"] < 0.05                # full fade -> ~0
    assert row["direction"] == -1.0
    assert row["entry_ts"] > row["t_sig_ns"]  # entry after r6-confirming tick


def test_impact_hold_rho_classification():
    """Burst with r1>=0.30 USD that persists to t0+6s -> rho~0.98 -> hold
    class, direction = +sign(immediate up move) = +1."""
    ts, mid, bid, ask = _quiet_and_burst(burst_rise_then_fade=False)
    ev, uni = build_impact(ts, mid, "hold", r1_min=0.30, rho_min=0.7)
    assert len(uni) >= 1
    assert len(ev) == 1, ev.to_dict("records")
    row = ev.iloc[0]
    assert row["class"] == "hold"
    assert abs(row["r1_usd"] - 0.50) < 1e-6
    assert row["rho"] >= 0.7
    assert row["direction"] == 1.0
    assert row["entry_ts"] > row["t_sig_ns"]


def test_impact_p95_point_in_time():
    """Trailing p95 is point-in-time over 60 x 5s calendar buckets: no bucket
    before 20 observed buckets qualifies (warm-up), the crafted 50-tick burst
    qualifies against a p95 of ~5 (its own count not in its trailing window),
    and quiet 5-tick buckets at/above the trailing p95 are present."""
    ts, mid, bid, ask = _quiet_and_burst(burst_rise_then_fade=True)
    bur = impact_bursts(ts, mid)
    assert len(bur) > 0
    assert bur["t0_ns"].min() >= 100.0 * 1e9    # >= 20 observed buckets warm-up
    crafted = bur[bur["t0_ns"] == 300.0 * 1e9]
    assert len(crafted) == 1
    assert crafted.iloc[0]["count"] == 50
    assert abs(crafted.iloc[0]["p95_trail"] - 5.0) < 1e-9
    assert (bur["count"] <= 50).all()
    assert len(bur[bur["count"] < 10]) > 0      # quiet bursts (5 >= p95) exist
