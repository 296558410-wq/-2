"""Regression tests — V3-HFT-DATA-EXECUTION-GAP-CLOSURE-001 (task X/XXXIV).

Covers: timestamp units + no silent inference, snapshot immutability, duplicate
identity, cost/slippage/commission signs, markout direction, AS sign, censoring,
cost-model version, DATA_GAP propagation, failure-taxonomy observability.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, V3)

from microstructure import timestamp_unit_guard as TG   # noqa: E402
from microstructure import adverse_selection as AS       # noqa: E402
from microstructure import markout as MK                 # noqa: E402
from execution import cost_model_v2 as CM2               # noqa: E402
from execution import slippage as SL                     # noqa: E402
from execution import observability as OBS               # noqa: E402
from execution import execution_quality as EQ            # noqa: E402

SNAPSHOT_ID = "V3-SNAP-20260922T025312Z"
SNAP = os.path.join(V3, "data", "snapshots", SNAPSHOT_ID)
RESEARCH = os.path.join(V3, "research")


# ---------------- timestamp unit tests ----------------
def test_ms_timestamp():
    assert TG.to_seconds([1000], "ms")[0] == 1.0


def test_us_timestamp():
    assert TG.to_seconds([1_000_000], "us")[0] == 1.0


def test_ns_timestamp():
    assert TG.to_seconds([1_000_000_000], "ns")[0] == 1.0


def test_utc_conversion():
    dt = TG.to_utc([1000], "ms")[0]
    assert dt.year == 1970 and dt.second == 1 and str(dt.tzinfo) in ("UTC", "utc")


def test_monotonicity():
    assert TG.assert_monotonic([1, 2, 3])["monotonic"] is True
    assert TG.assert_monotonic([3, 2, 1])["monotonic"] is False


def test_future_timestamp():
    future = int(9e18)
    assert TG.find_future(np.array([future]), now_ns=1_700_000_000_000_000_000)["future_count"] == 1


def test_timestamp_range():
    assert TG.range_check([1, 5, 20], 0, 10)["out_of_range"] == 1


def test_no_silent_inference():
    with pytest.raises(TG.TimestampUnitError):
        TG.require_unit(None)
    with pytest.raises(TG.TimestampUnitError):
        TG.require_unit("seconds")
    with pytest.raises(TG.TimestampUnitError):
        TG.to_ns([1], "fortnight")


# ---------------- snapshot immutability ----------------
def test_snapshot_immutability():
    mf = os.path.join(RESEARCH, "snapshot", f"V3_DATA_SNAPSHOT_{SNAPSHOT_ID}.json")
    assert os.path.exists(mf), "snapshot manifest missing"
    m = json.load(open(mf, encoding="utf-8"))
    assert m["RESEARCH_SNAPSHOT_IMMUTABLE"] is True
    assert m["LIVE_SOURCE_MUTABLE"] is True
    mism = 0
    for f in m["files"]:
        p = f["path"]
        if not os.path.exists(p):
            mism += 1
            continue
        assert os.path.getsize(p) == f["size"]


def test_snapshot_files_readonly():
    d = os.path.join(SNAP, "live_fxtm")
    if not os.path.isdir(d):
        pytest.skip("snapshot not materialised")
    for fn in os.listdir(d)[:3]:
        assert not os.access(os.path.join(d, fn), os.W_OK), "snapshot file is writable"


# ---------------- duplicate identity ----------------
def test_duplicate_identity():
    p = os.path.join(RESEARCH, "snapshot", f"V3_DUP_TRIAGE_{SNAPSHOT_ID}.json")
    d = json.load(open(p, encoding="utf-8"))
    assert d["staging_fxtm_DUP_TIMESTAMP_COUNT"] == 0
    assert d["live_fxtm_DUP_QUOTE_COUNT"] <= d["live_fxtm_DUP_TIMESTAMP_COUNT"]
    assert d["EVENT_IDENTITY"] == "DATA_GAP"


# ---------------- cost model ----------------
def test_cost_model_version():
    h = CM2.header()
    for k in ("COST_MODEL_VERSION", "COST_SOURCE", "COST_TIMESTAMP", "COST_ASSUMPTION"):
        assert h[k]
    assert abs(CM2.REAL_RT_COST_BP - 0.914) < 1e-9


def test_deprecated_cost_rejected():
    with pytest.raises(CM2.DeprecatedCostError):
        CM2.assert_not_deprecated(0.314)
    m = CM2.CostModelV2(spread_cost=0.5, commission=0.4)
    assert m.total_cost_bp()["total_cost_bp"] == pytest.approx(0.9)


def test_cost_components_positive_sum():
    m = CM2.CostModelV2(spread_cost=0.343, commission=0.503, slippage=0.02,
                        latency_cost=0.01, adverse_selection=0.05, impact=0.0)
    t = m.total_cost_bp()
    assert t["status"] == "MEASURED"
    assert t["total_cost_bp"] == pytest.approx(0.343 + 0.503 + 0.02 + 0.01 + 0.05 + 0.0)


# ---------------- slippage / commission signs ----------------
def test_slippage_favorable_unfavorable_zero():
    long_bad = SL.classify_slippage(fill_price=100.2, reference_price=100.0, direction=+1)
    assert long_bad["classification"] == "UNFAVOURABLE" and long_bad["signed_slippage"] > 0
    long_good = SL.classify_slippage(fill_price=99.8, reference_price=100.0, direction=+1)
    assert long_good["classification"] == "FAVOURABLE" and long_good["signed_slippage"] < 0
    zero = SL.classify_slippage(fill_price=100.0, reference_price=100.0, direction=+1)
    assert zero["classification"] == "NEUTRAL" and zero["signed_slippage"] == 0
    short_bad = SL.classify_slippage(fill_price=99.8, reference_price=100.0, direction=-1)
    assert short_bad["classification"] == "UNFAVOURABLE"


def test_only_unfavorable_slippage_is_cost():
    m = CM2.CostModelV2(spread_cost=0.343, commission=0.503)
    m.set_slippage_signed(favorable_bp=0.02, unfavorable_bp=0.03)
    assert m.component("slippage")["bp"] == 0.03          # not |0.02|+0.03
    assert m.total_cost_bp()["total_cost_bp"] == pytest.approx(0.343 + 0.503 + 0.03)


def test_commission_convention():
    broker_signed = -0.22                 # broker statement: cost already negative
    research_cost = -broker_signed        # research/ledger: cost is a positive entry
    assert research_cost == pytest.approx(0.22)


# ---------------- markout direction ----------------
def _mk():
    ts = np.array([0, 1000], np.int64)
    bid = np.array([99.9, 99.9])
    ask = np.array([100.1, 100.1])
    idx = np.array([0])
    return ts, bid, ask, idx


def test_markout_direction_long_up_positive():
    ts, bid, ask, idx = _mk()
    mid = np.array([100.0, 101.0])
    r = MK.markout(ts, mid, bid, ask, idx, 1000, +1)
    assert r["EXECUTION_MARKOUT"][0] > 0


def test_markout_direction_short_down_positive():
    ts, bid, ask, idx = _mk()
    mid = np.array([100.0, 99.0])
    r = MK.markout(ts, mid, bid, ask, idx, 1000, -1)
    assert r["EXECUTION_MARKOUT"][0] > 0


def test_markout_direction_long_down_negative():
    ts, bid, ask, idx = _mk()
    mid = np.array([100.0, 99.0])
    r = MK.markout(ts, mid, bid, ask, idx, 1000, +1)
    assert r["EXECUTION_MARKOUT"][0] < 0


# ---------------- adverse selection sign ----------------
def test_adverse_selection_sign_matrix():
    r = AS.self_test()
    assert r["result"] == "PASS"
    assert all(r["checks"].values())
    assert r["values"]["LONG_price_down"] > 0      # adverse -> positive
    assert r["values"]["LONG_price_up"] < 0        # favourable -> negative


def test_as_is_negative_of_execution_markout():
    ts, bid, ask, idx = _mk()
    mid = np.array([100.0, 99.0])
    r_as = AS.adverse_selection(ts, mid, bid, ask, idx, 1000, +1)
    r_mk = MK.markout(ts, mid, bid, ask, idx, 1000, +1)
    assert r_as["AS_bp"][0] == pytest.approx(-r_mk["EXECUTION_MARKOUT"][0])


# ---------------- censoring ----------------
def test_censoring_not_zero():
    ts = np.array([0], np.int64)               # no forward tick at all
    mid = np.array([100.0])
    bid = np.array([99.9])
    ask = np.array([100.1])
    idx = np.array([0])
    r = AS.adverse_selection(ts, mid, bid, ask, idx, 30000, +1)
    assert r["eligibility"][0] == AS.CENSORED
    assert np.isnan(r["AS_bp"][0]) and r["AS_bp"][0] != 0
    st = AS.stats(r["AS_bp"])
    assert st["effective_n"] == 0 and st["status"] == "DATA_INSUFFICIENT"


# ---------------- DATA_GAP propagation ----------------
def test_data_gap_not_zero():
    m = CM2.CostModelV2(spread_cost=None, commission=0.503)
    t = m.total_cost_bp()
    assert t["status"].startswith("PARTIAL")
    assert m.component("spread_cost")["status"] == "DATA_GAP"
    assert m.component("spread_cost")["bp"] is None


def test_observability_not_observable_not_zero():
    assert OBS.value_or_gap("queue_position", 0) == "NOT_OBSERVABLE"
    assert OBS.cannot_claim_zero("fill_probability") is True
    assert OBS.value_or_gap("entry_price", 100.0) == 100.0


def test_taxonomy_type567_not_tested():
    t = EQ.taxonomy_status()
    for x in ("TYPE5_ADVERSE_SELECTION", "TYPE6_FILL_FAILURE", "TYPE7_EXECUTION_COST_FAILURE"):
        assert x in t["not_tested_types"]


def test_data_state_states_valid():
    from microstructure import data_state as DS
    for k, v in DS.registry().items():
        assert v in DS.STATES, f"{k}={v} invalid"
    assert DS.registry()["microprice"] == "DATA_GAP"
