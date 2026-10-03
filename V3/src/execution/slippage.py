"""Signed slippage. NEVER use abs(slippage) as if all of it were cost."""
from __future__ import annotations


def classify_slippage(fill_price, reference_price, direction):
    """Signed slippage in price units.

    direction = +1 (long/buy) or -1 (short/sell).
    cost = direction * (fill_price - reference_price)
      cost > 0  -> UNFAVOURABLE (paid up / sold low)
      cost < 0  -> FAVOURABLE   (got a better price than the reference)
    """
    if direction not in (-1, 1):
        raise ValueError("direction must be +1 or -1")
    s = direction * (fill_price - reference_price)
    return {"signed_slippage": s,
            "classification": "UNFAVOURABLE" if s > 0 else ("FAVOURABLE" if s < 0 else "NEUTRAL")}
