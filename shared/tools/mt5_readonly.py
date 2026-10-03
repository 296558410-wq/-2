# -*- coding: utf-8 -*-
"""
MT5_RESEARCH_READONLY_MODE — research safety guard (Phase 9A lock, 2026-09-04T23:03Z)
====================================================================================
Context: the installed MT5 terminal is logged into a REAL account
(ForexTimeFXTM-Live01; evidence: reports/env_smoke_mt5.json). Research is read-only
by discipline; this module makes that discipline fail-closed at the code level:

  * env gate : functions raise unless MT5_RESEARCH_READONLY_MODE=1 (see
               configs/mt5_research_readonly.env)
  * API gate  : after enforce_readonly_mt5(), order-capable MetaTrader5 functions
               are replaced with callables that raise MT5ReadonlyViolation — any
               accidental execution path dies before touching the broker.
  * static gate: audit_static() greps code roots for forbidden order/deal symbols.

Usage (mandatory for any Phase 9 code that touches MT5):
    from tools.mt5_readonly import enforce_readonly_mt5, ensure_mode
    ensure_mode()                  # fail closed if env flag missing
    import MetaTrader5 as mt5
    enforce_readonly_mt5(mt5)      # nullify order-capable entry points

Never import order-capable wrappers; never call mt5.initialize() with trade intent.
"""
from __future__ import annotations

import os
from pathlib import Path

READONLY_ENV_VAR = "MT5_RESEARCH_READONLY_MODE"
REPO_ROOT = Path(__file__).resolve().parent.parent

# Functions that can touch the broker / mutate account state (MT5 Python API).
# order_send is the single execution entry point (buy/sell/modify/delete/close).
# account_update can change account settings on some builds. calc_* are read-only
# helpers but are disabled too (defense in depth; research never needs them).
ORDER_CAPABLE = [
    "order_send",
    "order_modify",
    "order_delete",
    "order_cancel",
    "order_calc_margin",
    "order_calc_profit",
    "position_close",
    "account_update",
]

# Static-scan forbidden tokens (mirrors phase9_detector_registry.yaml
# global_protocol.mt5_safety.forbidden_symbols).
FORBIDDEN_TOKENS = [
    "order_send", "OrderSend",
    "order_modify", "OrderModify",
    "order_delete", "OrderDelete",
    "order_cancel",
    "position_open", "PositionOpen",
    "position_close", "PositionClose",
    "account_update",
    "trade.Balance", "TradeCopy",
    "TRADE_ACTION_DEAL",
]

# Files that legitimately contain the tokens (definitions / verifiers only).
ALLOWLIST = {
    "research/phase9/registry/build_phase9_registry.py",
    "scripts/env_baseline/mt5_smoke.py",
    "scripts/phase9a_audit.py",
    "tools/mt5_readonly.py",
}


class MT5ReadonlyViolation(RuntimeError):
    """Raised when an order-capable MT5 path is attempted or the env gate is open."""


def ensure_mode() -> None:
    """Fail closed: raise unless MT5_RESEARCH_READONLY_MODE == '1'."""
    if os.environ.get(READONLY_ENV_VAR) != "1":
        raise MT5ReadonlyViolation(
            f"{READONLY_ENV_VAR} is not set to 1 — refusing research MT5 access "
            f"(REAL account protection). Set it via configs/mt5_research_readonly.env."
        )


def enforce_readonly_mt5(mt5_module=None):
    """Nullify order-capable functions on the MetaTrader5 module.

    Returns the list of disabled names. Accepts an already-imported module, or
    imports MetaTrader5 itself. Raises MT5ReadonlyViolation on env gate failure.
    """
    ensure_mode()
    if mt5_module is None:
        try:
            import MetaTrader5 as mt5_module  # type: ignore
        except ImportError:
            return []  # no terminal binding in this environment; nothing to disarm
    disabled = []
    for name in ORDER_CAPABLE:
        if hasattr(mt5_module, name):
            setattr(mt5_module, name, _blocked(name))
            disabled.append(name)
    return disabled


def _blocked(name: str):
    def _never(*_args, **_kwargs):
        raise MT5ReadonlyViolation(
            f"MetaTrader5.{name} is DISABLED by MT5_RESEARCH_READONLY_MODE "
            f"(REAL account). Research is read-only: no orders, no account mutation."
        )
    _never.__name__ = f"readonly_blocked_{name}"
    return _never


def audit_static(roots=None, allowlist=None):
    """Static scan for forbidden tokens. Returns list of hit dicts (empty == PASS)."""
    roots = roots or ["research", "scripts", "alpha_engine", "tools"]
    allowlist = allowlist or ALLOWLIST
    hits = []
    for root in roots:
        base = REPO_ROOT / root
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.py")):
            rel = p.relative_to(REPO_ROOT).as_posix()
            if "__pycache__" in rel or rel in allowlist:
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                for tok in FORBIDDEN_TOKENS:
                    if tok in line:
                        hits.append({"file": rel, "line": lineno, "token": tok,
                                     "snippet": line.strip()[:120]})
    return hits
