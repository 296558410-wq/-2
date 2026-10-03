"""Tests for RQ-07 Execution Reality Engine v0.

Run:  cd C:\\AIQuant && .venv\\Scripts\\python.exe -m pytest tests/test_execution_reality.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from research.execution_reality import (  # noqa: E402
    Decision,
    ExecutionConfig,
    ExecutionEngine,
    Fill,
    MissedOrder,
    OrderType,
    Side,
    load_tick_frame,
    normalize_frame,
)
from research.execution_reality.loader import _TIME_COLUMNS  # noqa: E402

FXTM_FILE = REPO / "data" / "staging_fxtm" / "ticks_20260804.parquet"
FXTM_FILE2 = REPO / "data" / "staging_fxtm" / "ticks_20260904.parquet"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def make_frame(ts_ms, bids, asks):
    return pd.DataFrame(
        {
            "ts": np.asarray(ts_ms, dtype="int64"),
            "bid": np.asarray(bids, dtype="float64"),
            "ask": np.asarray(asks, dtype="float64"),
        }
    )


def zero_cost_config(**kw):
    base = dict(latency_ms=0.0, max_quote_age_ms=5000.0,
                slippage_bps=0.0, slippage_spread_frac=0.0, cost_bps=0.0)
    base.update(kw)
    return ExecutionConfig(**base)


# --------------------------------------------------------------------------- #
# (1) no-lookahead as-of quote selection + decision price
# --------------------------------------------------------------------------- #
def test_no_lookahead_asof_quote_selection():
    # quotes at t=1000 (ask 101.00) and t=2000 (ask 102.00)
    frame = make_frame([1000, 2000], [100.00, 101.00], [101.00, 102.00])
    cfg = zero_cost_config(decision_price_mode="mid", latency_ms=0.0)
    eng = ExecutionEngine(cfg)

    # decision at t=1500: newest quote <= 1500 is the t=1000 quote.
    rep = eng.run(frame, [(1500, "buy", 1.0)])
    assert rep.n_fills == 1 and rep.n_missed == 0
    f = rep.fills[0]
    assert f.quote_time == 1000.0
    assert f.fill_price == 101.00          # ask of the as-of quote, no slip
    assert f.decision_price == 100.5       # mid of quote <= decision time

    # decision at t=2000 exactly: as-of includes the t=2000 quote.
    rep2 = eng.run(frame, [(2000, "buy", 1.0)])
    assert rep2.fills[0].quote_time == 2000.0
    assert rep2.fills[0].fill_price == 102.00

    # never sees quotes strictly after the arrival instant
    assert all(f.quote_time <= f.fill_time for f in rep2.fills)


def test_decision_price_modes():
    frame = make_frame([0], [100.00], [102.00])
    for mode, want_buy, want_sell in [
        ("mid", 101.0, 101.0),
        ("touch", 102.0, 100.0),
        ("bid", 100.0, 100.0),
        ("ask", 102.0, 102.0),
    ]:
        eng = ExecutionEngine(zero_cost_config(decision_price_mode=mode))
        rb = eng.run(frame, [(0, "buy", 1.0)])
        rs = eng.run(frame, [(0, "sell", 1.0)])
        assert rb.fills[0].decision_price == want_buy
        assert rs.fills[0].decision_price == want_sell


def test_latency_shift_uses_quotes_within_latency():
    # buy at t=0 with 3 s latency; a new ask arrives at t=2 s inside latency
    frame = make_frame([0, 2000], [100.00, 100.00], [100.00, 100.50])
    eng = ExecutionEngine(zero_cost_config(latency_ms=3000.0))
    rep = eng.run(frame, [(0, "buy", 1.0)])
    assert rep.n_fills == 1
    f = rep.fills[0]
    assert f.fill_time == 3000.0
    assert f.quote_time == 2000.0          # quote inside the latency window
    assert f.fill_price == 100.50
    # decision price still only sees the t=0 quote
    assert f.decision_price == 100.00


# --------------------------------------------------------------------------- #
# (2) taker fills at touch + slippage (buy ask / sell bid)
# --------------------------------------------------------------------------- #
def test_taker_buy_fills_at_ask_plus_slippage():
    frame = make_frame([0], [100.00], [100.50])
    eng = ExecutionEngine(zero_cost_config(slippage_bps=2.0))
    f = eng.run(frame, [(0, "buy", 1.0)]).fills[0]
    assert f.touch == 100.50
    assert f.fill_price == pytest.approx(100.50 * (1 + 2.0 / 1e4), rel=1e-12)
    assert f.slip_price == pytest.approx(100.50 * 2.0 / 1e4, rel=1e-12)
    assert f.slip_bps == pytest.approx(2.0)
    assert f.fill_price > f.ask  # adverse: buy pays more than ask


def test_taker_sell_fills_at_bid_minus_slippage():
    frame = make_frame([0], [100.00], [100.50])
    eng = ExecutionEngine(zero_cost_config(slippage_bps=2.0))
    f = eng.run(frame, [(0, "sell", 1.0)]).fills[0]
    assert f.touch == 100.00
    assert f.fill_price == pytest.approx(100.00 * (1 - 2.0 / 1e4), rel=1e-12)
    assert f.fill_price < f.bid  # adverse: sell receives less than bid


def test_slippage_proportional_to_spread_component():
    bid, ask = 4050.00, 4050.30
    frame = make_frame([0], [bid], [ask])
    mid = (bid + ask) / 2.0
    spread_bps = (ask - bid) / mid * 1e4
    eng = ExecutionEngine(zero_cost_config(slippage_spread_frac=0.25))
    f = eng.run(frame, [(0, "buy", 1.0)]).fills[0]
    assert f.spread_bps == pytest.approx(spread_bps, rel=1e-12)
    want_slip_bps = 0.25 * spread_bps
    assert f.slip_bps == pytest.approx(want_slip_bps, rel=1e-9)
    assert f.fill_price == pytest.approx(
        ask * (1 + want_slip_bps / 1e4), rel=1e-9)


# --------------------------------------------------------------------------- #
# (3) stale quote => missed fill
# --------------------------------------------------------------------------- #
def test_stale_quote_missed_fill():
    frame = make_frame([0], [100.00], [100.50])
    eng = ExecutionEngine(zero_cost_config(max_quote_age_ms=10.0))
    rep = eng.run(frame, [(1000, "buy", 1.0)])  # arrival 1 s after the quote
    assert rep.n_fills == 0 and rep.n_missed == 1
    m = rep.missed[0]
    assert m.reason == "stale_quote"
    assert m.detail["quote_age_ms"] == pytest.approx(1000.0)

    # exactly at max age the quote is still usable (age <= max)
    rep2 = eng.run(frame, [(10, "buy", 1.0)])
    assert rep2.n_fills == 1 and rep2.n_missed == 0


def test_before_first_quote_missed_fill():
    frame = make_frame([1000], [100.00], [100.50])
    eng = ExecutionEngine(zero_cost_config())
    rep = eng.run(frame, [(500, "buy", 1.0)])
    assert rep.n_missed == 1
    assert rep.missed[0].reason == "before_first_quote"


def test_engine_sorts_decisions_and_preserves_ids():
    frame = make_frame([0, 10000], [100.00, 101.00], [100.50, 101.50])
    eng = ExecutionEngine(zero_cost_config())
    rep = eng.run(frame, [
        Decision(10000, Side.SELL, 1.0, id="later"),
        Decision(0, Side.BUY, 1.0, id="first"),
    ])
    assert [f.decision_id for f in rep.fills] == ["first", "later"]
    assert [f.fill_time for f in rep.fills] == [0.0, 10000.0]
    assert len(rep.decisions) == 2
    # fill order matches decision-time order, deterministically
    assert rep.fills[0].fill_price == 100.50
    assert rep.fills[1].fill_price == 101.00


# --------------------------------------------------------------------------- #
# (4) spread computation
# --------------------------------------------------------------------------- #
def test_spread_computation():
    frame = make_frame([0, 1000, 2000],
                       [100.00, 4050.00, 99.90],
                       [100.40, 4050.30, 100.00])
    eng = ExecutionEngine(zero_cost_config())
    rep = eng.run(frame, [(0, "buy", 1.0), (1000, "buy", 1.0),
                          (2000, "buy", 1.0)])
    assert rep.fills[0].spread_price == pytest.approx(0.40)
    assert rep.fills[0].spread_bps == pytest.approx(
        0.40 / 100.20 * 1e4, rel=1e-12)
    assert rep.fills[1].spread_price == pytest.approx(0.30)
    assert rep.fills[2].spread_price == pytest.approx(0.10)
    # frame-level stats
    s = rep.summary()["quotes"]
    assert s["spread_price_min"] == pytest.approx(0.10)
    assert s["spread_price_max"] == pytest.approx(0.40)
    assert s["spread_price_mean"] == pytest.approx((0.40 + 0.30 + 0.10) / 3.0)


# --------------------------------------------------------------------------- #
# (5) net PnL correctness - hand-computed round trips
# --------------------------------------------------------------------------- #
def test_round_trip_net_pnl_hand_computed():
    # quotes: t=0      bid 4050.00 ask 4050.30
    #         t=10000  bid 4055.00 ask 4055.30
    frame = make_frame([0, 10000],
                       [4050.00, 4055.00], [4050.30, 4055.30])
    eng = ExecutionEngine(zero_cost_config(slippage_bps=1.0))
    rep = eng.run(frame, [(0, "buy", 1.0), (10000, "sell", 1.0)])
    assert rep.n_fills == 2 and rep.n_missed == 0

    b = rep.fills[0]
    s = rep.fills[1]
    # buy fill = ask * (1 + 1bp), sell fill = bid * (1 - 1bp)
    assert b.fill_price == pytest.approx(4050.30 * 1.0001, rel=1e-12)
    assert s.fill_price == pytest.approx(4055.00 * 0.9999, rel=1e-12)

    want_pnl = 4055.00 * 0.9999 - 4050.30 * 1.0001   # = 3.88947
    assert want_pnl == pytest.approx(3.88947, abs=1e-9)
    assert rep.pnl_total_price == pytest.approx(want_pnl, abs=1e-9)
    assert rep.pnl_realized_price == pytest.approx(want_pnl, abs=1e-9)
    assert rep.pnl_unrealized_price == pytest.approx(0.0, abs=1e-12)
    assert rep.inventory_final == 0.0
    assert rep.exit_ref is None
    assert rep.cash_total == pytest.approx(want_pnl, abs=1e-9)

    # bps: relative to total traded notional (both legs)
    notional = 4050.30 * 1.0001 + 4055.00 * 0.9999
    assert rep.notional_total == pytest.approx(notional, rel=1e-12)
    assert rep.pnl_total_bps == pytest.approx(want_pnl / notional * 1e4,
                                              rel=1e-9)
    assert rep.costs_total == 0.0


def test_round_trip_pnl_with_per_side_costs():
    frame = make_frame([0, 10000],
                       [4050.00, 4055.00], [4050.30, 4055.30])
    eng = ExecutionEngine(zero_cost_config(slippage_bps=1.0, cost_bps=5.0))
    rep = eng.run(frame, [(0, "buy", 1.0), (10000, "sell", 1.0)])
    b, s = rep.fills[0], rep.fills[1]

    buy_gross = 4050.30 * 1.0001
    sell_gross = 4055.00 * 0.9999
    # cost is per side, in bps of the fill price
    assert b.cost_price == pytest.approx(buy_gross * 5.0 / 1e4, rel=1e-12)
    assert s.cost_price == pytest.approx(sell_gross * 5.0 / 1e4, rel=1e-12)
    assert b.net_price == pytest.approx(buy_gross * (1 + 5.0 / 1e4), rel=1e-12)
    assert s.net_price == pytest.approx(sell_gross * (1 - 5.0 / 1e4), rel=1e-12)

    want = sell_gross * (1 - 5e-4) - buy_gross * (1 + 5e-4)
    assert rep.pnl_total_price == pytest.approx(want, rel=1e-9)
    assert rep.costs_total == pytest.approx(
        buy_gross * 5e-4 + sell_gross * 5e-4, rel=1e-9)


def test_open_position_mtm_and_unrealized():
    frame = make_frame([0, 1000], [100.00, 102.00], [100.50, 102.50])
    eng = ExecutionEngine(zero_cost_config())  # no costs / slippage
    rep = eng.run(frame, [(0, "buy", 2.0)])
    assert rep.inventory_final == 2.0
    assert rep.exit_ref == 102.00            # long marked at last bid
    # unrealized = 2 * (last bid - buy fill at ask 100.50)
    assert rep.pnl_unrealized_price == pytest.approx(2.0 * (102.00 - 100.50))
    assert rep.pnl_realized_price == pytest.approx(0.0)
    assert rep.pnl_total_price == pytest.approx(2.0 * (102.00 - 100.50))

    rep2 = eng.run(frame, [(0, "sell", 2.0)])  # short marked at last ask
    assert rep2.inventory_final == -2.0
    assert rep2.exit_ref == 102.50
    assert rep2.pnl_total_price == pytest.approx(
        2.0 * (100.00 - 102.50))  # sold at 100, must buy back at 102.50


# --------------------------------------------------------------------------- #
# limit IOC (conservative, optional per spec)
# --------------------------------------------------------------------------- #
def test_limit_ioc_conservative_semantics():
    frame = make_frame([0], [100.00], [100.50])
    eng = ExecutionEngine(zero_cost_config())

    # marketable buy limit (ask 100.50 <= 100.75): fills at ask, not at the
    # limit; zero slippage because the limit binds.
    rep = eng.run(frame, [(0, "buy", 1.0, "limit_ioc", 100.75)])
    f = rep.fills[0]
    assert f.fill_price == 100.50 and f.slip_bps == 0.0 and f.slip_price == 0.0

    # marketable sell limit (bid 100.00 >= 99.50): fills at bid.
    rep = eng.run(frame, [(0, "sell", 1.0, "limit_ioc", 99.50)])
    assert rep.fills[0].fill_price == 100.00

    # not marketable at arrival -> IOC cancels: missed fill
    rep = eng.run(frame, [(0, "buy", 1.0, "limit_ioc", 100.30)])
    assert rep.n_fills == 0 and rep.n_missed == 1
    assert rep.missed[0].reason == "limit_not_marketable"

    rep = eng.run(frame, [(0, "sell", 1.0, "limit_ioc", 100.10)])
    assert rep.missed[0].reason == "limit_not_marketable"


def test_limit_ioc_evaluated_at_arrival_not_decision():
    # ask moves 100.50 -> 100.60 inside the latency window; the buy limit of
    # 100.55 was marketable at decision time but not at arrival -> cancelled.
    frame = make_frame([0, 1500], [100.00, 100.00], [100.50, 100.60])
    eng = ExecutionEngine(zero_cost_config(latency_ms=3000.0))
    rep = eng.run(frame, [(0, "buy", 1.0, "limit_ioc", 100.55)])
    assert rep.n_fills == 0 and rep.n_missed == 1
    assert rep.missed[0].reason == "limit_not_marketable"
    assert rep.missed[0].detail["ask"] == 100.60


def test_limit_ioc_requires_limit_price():
    eng = ExecutionEngine(zero_cost_config())
    frame = make_frame([0], [100.00], [100.50])
    with pytest.raises(ValueError):
        eng.run(frame, [(0, "buy", 1.0, "limit_ioc")])


# --------------------------------------------------------------------------- #
# (6) exposure tracking
# --------------------------------------------------------------------------- #
def test_exposure_tracking():
    # inventory: +2 (t0) -> +1 (t5000) -> 0 (t10000); frame runs to t15000
    frame = make_frame([0, 5000, 10000, 15000],
                       [100.00, 100.10, 100.20, 100.30],
                       [100.50, 100.60, 100.70, 100.80])
    eng = ExecutionEngine(zero_cost_config())
    rep = eng.run(frame, [
        (0, "buy", 2.0),
        (5000, "sell", 1.0),
        (10000, "sell", 1.0),
    ])
    assert rep.n_fills == 3
    e = rep.exposure_summary()
    assert e["inventory_final"] == 0.0
    assert e["max_abs_inventory"] == 2.0
    assert e["span_ms"] == 15000.0            # first fill -> end of frame
    assert e["in_market_ms"] == 10000.0       # [0,5000)+[5000,10000)
    assert e["flat_ms"] == 5000.0
    assert e["long_ms"] == 10000.0
    assert e["short_ms"] == 0.0
    # weighted: (2*5000 + 1*5000)/10000 over in-market; /span over whole span
    assert e["exposure_weighted_avg_inventory_in_market"] == pytest.approx(1.5)
    assert e["exposure_weighted_avg_inventory_over_span"] == pytest.approx(1.0)
    s = rep.summary()["exposure"]
    for k, v in e.items():
        assert abs(s[k] - v) < 1e-12, (k, s[k], v)


def test_short_exposure_tracking():
    frame = make_frame([0, 1000, 2000, 3000],
                       [100.00, 100.00, 100.00, 100.00],
                       [100.50, 100.50, 100.50, 100.50])
    eng = ExecutionEngine(zero_cost_config())
    rep = eng.run(frame, [(0, "sell", 1.5), (2000, "buy", 1.5)])
    e = rep.exposure_summary()
    assert e["short_ms"] == 2000.0 and e["long_ms"] == 0.0
    assert e["in_market_ms"] == 2000.0
    assert e["max_abs_inventory"] == 1.5
    assert e["flat_ms"] == 1000.0  # t2000..t3000 flat, frame ends at t3000


# --------------------------------------------------------------------------- #
# (7) determinism
# --------------------------------------------------------------------------- #
def test_determinism_same_inputs_identical_report():
    rng = np.random.default_rng(7)
    n = 4000
    base = np.linspace(4000.0, 4050.0, n)
    noise = rng.normal(0, 0.15, n)
    bid = base + noise
    ask = bid + np.abs(rng.normal(0.13, 0.02, n)) + 0.05
    ts = np.arange(n, dtype="int64") * 250
    frame = make_frame(ts, bid, ask)
    cfg = zero_cost_config(latency_ms=1.0, slippage_bps=0.2,
                           slippage_spread_frac=0.1, cost_bps=0.05)
    engine1 = ExecutionEngine(cfg)
    engine2 = ExecutionEngine(cfg)
    decisions = [(int(ts[i]), "buy" if i % 2 == 0 else "sell", 0.1)
                 for i in range(0, n, 200)]
    r1 = engine1.run(frame, decisions)
    r2 = engine2.run(frame, decisions)
    assert r1.summary() == r2.summary()
    assert [f.as_dict() for f in r1.fills] == [f.as_dict() for f in r2.fills]
    assert [m.as_dict() for m in r1.missed] == [m.as_dict() for m in r2.missed]
    assert r1.pnl_total_price == r2.pnl_total_price
    assert r1.summary()["pnl"] == r2.summary()["pnl"]


def test_empty_decisions_report():
    frame = make_frame([0, 1000], [100.00, 101.00], [100.50, 101.50])
    rep = ExecutionEngine(zero_cost_config()).run(frame, [])
    assert rep.n_fills == 0 and rep.n_missed == 0
    s = rep.summary()
    assert s["pnl"]["pnl_total_price"] == 0.0
    assert s["exposure"]["in_market_ms"] == 0.0
    assert rep.fills_df().empty


# --------------------------------------------------------------------------- #
# loader: formats, units, cleaning
# --------------------------------------------------------------------------- #
def test_loader_fxtm_real_file_schema():
    if not FXTM_FILE.exists():
        pytest.skip("FXTM tick parquet not present")
    for path in (FXTM_FILE, FXTM_FILE2):
        ndf = load_tick_frame(path)
        assert list(ndf.columns) == ["ts", "bid", "ask"]
        assert ndf["ts"].dtype.kind == "i"
        assert ndf["bid"].dtype.kind == "f" and ndf["ask"].dtype.kind == "f"
        assert (np.diff(ndf["ts"].to_numpy()) >= 0).all()
        assert (ndf["ask"] > ndf["bid"]).all()
        assert (ndf["bid"] > 0).all()
        meta = ndf.attrs["execution_reality"]
        assert meta["time_column"] == "ts_utc"
        assert meta["bid_column"] == "bid"
        assert meta["ask_column"] == "ask"
        assert "volume" in meta["extra_columns_ignored"]
        assert "flags" in meta["extra_columns_ignored"]
        # no rows dropped on clean real data
        assert meta["dropped_rows"]["nan_quote"] == 0
        assert meta["dropped_rows"]["crossed_or_nonpositive"] == 0
        # sanity on real magnitudes
        assert 1.7e12 < float(ndf["ts"].iloc[0]) < 1.8e12


def test_loader_duka_style_ms():
    ms = np.array([1_785_800_000_000 + i * 1000 for i in range(3)], dtype="int64")
    duka = pd.DataFrame({"ms": ms, "ask": [100.5, 100.6, 100.7],
                         "bid": [100.0, 100.1, 100.2],
                         "ask_vol": [1, 2, 3], "bid_vol": [4, 5, 6]})
    ndf = normalize_frame(duka)
    assert list(ndf.columns) == ["ts", "bid", "ask"]
    assert (ndf["ts"].to_numpy() == ms).all()
    meta = ndf.attrs["execution_reality"]
    assert meta["time_column"] == "ms"
    assert "ask_vol" in meta["extra_columns_ignored"]


def test_loader_numeric_units_and_datetime_columns():
    # seconds -> ms
    s = pd.DataFrame({"time": [1_700_000_000, 1_700_000_001],
                      "bid": [1.0, 1.1], "ask": [1.2, 1.3]})
    ndf = normalize_frame(s)
    assert ndf["ts"].iloc[0] == 1_700_000_000_000
    # explicit ms unit for small synthetic values
    s2 = pd.DataFrame({"time": [1000, 2000], "bid": [1.0, 1.1],
                       "ask": [1.2, 1.3]})
    ndf2 = normalize_frame(s2, time_unit="ms")
    assert ndf2["ts"].tolist() == [1000, 2000]
    # tz-aware datetime64[ms] (FXTM storage format)
    d = pd.DataFrame({
        "ts_utc": pd.date_range("2026-08-04", periods=3, freq="1s", tz="UTC"),
        "bid": [1.0, 1.1, 1.2], "ask": [1.3, 1.4, 1.5]})
    ndf3 = normalize_frame(d)
    assert ndf3["ts"].tolist() == [int(t.timestamp() * 1000)
                                   for t in d["ts_utc"]]
    # naive datetime64 and python-datetime strings also accepted
    d4 = pd.DataFrame({"timestamp": pd.to_datetime(
        ["2026-08-04 01:00:00", "2026-08-04 01:00:01"]),
        "bid": [1.0, 1.1], "ask": [1.2, 1.3]})
    ndf4 = normalize_frame(d4)
    assert ndf4["ts"].iloc[1] - ndf4["ts"].iloc[0] == 1000


def test_loader_cleaning_and_stable_sort():
    df = pd.DataFrame({
        "ts": [5, 3, 5, 4, np.nan],
        "bid": [100.0, 101.0, np.nan, 102.0, 103.0],
        "ask": [100.5, 100.0, 100.5, 102.5, 103.5],  # row1 crossed
    })
    ndf = normalize_frame(df, time_unit="ms")
    # kept rows: ts=5 (bid 100, crossed? no - row 1 ts=3 crossed, row 2 nan,
    # row 4 bad ts); so survivors are ts4 (102/102.5) and ts5 (100/100.5)
    assert ndf["ts"].tolist() == [4, 5]          # stable ascending
    assert ndf["bid"].tolist() == [102.0, 100.0]
    assert ndf["ask"].tolist() == [102.5, 100.5]
    assert (ndf["ask"] > ndf["bid"]).all()
    meta = ndf.attrs["execution_reality"]
    assert meta["dropped_rows"]["nan_quote"] == 2    # bad ts row + nan bid
    assert meta["dropped_rows"]["crossed_or_nonpositive"] == 1

    # duplicate timestamps are preserved (as-of lookup picks the latest one)
    dup = pd.DataFrame({"ts": [5, 5, 6], "bid": [1.0, 1.5, 2.0],
                        "ask": [2.0, 2.5, 3.0]})
    nd = normalize_frame(dup, time_unit="ms")
    assert nd["ts"].tolist() == [5, 5, 6]
    assert nd["bid"].tolist() == [1.0, 1.5, 2.0]

    with pytest.raises(ValueError):
        normalize_frame(pd.DataFrame({"time": [1, 2], "bid": [1.0, 2.0]}))
    with pytest.raises(ValueError):
        normalize_frame(pd.DataFrame({"bid": [1.0], "ask": [2.0]}))
    # a non-positive quote row is dropped (not fatal) ...
    badrow = normalize_frame(pd.DataFrame({"ts": [1, 2], "bid": [1.0, 0.0],
                                           "ask": [2.0, 3.0]}), time_unit="ms")
    assert badrow["ts"].tolist() == [1]
    assert badrow.attrs["execution_reality"]["dropped_rows"]["crossed_or_nonpositive"] == 1
    # ... but a frame with no usable quotes at all fails closed
    all_bad = pd.DataFrame({"ts": [1, 2], "bid": [5.0, 5.0], "ask": [4.0, 4.0]})
    with pytest.raises(ValueError):
        normalize_frame(all_bad, time_unit="ms")


def test_invalid_frame_fails_closed():
    eng = ExecutionEngine(zero_cost_config())
    with pytest.raises(ValueError):
        eng.run(pd.DataFrame({"ts": [1], "bid": [2.0]}), [])  # no ask
    crossed = make_frame([0], [101.0], [100.0])
    with pytest.raises(ValueError):
        eng.run(crossed, [])
    bad = make_frame([0], [100.0], [np.nan])
    with pytest.raises(ValueError):
        eng.run(bad, [])


def test_config_validation():
    with pytest.raises(ValueError):
        ExecutionConfig(latency_ms=-1.0)
    with pytest.raises(ValueError):
        ExecutionConfig(max_quote_age_ms=-1)
    with pytest.raises(ValueError):
        ExecutionConfig(slippage_bps=-0.1)
    with pytest.raises(ValueError):
        ExecutionConfig(decision_price_mode="last")
    with pytest.raises(ValueError):
        ExecutionConfig(cost_bps=-1)


def test_parse_decision_rejects_garbage():
    eng = ExecutionEngine(zero_cost_config())
    frame = make_frame([0], [100.0], [100.5])
    with pytest.raises(ValueError):
        eng.run(frame, [(0, "hold", 1.0)])          # unknown side
    with pytest.raises(ValueError):
        eng.run(frame, [(0, "buy", -1.0)])          # non-positive size
    with pytest.raises(ValueError):
        eng.run(frame, [(0, "buy", 1.0, "pegged")])  # unknown order type
    with pytest.raises(TypeError):
        eng.run(frame, [(0, 123, 1.0)])             # bad side type


# --------------------------------------------------------------------------- #
# (8) end-to-end run on a real slice of the FXTM tick file (read-only)
# --------------------------------------------------------------------------- #
def test_e2e_real_fxtm_slice():
    if not FXTM_FILE.exists():
        pytest.skip("FXTM tick parquet not present")
    raw = pd.read_parquet(FXTM_FILE, columns=["ts_utc", "bid", "ask"])
    ndf = normalize_frame(raw)
    assert len(ndf) > 100_000

    # deterministic contiguous slice
    lo, hi = 20_000, 30_000
    sl = ndf.iloc[lo:hi].reset_index(drop=True)
    ts = sl["ts"].to_numpy(dtype="int64")
    cfg = zero_cost_config(latency_ms=0.0, slippage_bps=0.1,
                           slippage_spread_frac=0.05, cost_bps=0.05)
    eng = ExecutionEngine(cfg)
    decisions = [
        (int(ts[i]), "buy" if k % 2 == 0 else "sell", 0.1)
        for k, i in enumerate(range(0, len(ts), 500))
    ]
    assert len(decisions) == 20
    rep = eng.run(sl, decisions)

    assert rep.n_decisions == 20
    assert rep.n_fills == 20 and rep.n_missed == 0
    assert rep.inventory_final == 0.0

    # order book sanity per fill
    for f in rep.fills:
        assert f.quote_time <= f.fill_time
        assert f.spread_price > 0.0
        assert 0.3 < f.spread_bps < 1.5            # realistic XAUUSD spread
        assert f.slip_bps == pytest.approx(
            0.1 + 0.05 * f.spread_bps, rel=1e-9)
        if f.side is Side.BUY:
            assert f.fill_price > f.ask
            assert f.fill_price == pytest.approx(
                f.ask * (1 + f.slip_bps / 1e4), rel=1e-9)
        else:
            assert f.fill_price < f.bid
            assert f.fill_price == pytest.approx(
                f.bid * (1 - f.slip_bps / 1e4), rel=1e-9)
        # decision price sits inside the decision-time quote
        assert f.decision_price is not None

    # alternating 0.1 buys/sells -> exposure alternates 0.1 and 0
    e = rep.exposure_summary()
    assert e["max_abs_inventory"] == pytest.approx(0.1)
    assert e["inventory_final"] == 0.0
    # window: [first fill, end of tick data]; inventory is flat only after
    # the final sell, so in_market == last_fill - first_fill (telescoping)
    first_fill = rep.fills[0].fill_time
    last_fill = rep.fills[-1].fill_time
    assert e["span_ms"] == pytest.approx(rep.last_quote_time - first_fill)
    # inventory is open only from each buy (even fill) to its closing sell
    # (odd fill); gaps between sells and the next buy are flat
    open_legs = sum(
        rep.fills[j + 1].fill_time - rep.fills[j].fill_time
        for j in range(0, len(rep.fills) - 1, 2)
    )
    assert e["in_market_ms"] == pytest.approx(open_legs)
    assert e["flat_ms"] == pytest.approx(
        rep.last_quote_time - first_fill - open_legs)

    p = rep.summary()["pnl"]
    assert p["notional_total_price"] > 0.0
    assert abs(p["pnl_total_price"]) < p["notional_total_price"]
    assert rep.costs_total > 0.0
    # frame-level stats are consistent with the full cleaned frame
    assert rep.n_quotes == len(sl)

    # determinism on the real slice
    rep2 = ExecutionEngine(cfg).run(sl, decisions)
    assert rep.summary() == rep2.summary()


def test_e2e_stale_quotes_miss_on_real_data():
    """On the real file, a decision during a quote gap must not phantom-fill."""
    if not FXTM_FILE.exists():
        pytest.skip("FXTM tick parquet not present")
    ndf = load_tick_frame(FXTM_FILE)
    sl = ndf.iloc[5000:8000].reset_index(drop=True)
    # decision placed well after the last quote of the slice (simulated gap)
    eng = ExecutionEngine(zero_cost_config(max_quote_age_ms=1.0))
    last_ts = float(sl["ts"].iloc[-1])
    rep = eng.run(sl, [(last_ts + 50_000, "buy", 0.1)])
    assert rep.n_fills == 0 and rep.n_missed == 1
    assert rep.missed[0].reason == "stale_quote"


def test_timestamp_decision_times():
    """Decisions may also carry pandas Timestamps / datetime64."""
    frame = make_frame([0, 1000], [100.0, 100.5], [100.4, 100.9])
    t0 = pd.Timestamp("2026-08-04T00:00:00", tz="UTC")
    base_ms = int(t0.value // 1_000_000)
    frame2 = make_frame([base_ms, base_ms + 1000], [100.0, 100.5],
                        [100.4, 100.9])
    eng = ExecutionEngine(zero_cost_config())
    rep = eng.run(frame2, [(t0, "buy", 1.0),
                           (t0 + pd.Timedelta(seconds=1), "sell", 1.0)])
    assert rep.n_fills == 2
    assert rep.fills[0].fill_price == 100.4
    assert rep.fills[1].fill_price == 100.5
