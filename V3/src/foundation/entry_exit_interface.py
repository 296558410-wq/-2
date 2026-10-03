"""Entry/Exit interface (stage-1 skeleton). ORDER_SEND=FALSE enforced.

Can receive signal_time, decision_id, price_snapshot, model_output, agent_decision.
Does NOT place orders.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

# ---- execution mode (fail-closed: missing/unknown mode == RESEARCH_READONLY) ----
_MODE_FILE = Path(r"C:\AIQuant\research\hermes\trader_v3\state\V3_EXECUTION_MODE")


def execution_mode() -> str:
    try:
        m = _MODE_FILE.read_text(encoding="utf-8").strip().upper()
    except Exception:  # noqa: BLE001
        return "RESEARCH_READONLY"
    return m if m in ("RESEARCH_READONLY", "DEMO_CALIBRATION", "LIVE") else "RESEARCH_READONLY"


# ORDER_SEND is no longer a blanket False: it is False in RESEARCH_READONLY (unchanged)
# and True only in the explicitly authorised DEMO_CALIBRATION mode.
ORDER_SEND = (execution_mode() == "DEMO_CALIBRATION")


class Signal(str, Enum):
    ENTRY_LONG = "ENTRY_LONG"
    ENTRY_SHORT = "ENTRY_SHORT"
    EXIT = "EXIT"
    WAIT = "WAIT"


@dataclass
class OrderIntent:
    signal: str
    signal_time_ns: int
    decision_id: str
    price_snapshot: dict
    model_output: dict | None = None
    agent_decision: str | None = None
    order_send: bool = False


def build_intent(signal: Signal, signal_time_ns: int, decision_id: str,
                 price_snapshot: dict, model_output=None, agent_decision=None) -> OrderIntent:
    return OrderIntent(
        signal=signal.value if isinstance(signal, Signal) else str(signal),
        signal_time_ns=int(signal_time_ns),
        decision_id=decision_id,
        price_snapshot=dict(price_snapshot),
        model_output=model_output,
        agent_decision=agent_decision,
        order_send=ORDER_SEND,
    )


def send(intent: OrderIntent):
    if execution_mode() != "DEMO_CALIBRATION":
        raise RuntimeError("V3 RESEARCH_READONLY: ORDER_SEND=FALSE (no execution path).")
    raise RuntimeError("V3 DEMO_CALIBRATION: strategy-signal ordering is NOT authorised in this task; "
                       "calibration orders go through foundation/calibration_pilot.py only.")
