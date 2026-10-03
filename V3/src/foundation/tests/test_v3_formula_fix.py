"""V3-HFT-CALIBRATION-FORMULA-FIX-001 regression tests (A-I).

Standalone:  python foundation/tests/test_v3_formula_fix.py
Exit 0 iff every executed case passes. No broker call, no order_send.

A  fill price already contains bid/ask -> spread must NOT be charged twice
B  favourable slippage must stay favourable (no abs())
C  MT5 commission<0 (cost) -> NET decreases, sign not inverted
D  commission=0 handled
E  swap=0 handled
F  LONG and SHORT both correct
G  different contract size / volume scale correctly (broker spec units)
H  the frozen 20 round trips recompute offline (old formula reproducible)
I  broker realised P&L reconciles with independent broker facts
"""
from __future__ import annotations
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.dirname(os.path.dirname(HERE))
if V3 not in sys.path:
    sys.path.insert(0, V3)

from foundation import pnl_accounting as PNA  # noqa: E402

RESULTS = []


def case(fn):
    def wrap():
        try:
            note = fn()
            RESULTS.append((fn.__name__, "PASS", note or ""))
        except SkipTest as s:
            RESULTS.append((fn.__name__, "SKIP", str(s)))
        except Exception as e:  # noqa: BLE001
            RESULTS.append((fn.__name__, "FAIL", f"{type(e).__name__}:{e}"))
    wrap.__name__ = fn.__name__
    return wrap


class SkipTest(Exception):
    pass


def acc(**kw):
    """Small helper: XAUUSD-style spec unless overridden."""
    base = dict(direction="LONG", volume=0.01, contract_size=100.0,
                tick_size=0.01, tick_value=1.0,
                profit_currency="USD", account_currency="USD")
    base.update(kw)
    return PNA.round_trip_accounting(**base)


BID, ASK = 3300.00, 3300.18
MID = (BID + ASK) / 2.0


# ---------------- A ----------------
def test_a_spread_not_double_charged():
    """Long entry filled at ask, exit filled at bid: net is exactly -1 spread."""
    r = acc(entry_fill_price=ASK, exit_fill_price=BID, entry_ref_price=ASK, exit_ref_price=BID,
            entry_bid=BID, entry_ask=ASK, exit_bid=BID, exit_ask=ASK,
            entry_mid=MID, exit_mid=MID, commission=0.0, swap=0.0,
            broker_gross_profit=BID - ASK)
    assert abs(r["net_pnl"] - (-0.18)) < 1e-12, r["net_pnl"]
    assert abs(r["gross_pnl_usd"] - (-0.18)) < 1e-12
    assert abs(r["entry_spread_price"] - 0.18) < 1e-12
    assert r["spread_slippage_basis"] == "EMBEDDED_IN_FILL_PRICE_NOT_DEDUCTED"
    old = PNA.old_formula_net(direction="LONG", entry_fill_price=ASK, exit_fill_price=BID,
                              spread=0.18, entry_slippage=0.0, exit_slippage=0.0, commission=0.0)
    assert abs(old - (-0.36)) < 1e-12, old  # old formula charged the spread twice
    return f"corrected={r['net_pnl']:.4f} vs old={old:.4f} (1x spread, not 2x)"


# ---------------- B ----------------
def test_b_favourable_slippage_stays_favourable():
    """Fills better than the requested price must INCREASE net, never be costed."""
    entry_fill, exit_fill = ASK - 0.08, BID + 0.16
    r = acc(entry_fill_price=entry_fill, exit_fill_price=exit_fill,
            entry_ref_price=ASK, exit_ref_price=BID,
            entry_bid=BID, entry_ask=ASK, exit_bid=BID, exit_ask=ASK,
            entry_mid=MID, exit_mid=MID, commission=0.0, swap=0.0,
            broker_gross_profit=exit_fill - entry_fill)
    assert abs(r["entry_slippage_adverse_price"] - (-0.08)) < 1e-12
    assert abs(r["exit_slippage_adverse_price"] - (-0.16)) < 1e-12
    assert abs(r["net_pnl"] - 0.06) < 1e-12, r["net_pnl"]
    at_ref = PNA.signed_price_move("LONG", ASK, BID)
    assert r["net_pnl"] > at_ref, "favourable slippage must add value"
    old = PNA.old_formula_net(direction="LONG", entry_fill_price=entry_fill,
                              exit_fill_price=exit_fill, spread=0.18,
                              entry_slippage=-0.08, exit_slippage=-0.16, commission=0.0)
    assert old < r["net_pnl"], "old abs() must be visibly worse"
    return f"corrected={r['net_pnl']:.4f} old={old:.4f} (favourable kept)"


