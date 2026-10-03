# -*- coding: utf-8 -*-
"""Risk Layer unit tests (§37) incl. red lines (§38). No broker access. Standalone runner."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

V3 = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, V3)

from strategy import risk as R  # noqa: E402

NOW = datetime.now(timezone.utc)
CFG = dict(R.RISK_CONFIG)


def sig(**kw):
    base = {"signal_id": "S1", "timestamp": NOW.isoformat(), "data_cutoff": NOW.isoformat(),
            "symbol": "XAUUSD", "direction": "LONG", "confidence": 0.6, "entry_reference": 4270.0,
            "invalid_condition": "x", "reason": "mech"}
    base.update(kw)
    return base


def env(**kw):
    m = {"spread_bp": 0.4, "cost_bp_round_trip": 0.914}
    e = {"execution_mode": "DEMO_CALIBRATION", "live_allowed": "NO", "order_send_allowed": "YES",
         "strategy_forward": "NOT_ENABLED"}
    a = {"login": 160766418, "server": "ForexTimeFXTM-Demo01"}
    r = {"open_positions": 0, "notional_usd": 0.0, "seen_signal_ids": [], "last_trade_ts": None}
    for d, k in ((m, "m"), (e, "e"), (a, "a"), (r, "r")):
        if k in kw:
            d.update(kw[k])
    return kw.get("signal", sig()), m, e, a, r


def run(signal, m, e, a, r):
    return R.evaluate(signal, m, e, a, r, cfg=CFG)


CASES = []


def case(name, expect):
    def deco(fn):
        CASES.append((name, fn, expect))
        return fn
    return deco


@case("valid_signal", "ALLOW")
def _():
    return run(*env()).risk_output


@case("stale_signal", "BLOCK")
def _():
    old = (NOW - timedelta(seconds=600)).isoformat()
    return run(*env(signal=sig(timestamp=old, data_cutoff=old))).risk_output


@case("future_data", "BLOCK")
def _():
    fut = (NOW + timedelta(seconds=300)).isoformat()
    return run(*env(signal=sig(timestamp=fut, data_cutoff=fut))).risk_output


@case("wrong_symbol", "BLOCK")
def _():
    return run(*env(signal=sig(symbol="EURUSD"))).risk_output


@case("wrong_account", "BLOCK")
def _():
    return run(*env(a={"login": 160759434, "server": "ForexTimeFXTM-Demo01"})).risk_output


@case("wrong_mode_live", "BLOCK")
def _():
    return run(*env(e={"execution_mode": "LIVE", "live_allowed": "YES",
                        "order_send_allowed": "YES", "strategy_forward": "NOT_ENABLED"})).risk_output


@case("forward_enabled", "BLOCK")
def _():
    return run(*env(e={"execution_mode": "DEMO_CALIBRATION", "live_allowed": "NO",
                        "order_send_allowed": "YES", "strategy_forward": "ENABLED"})).risk_output


@case("spread_too_high", "NO_TRADE")
def _():
    return run(*env(m={"spread_bp": 9.9, "cost_bp_round_trip": 0.914})).risk_output


@case("cost_too_high", "NO_TRADE")
def _():
    return run(*env(m={"spread_bp": 0.4, "cost_bp_round_trip": 3.5})).risk_output


@case("duplicate_signal", "BLOCK")
def _():
    return run(*env(r={"open_positions": 0, "notional_usd": 0.0, "seen_signal_ids": ["S1"],
                        "last_trade_ts": None})).risk_output


@case("existing_position", "NO_TRADE")
def _():
    return run(*env(r={"open_positions": 1, "notional_usd": 0.0, "seen_signal_ids": [],
                        "last_trade_ts": None})).risk_output


@case("cooldown", "NO_TRADE")
def _():
    return run(*env(r={"open_positions": 0, "notional_usd": 0.0, "seen_signal_ids": [],
                        "last_trade_ts": (NOW - timedelta(seconds=5)).isoformat()})).risk_output


@case("invalid_context", "BLOCK")
def _():
    return run(*env(signal=sig(direction="MAYBE"))).risk_output


@case("no_trade_signal", "NO_TRADE")
def _():
    return run(*env(signal=sig(direction="NO_TRADE", entry_reference=None, invalid_condition=""))).risk_output


@case("low_confidence", "NO_TRADE")
def _():
    return run(*env(signal=sig(confidence=0.05))).risk_output


@case("exposure_limit", "NO_TRADE")
def _():
    return run(*env(r={"open_positions": 0, "notional_usd": 99999.0, "seen_signal_ids": [],
                        "last_trade_ts": None})).risk_output


def main():
    ok = 0
    lines = []
    for name, fn, expect in CASES:
        got = fn()
        good = (got == expect)
        ok += good
        lines.append(f"[{'PASS' if good else 'FAIL'}] {name}: expect={expect} got={got}")

    # determinism + replay (§10/§11)
    a = run(*env()); b = run(*env())
    det = (a.risk_decision_id == b.risk_decision_id and a.risk_input_hash == b.risk_input_hash
           and a.risk_output == b.risk_output)
    lines.append(f"[{'PASS' if det else 'FAIL'}] determinism_replay: {a.risk_decision_id[:12]} == {b.risk_decision_id[:12]}")

    # direction never altered (§9)
    d1 = run(*env(signal=sig(direction="LONG"))).direction_unchanged
    d2 = run(*env(signal=sig(direction="SHORT"))).direction_unchanged
    dirn = (d1 == "LONG" and d2 == "SHORT")
    lines.append(f"[{'PASS' if dirn else 'FAIL'}] direction_unchanged: {d1}/{d2}")

    # no broker call (§39)
    nb = (a.broker_call is False)
    lines.append(f"[{'PASS' if nb else 'FAIL'}] no_broker_call")

    # risk must live in its own module (§6)
    src = open(os.path.join(V3, "strategy", "risk.py"), encoding="utf-8").read()
    # precise: risk.py must not import/call a broker. ("order_send_allowed" is a STATE KEY, not a call.)
    own = (("import MetaTrader5" not in src) and ("mt5." not in src)
           and (".order_send(" not in src) and (".order_check(" not in src))
    lines.append(f"[{'PASS' if own else 'FAIL'}] no_broker_import_in_risk_module")

    print("\n".join(lines))
    total = len(CASES)
    print(f"\n=== RISK_TEST_COUNT={total} PASS={ok} FAIL={total - ok} | extra_checks={(4 if det and dirn and nb and own else 0)}/4 ===")
    return 0 if (ok == total and det and dirn and nb and own) else 1


if __name__ == "__main__":
    raise SystemExit(main())
