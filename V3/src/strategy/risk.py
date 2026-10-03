# -*- coding: utf-8 -*-
"""V3 Risk Layer (§6-§13). INDEPENDENT module — never predicts, never changes a signal's direction.

Contract:
  input  = Signal Contract + market state + execution state + account state + risk state
  output = ALLOW | NO_TRADE | BLOCK          (never LONG/SHORT)
  same inputs + same config -> identical decision (§10 determinism, §11 replay)
  never bypasses the Execution Guard: this module performs NO broker call at all (§39)
  always subordinate to V3_LIVE_ALLOWED = NO (§13)
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.dirname(HERE)
STATE = os.path.join(V3, "state")

ALLOW, NO_TRADE, BLOCK = "ALLOW", "NO_TRADE", "BLOCK"

# frozen risk configuration (changing any value is a NEW config version)
RISK_CONFIG = {
    "config_version": "v3-risk-config/1",
    "account": 160766418,
    "server": "ForexTimeFXTM-Demo01",
    "symbol": "XAUUSD",
    "magic": 90004,
    "allowed_execution_modes": ["DEMO_CALIBRATION"],
    "max_spread_bp": 3.0,             # execution-environment quality gate
    "max_cost_bp_round_trip": 1.5,    # 1x anchor 0.914bp; allow headroom to 1.5
    "max_signal_age_s": 120,          # stale data is a RED LINE (§38)
    "max_future_skew_s": 0,           # any future timestamp is a RED LINE
    "cooldown_s": 300,
    "max_open_positions": 1,
    "max_notional_usd": 25000.0,
    "min_confidence": 0.30,
    "require_forward_disabled": True,  # V3_STRATEGY_FORWARD must be NOT_ENABLED
}

RED_LINE_REASONS = ("FUTURE_TIMESTAMP", "WRONG_ACCOUNT", "WRONG_SYMBOL", "WRONG_SERVER", "LIVE_MODE",
                     "INVALID_SIGNAL", "DUPLICATE_INTENT", "STALE_DATA", "FORWARD_ENABLED")


def _sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
                           .encode()).hexdigest()


def config_hash(cfg=None):
    return _sha(cfg or RISK_CONFIG)


@dataclass(frozen=True)
class RiskDecision:
    risk_decision_id: str
    risk_input_hash: str
    risk_config_hash: str
    risk_output: str
    risk_reason: str
    checks: dict
    timestamp: str
    direction_unchanged: str
    broker_call: bool = False

    def to_dict(self):
        return asdict(self)


def _read_state(name, default=None):
    try:
        return open(os.path.join(STATE, name), encoding="utf-8").read().strip()
    except Exception:  # noqa: BLE001
        return default


def build_state_from_files():
    """Real environment state (read-only). Never connects to a broker."""
    return {
        "execution_mode": _read_state("V3_EXECUTION_MODE", "RESEARCH_READONLY"),
        "live_allowed": _read_state("V3_LIVE_ALLOWED", "NO"),
        "order_send_allowed": _read_state("V3_ORDER_SEND_ALLOWED", "NO"),
        "strategy_forward": _read_state("V3_STRATEGY_FORWARD", "NOT_ENABLED"),
    }


def evaluate(signal, market_state, execution_state, account_state, risk_state, cfg=None):
    """Deterministic risk decision. `signal` is a Signal Contract dataclass or dict."""
    cfg = cfg or RISK_CONFIG
    s = signal.to_dict() if hasattr(signal, "to_dict") else dict(signal)
    inputs = {"signal": s, "market": market_state, "execution": execution_state,
               "account": account_state, "risk": risk_state}
    in_hash = _sha(inputs)
    cfg_hash = config_hash(cfg)
    checks = {}
    reasons = []

    def fail(name, ok, reason=None):
        checks[name] = {"pass": bool(ok), "reason": reason}
        if not ok and reason:
            reasons.append(reason)
        return ok

    now = datetime.now(timezone.utc)

    # 1 signal_validity (red line: invalid signal)
    valid = True
    try:
        if hasattr(signal, "validate"):
            signal.validate()
        else:
            if s.get("direction") not in ("LONG", "SHORT", "NO_TRADE"):
                valid = False
            if s.get("direction") in ("LONG", "SHORT") and not s.get("entry_reference"):
                valid = False
            if str(s.get("data_cutoff")) > str(s.get("timestamp")):
                valid = False
    except Exception:  # noqa: BLE001
        valid = False
    fail("signal_validity", valid, None if valid else "INVALID_SIGNAL")

    # 2 data_freshness / 12 stale_signal_check (red line: stale data / future timestamp)
    try:
        ts = datetime.fromisoformat(str(s.get("timestamp")).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age = (now - ts).total_seconds()
        future = age < -float(cfg["max_future_skew_s"])
        stale = age > float(cfg["max_signal_age_s"])
    except Exception:  # noqa: BLE001
        age, future, stale = None, True, True
    fail("data_freshness", not future, None if not future else "FUTURE_TIMESTAMP")
    fail("stale_signal_check", not stale, None if not stale else "STALE_DATA")

    # 3 symbol_check (red line)
    ok_sym = s.get("symbol") == cfg["symbol"]
    fail("symbol_check", ok_sym, None if ok_sym else "WRONG_SYMBOL")

    # 4 account_check (red line)
    acc_ok = (account_state.get("login") == cfg["account"]
              and account_state.get("server", cfg["server"]) == cfg["server"])
    fail("account_check", acc_ok, None if acc_ok else "WRONG_ACCOUNT")

    # 5 execution_mode_check (red line if LIVE / unknown; forward must stay disabled)
    mode_ok = execution_state.get("execution_mode") in cfg["allowed_execution_modes"]
    live_off = str(execution_state.get("live_allowed", "NO")).upper() == "NO"
    fwd_off = str(execution_state.get("strategy_forward", "NOT_ENABLED")).upper() != "ENABLED"
    fail("execution_mode_check", mode_ok and live_off,
         None if (mode_ok and live_off) else ("LIVE_MODE" if not live_off else "WRONG_MODE"))
    fail("live_gate_check", live_off, None if live_off else "LIVE_MODE")
    fail("forward_gate_check", fwd_off, None if fwd_off else "FORWARD_ENABLED")

    # 6 spread_check -> NO_TRADE (environment), not a violation
    spr = market_state.get("spread_bp")
    spread_ok = spr is not None and float(spr) <= float(cfg["max_spread_bp"])
    checks["spread_check"] = {"pass": spread_ok, "reason": None if spread_ok else "SPREAD_TOO_HIGH"}

    # 7 cost_check -> NO_TRADE
    cst = market_state.get("cost_bp_round_trip")
    cost_ok = cst is not None and float(cst) <= float(cfg["max_cost_bp_round_trip"])
    checks["cost_check"] = {"pass": cost_ok, "reason": None if cost_ok else "COST_TOO_HIGH"}

    # 8 position_check -> NO_TRADE
    npos = int(risk_state.get("open_positions", 0) or 0)
    pos_ok = npos < int(cfg["max_open_positions"])
    checks["position_check"] = {"pass": pos_ok, "reason": None if pos_ok else "POSITION_ALREADY_OPEN"}

    # 9 exposure_check -> NO_TRADE
    notional = float(risk_state.get("notional_usd", 0.0) or 0.0)
    exp_ok = notional <= float(cfg["max_notional_usd"])
    checks["exposure_check"] = {"pass": exp_ok, "reason": None if exp_ok else "EXPOSURE_LIMIT"}

    # 10 duplicate_check (red line)
    seen = set(risk_state.get("seen_signal_ids") or [])
    dup = s.get("signal_id") in seen
    fail("duplicate_check", not dup, None if not dup else "DUPLICATE_INTENT")

    # 11 cooldown_check -> NO_TRADE
    last = risk_state.get("last_trade_ts")
    cd_ok = True
    if last:
        try:
            lt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
            if lt.tzinfo is None:
                lt = lt.replace(tzinfo=timezone.utc)
            cd_ok = (now - lt).total_seconds() >= float(cfg["cooldown_s"])
        except Exception:  # noqa: BLE001
            cd_ok = True
    checks["cooldown_check"] = {"pass": cd_ok, "reason": None if cd_ok else "COOLDOWN_ACTIVE"}

    # ---- output: never alter the signal's direction ----
    direction = s.get("direction")
    red = [r for r in reasons if r in RED_LINE_REASONS]
    soft = [c["reason"] for c in checks.values() if (not c["pass"]) and c["reason"]
            and c["reason"] not in RED_LINE_REASONS]
    if direction == "NO_TRADE":
        out, reason = NO_TRADE, "SIGNAL_NO_TRADE"
    elif red:
        out, reason = BLOCK, red[0]
    elif s.get("confidence") is not None and float(s.get("confidence", 0)) < float(cfg["min_confidence"]):
        out, reason = NO_TRADE, "LOW_CONFIDENCE"
    elif soft:
        out, reason = NO_TRADE, soft[0]
    else:
        out, reason = ALLOW, "ALL_CHECKS_PASS"

    rid = _sha({"in": in_hash, "cfg": cfg_hash, "out": out, "reason": reason})[:32]
    return RiskDecision(risk_decision_id=rid, risk_input_hash=in_hash, risk_config_hash=cfg_hash,
                         risk_output=out, risk_reason=reason, checks=checks,
                         timestamp=now.isoformat(), direction_unchanged=direction, broker_call=False)
