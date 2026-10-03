"""V3 execution research package (read-only, no orders).

Canonical cost model: `cost_model_v2` (version CALIBRATION_20RT_20260921, 0.914 bp/RT).
The legacy 0.314 bp anchor is retained only as HISTORICAL_INVALID_FOR_CURRENT_RESEARCH.
"""
from . import (cost_model_v2, slippage, latency_cost, pnl_attribution,
               execution_quality, observability)

__all__ = ["cost_model_v2", "slippage", "latency_cost", "pnl_attribution",
           "execution_quality", "observability"]
