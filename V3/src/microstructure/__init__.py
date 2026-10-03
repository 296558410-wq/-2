"""V3 L1 microstructure research package (read-only, no orders).

Field naming contract:
  * true OFI        -> DATA_GAP on an L1-quote-only feed
  * tick-rule proxy -> ALWAYS named *_PROXY (never "OFI", never "microprice")
  * unmeasurable    -> DATA_GAP, never 0 and never silently substituted by a proxy

Timestamp contract: integers are **milliseconds since epoch** unless a unit is
explicitly declared through `timestamp_unit_guard`. No silent inference.
"""
from . import (spread, microprice, ofi, tick_flow, imbalance,
               volatility_state, markout, adverse_selection,
               fill_probability, arrival_rate, data_state,
               timestamp_unit_guard)

__all__ = ["spread", "microprice", "ofi", "tick_flow", "imbalance",
           "volatility_state", "markout", "adverse_selection",
           "fill_probability", "arrival_rate", "data_state",
           "timestamp_unit_guard"]
