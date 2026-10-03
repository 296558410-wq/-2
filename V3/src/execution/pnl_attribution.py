"""Execution PnL attribution (task XI).

Gross Directional PnL
+ Spread Capture
- Spread Cost
- Commission
- Slippage
- Latency Cost
- Adverse Selection
- Impact
= Net Executable PnL

Any unmeasurable term => "DATA_GAP" (never 0).
"""
from __future__ import annotations

TERMS = ["gross_directional_pnl", "spread_capture", "spread_cost", "commission",
         "slippage", "latency_cost", "adverse_selection", "market_impact"]


def attribute(gross_directional_pnl=None, spread_capture=None, spread_cost=None,
              commission=None, slippage=None, latency_cost=None,
              adverse_selection=None, market_impact=None):
    t = {"gross_directional_pnl": gross_directional_pnl, "spread_capture": spread_capture,
         "spread_cost": spread_cost, "commission": commission, "slippage": slippage,
         "latency_cost": latency_cost, "adverse_selection": adverse_selection,
         "market_impact": market_impact}
    gaps = [k for k in TERMS if t[k] is None]
    total = 0.0
    for k in TERMS:
        v = t[k]
        if v is None:
            continue
        total += v if k in ("gross_directional_pnl", "spread_capture") else -v
    return {"terms": t, "net_executable_pnl": (None if gaps else total),
            "status": "MEASURED" if not gaps else f"PARTIAL(DATA_GAP: {','.join(gaps)})"}
