# -*- coding: utf-8 -*-
"""V3 Signal Contract (§13) + NO_TRADE vocabulary (§14). Deterministic, no I/O."""
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from enum import Enum

NO_TRADE_REASONS = ("NO_EDGE", "LOW_CONFIDENCE", "BAD_LIQUIDITY", "CONFLICTING_CONTEXT",
                    "HIGH_COST", "DATA_INVALID", "REGIME_UNCERTAIN", "RISK_BLOCKED")


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NO_TRADE = "NO_TRADE"


@dataclass(frozen=True)
class Signal:
    run_id: str
    signal_id: str
    timestamp: str            # decision timestamp t (ISO, UTC)
    symbol: str
    signal_type: str
    direction: str            # LONG | SHORT | NO_TRADE
    confidence: float
    regime: str
    feature_snapshot_hash: str
    context_hash: str
    entry_reference: float | None
    expected_horizon: str
    invalid_condition: str
    reason: str               # NO_TRADE reason or trade rationale
    strategy_version: str
    signal_version: str
    data_cutoff: str          # information cutoff (<= timestamp)
    execution_delay: str      # when execution may occur (strictly after timestamp)

    def validate(self):
        if self.direction not in (d.value for d in Direction):
            raise ValueError(f"bad direction {self.direction}")
        if self.direction == Direction.NO_TRADE.value:
            if self.reason not in NO_TRADE_REASONS:
                raise ValueError(f"NO_TRADE needs a valid reason, got {self.reason!r}")
        else:
            if self.entry_reference is None:
                raise ValueError("trade signal needs entry_reference")
            if not self.invalid_condition:
                raise ValueError("trade signal needs invalid_condition")
        if self.data_cutoff > self.timestamp:
            raise ValueError("LOOKAHEAD: data_cutoff after signal timestamp")
        return True

    def to_dict(self):
        return asdict(self)


def no_trade(run_id, signal_id, ts, symbol, why, strategy_version, signal_version, cutoff,
             regime="UNKNOWN", ctx_hash="", feat_hash=""):
    s = Signal(run_id=run_id, signal_id=signal_id, timestamp=ts, symbol=symbol, signal_type="NO_TRADE",
               direction="NO_TRADE", confidence=0.0, regime=regime, feature_snapshot_hash=feat_hash,
               context_hash=ctx_hash, entry_reference=None, expected_horizon="NONE",
               invalid_condition="", reason=why, strategy_version=strategy_version,
               signal_version=signal_version, data_cutoff=cutoff,
               execution_delay="N/A (no trade)")
    s.validate()
    return s