# ---------------- C ----------------
def test_c_negative_commission_decreases_net():
    """Broker commission -0.22 per round trip is a COST."""
    r = acc(entry_fill_price=ASK, exit_fill_price=ASK + 1.00, entry_ref_price=ASK,
            exit_ref_price=ASK + 1.00, entry_bid=BID, entry_ask=ASK,
            exit_bid=ASK - 0.18 + 1.00, exit_ask=ASK + 1.00,
            entry_mid=MID, exit_mid=ASK + 1.00 - 0.09,
            commission=-0.22, swap=0.0, broker_gross_profit=1.00)
    assert abs(r["gross_pnl_usd"] - 1.00) < 1e-12
    assert abs(r["net_pnl"] - 0.78) < 1e-12, r["net_pnl"]
    assert r["net_pnl"] < r["gross_pnl_usd"], "a negative commission must reduce net"
    old = PNA.old_formula_net(direction="LONG", entry_fill_price=ASK, exit_fill_price=ASK + 1.00,
                              spread=0.18, entry_slippage=0.0, exit_slippage=0.0, commission=-0.22)
    assert old > r["gross_pnl_usd"], "old formula inverted the commission into a credit"
    return f"corrected={r['net_pnl']:.4f} old={old:.4f} (no sign inversion)"


# ---------------- D ----------------
def test_d_zero_commission():
    r = acc(entry_fill_price=ASK, exit_fill_price=ASK + 1.00, entry_ref_price=ASK,
            exit_ref_price=ASK + 1.00, commission=0.0, swap=0.0, broker_gross_profit=1.00)
    assert abs(r["net_pnl"] - r["gross_pnl_usd"]) < 1e-12
    assert r["net_pnl_status"] == "OK"
    return "commission=0 -> net == gross"


# ---------------- E ----------------
def test_e_zero_swap():
    base = dict(entry_fill_price=ASK, exit_fill_price=ASK + 1.00, entry_ref_price=ASK,
                exit_ref_price=ASK + 1.00, commission=-0.22)
    r0 = acc(swap=0.0, broker_gross_profit=1.00, **base)
    r1 = acc(swap=-0.50, broker_gross_profit=1.00, **base)
    assert abs(r0["net_pnl"] - 0.78) < 1e-12
    assert abs(r1["net_pnl"] - (r0["net_pnl"] - 0.50)) < 1e-12
    return f"swap=0 -> {r0['net_pnl']:.4f}; swap=-0.5 -> {r1['net_pnl']:.4f}"


# ---------------- F ----------------
def test_f_long_and_short_symmetric():
    long_r = acc(direction="LONG", entry_fill_price=ASK, exit_fill_price=ASK + 1.00,
                 entry_ref_price=ASK, exit_ref_price=ASK + 1.00, commission=-0.22, swap=0.0,
                 broker_gross_profit=1.00)
    short_r = acc(direction="SHORT", entry_fill_price=BID, exit_fill_price=BID - 1.00,
                  entry_ref_price=BID, exit_ref_price=BID - 1.00, commission=-0.22, swap=0.0,
                  broker_gross_profit=1.00)
    assert abs(long_r["net_pnl"] - 0.78) < 1e-12
    assert abs(short_r["net_pnl"] - 0.78) < 1e-12
    mirror = acc(direction="SHORT", entry_fill_price=BID, exit_fill_price=BID + 1.00,
                 entry_ref_price=BID, exit_ref_price=BID + 1.00, commission=0.0, swap=0.0,
                 broker_gross_profit=-1.00)
    assert abs(mirror["net_pnl"] - (-1.00)) < 1e-12
    return "LONG +1.00 and SHORT +1.00 both net 0.78; mirrored SHORT nets -1.00"


# ---------------- G ----------------
def test_g_contract_size_and_volume_scale():
    r1 = acc(volume=0.01, contract_size=100.0, entry_fill_price=BID, exit_fill_price=BID + 1.00,
             entry_ref_price=BID, exit_ref_price=BID + 1.00, commission=0.0, swap=0.0,
             broker_gross_profit=1.00)
    r10 = acc(volume=0.10, contract_size=100.0, entry_fill_price=BID, exit_fill_price=BID + 1.00,
              entry_ref_price=BID, exit_ref_price=BID + 1.00, commission=0.0, swap=0.0,
              broker_gross_profit=10.00)
    rsmall = acc(volume=0.01, contract_size=10.0, entry_fill_price=BID, exit_fill_price=BID + 1.00,
                 entry_ref_price=BID, exit_ref_price=BID + 1.00, commission=0.0, swap=0.0,
                 broker_gross_profit=0.10)
    assert abs(r1["price_unit_usd"] - 1.0) < 1e-12
    assert abs(r1["net_pnl"] - 1.0) < 1e-12
    assert abs(r10["price_unit_usd"] - 10.0) < 1e-12 and abs(r10["net_pnl"] - 10.0) < 1e-12
    assert abs(rsmall["price_unit_usd"] - 0.1) < 1e-12 and abs(rsmall["net_pnl"] - 0.10) < 1e-9
    # tick metadata cross-check: consistent spec -> PASS
    assert r1["unit_status"] == "PASS", r1["unit_status"]
    bad = acc(entry_fill_price=BID, exit_fill_price=BID + 1.00, entry_ref_price=BID,
              exit_ref_price=BID + 1.00, commission=0.0, swap=0.0, tick_value=0.1,
              broker_gross_profit=1.00)
    assert bad["unit_status"] == "DATA_GAP_TICK_VALUE_INCONSISTENT", bad["unit_status"]
    return "u=1.0/10.0/0.1 correct; tick-metadata mismatch flagged as DATA_GAP"


