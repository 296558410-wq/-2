"""cost_model_v2 — the ONLY canonical execution cost model for V3 research.

Task: V3-HFT-DATA-EXECUTION-GAP-CLOSURE-001 (task XI..XVI).

GOVERNANCE
----------
* `COST_MODEL_VERSION`, `COST_SOURCE`, `COST_TIMESTAMP`, `COST_ASSUMPTION` are mandatory.
* The legacy anchor **0.314 bp** is retained ONLY as
  `HISTORICAL_INVALID_FOR_CURRENT_RESEARCH` and may never be a default parameter.
* A component that is not measured is `DATA_GAP` — never 0.

SIGN CONVENTION (all six terms are POSITIVE COSTS)
--------------------------------------------------
    spread_cost, commission, slippage, latency_cost, adverse_selection, impact  >= 0 means "cost".
    slippage is reported SIGNED first (favorable / unfavorable) and only the
    UNFAVORABLE part is folded into total cost. `abs(slippage)` is forbidden.

COMMISSION CONVENTION
---------------------
    broker statement : net_pnl already NEGATIVE of the cost  (broker view)
    research / ledger: costs are POSITIVE entries that are SUBTRACTED
    conversion       : research_cost = -broker_signed  (documented, tested)
"""
from __future__ import annotations

COST_MODEL_VERSION = "CALIBRATION_20RT_20260921"
COST_SOURCE = ("trader_v3/state/V3_COST_PROFILE.json + V3_EXECUTION_PROFILE.json "
               "(20 measured round trips, FXTM demo, magic 90004)")
COST_TIMESTAMP = "2026-09-21T07:06:13Z"
COST_ASSUMPTION = ("XAUUSD 0.01 lot; spread 0.18 USD/RT + commission 0.22 USD/RT "
                   "=> 0.40 USD/RT ~= 0.914 bp at ~4376 USD/oz")
REAL_RT_COST_BP = 0.914
REAL_RT_COST_USD = 0.40

DEPRECATED = {"value_bp": 0.314, "status": "HISTORICAL_INVALID_FOR_CURRENT_RESEARCH",
              "note": "may not be used in defaults, alpha experiments, feature selection, "
                      "thresholds, backtests, markout or the opportunity gate"}

COMPONENTS = ["spread_cost", "commission", "slippage", "latency_cost",
              "adverse_selection", "impact"]


class DeprecatedCostError(ValueError):
    pass


def assert_not_deprecated(bp):
    if bp is not None and abs(bp - 0.314) < 1e-9:
        raise DeprecatedCostError("0.314 bp is HISTORICAL_INVALID_FOR_CURRENT_RESEARCH")
    return bp


def header():
    return {"COST_MODEL_VERSION": COST_MODEL_VERSION, "COST_SOURCE": COST_SOURCE,
            "COST_TIMESTAMP": COST_TIMESTAMP, "COST_ASSUMPTION": COST_ASSUMPTION,
            "REAL_RT_COST_BP": REAL_RT_COST_BP, "REAL_RT_COST_USD": REAL_RT_COST_USD,
            "deprecated": DEPRECATED}


class CostModelV2:
    def __init__(self, spread_cost=None, commission=None, slippage=None,
                 latency_cost=None, adverse_selection=None, impact=None):
        self.c = {"spread_cost": spread_cost, "commission": commission, "slippage": slippage,
                  "latency_cost": latency_cost, "adverse_selection": adverse_selection,
                  "impact": impact}
        for k, v in self.c.items():
            assert_not_deprecated(v)

    def set_slippage_signed(self, favorable_bp=0.0, unfavorable_bp=0.0):
        """Only the UNFAVORABLE part is a cost. Favorable execution is a credit, not |x|."""
        self.slippage_breakdown = {"favorable_slippage": favorable_bp,
                                   "unfavorable_slippage": unfavorable_bp}
        self.c["slippage"] = unfavorable_bp
        return self.slippage_breakdown

    def component(self, name):
        if name not in COMPONENTS:
            raise KeyError(name)
        v = self.c[name]
        return {"status": "MEASURED" if v is not None else "DATA_GAP", "bp": v}

    def total_cost_bp(self):
        measured = {k: v for k, v in self.c.items() if v is not None}
        gaps = [k for k, v in self.c.items() if v is None]
        return {"total_cost_bp": float(sum(measured.values())),
                "status": "MEASURED" if not gaps else f"PARTIAL(DATA_GAP: {','.join(gaps)})",
                "components": {k: self.component(k) for k in COMPONENTS},
                "version": COST_MODEL_VERSION, "anchor_bp": REAL_RT_COST_BP}

    def net_edge_bp(self, gross_edge_bp):
        t = self.total_cost_bp()
        return {"gross_edge_bp": gross_edge_bp, "total_cost_bp": t["total_cost_bp"],
                "net_edge_bp": gross_edge_bp - t["total_cost_bp"], "status": t["status"],
                "gap_components": [k for k in COMPONENTS if self.c[k] is None]}

    def require_complete(self, threshold_bp=0.10):
        """Opportunity-gate helper: a decision may not be taken on a PARTIAL cost model
        unless the missing components are provably zero for the strategy."""
        t = self.total_cost_bp()
        return {"complete": t["status"] == "MEASURED", "total_cost_bp": t["total_cost_bp"],
                "missing": [k for k in COMPONENTS if self.c[k] is None]}