# ---------------- helpers for H / I ----------------
def _load_recompute():
    path = os.path.join(V3, "audit", "v3_formula_fix_recompute.py")
    if not os.path.exists(path):
        raise SkipTest("audit/v3_formula_fix_recompute.py not present")
    spec = importlib.util.spec_from_file_location("v3_formula_fix_recompute", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for req in (mod.LEDGER, mod.REGISTRY, mod.PROBE):
        if not os.path.exists(req):
            raise SkipTest(f"frozen input missing: {os.path.basename(req)}")
    return mod


# ---------------- H ----------------
def test_h_frozen_20_offline_recompute():
    mod = _load_recompute()
    s = mod.recompute()
    assert s["n_roundtrips"] == 20, s["n_roundtrips"]
    assert s["OLD_FORMULA_REPRODUCED_ALL"] is True, "old formula must reproduce the frozen data"
    assert s["CORRECTED_RECONCILED_ALL"] is True
    assert abs(s["OLD_MODEL_NET_MEAN"] - (-0.1375)) < 1e-9, s["OLD_MODEL_NET_MEAN"]
    assert abs(s["CORRECTED_MODEL_NET_MEAN"] - (-0.372)) < 1e-9, s["CORRECTED_MODEL_NET_MEAN"]
    assert abs(s["BROKER_NET_MEAN"] - (-0.372)) < 1e-9, s["BROKER_NET_MEAN"]
    assert s["MAX_ABS_RESIDUAL"] < 1e-6, s["MAX_ABS_RESIDUAL"]
    assert s["RAW_DATA_IMMUTABLE"] is True
    return (f"n=20 old_mean={s['OLD_MODEL_NET_MEAN']:.4f} "
            f"corrected_mean={s['CORRECTED_MODEL_NET_MEAN']:.4f} "
            f"max_resid={s['MAX_ABS_RESIDUAL']:.2e}")


# ---------------- I ----------------
def test_i_broker_realized_reconciliation():
    mod = _load_recompute()
    s = mod.recompute()
    probe = mod.load_probe()
    gross = sum(float(d.get("profit") or 0.0) for d in probe["deals"])
    comm = sum(float(d.get("commission") or 0.0) for d in probe["deals"])
    swap = sum(float(d.get("swap") or 0.0) for d in probe["deals"])
    assert abs(s["BROKER_GROSS_SUM"] - gross) < 1e-9
    assert abs(s["BROKER_COMMISSION_SUM"] - comm) < 1e-9
    assert abs(s["BROKER_SWAP_SUM"] - swap) < 1e-9
    assert abs(s["BROKER_NET_SUM"] - (gross + comm + swap)) < 1e-9
    assert abs(s["BROKER_NET_SUM"] - (-7.44)) < 1e-9, s["BROKER_NET_SUM"]
    # independent anchor: the pilot's own balance delta
    pilot = os.path.join(V3, "state", "V3_CALIBRATION_PILOT.json")
    if os.path.exists(pilot):
        with open(pilot, encoding="utf-8") as f:
            p = json.load(f)
        delta = p["account_after"]["balance"] - p["account_before"]["balance"]
        assert abs(delta - s["BROKER_NET_SUM"]) < 1e-6, (delta, s["BROKER_NET_SUM"])
    for r in s["rows"]:
        assert r["reconciliation_residual"] is None or abs(r["reconciliation_residual"]) < 1e-6
    return f"broker net {s['BROKER_NET_SUM']:.2f} == deal profit+fees == balance delta"


def run() -> int:
    tests = [fn for name, fn in sorted(globals().items())
             if name.startswith("test_") and callable(fn)]
    for fn in tests:
        case(fn)()
    for name, status, note in RESULTS:
        print(f"[{status}] {name}" + (f"  -> {note}" if note else ""))
    p = sum(1 for _, st, _ in RESULTS if st == "PASS")
    f = sum(1 for _, st, _ in RESULTS if st == "FAIL")
    sk = sum(1 for _, st, _ in RESULTS if st == "SKIP")
    print(f"=== FORMULA_FIX_TESTS total={len(RESULTS)} PASS={p} FAIL={f} SKIP={sk} ===")
    return 0 if f == 0 else 1


if __name__ == "__main__":
    raise SystemExit(run())
