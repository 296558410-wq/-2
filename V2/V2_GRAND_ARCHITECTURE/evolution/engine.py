"""Evolution Engine.

NOT "change the strategy every 48h". Flow:
  monitor -> detect performance change -> propose upgrade hypothesis ->
  generate candidate -> historical validation -> OOS -> shadow -> decide.
States: NO_CHANGE / SHADOW / CANDIDATE_RELEASE / RETIRED.

Triggers are evidence-based (no fixed clock):
  edge degradation, regime transition, opportunity degradation, confidence drift,
  calibration drift, cost sensitivity, MAE expansion, MFE contraction,
  prediction drift.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import numpy as np

NO_CHANGE = "NO_CHANGE"
SHADOW = "SHADOW"
CANDIDATE_RELEASE = "CANDIDATE_RELEASE"
RETIRED = "RETIRED"


@dataclass
class MonitorState:
    strategy_id: str
    edge: float          # recent expectancy (cost-adjusted)
    edge_baseline: float
    mfe: float
    mae: float
    confidence_mean: float
    hit_rate: float
    regime_now: str
    regime_then: str
    cost_sens: float     # expectancy change per 1x cost increase


def detect_triggers(m: MonitorState, thresholds: dict | None = None) -> list[str]:
    th = thresholds or {"edge_drop": 0.35, "mae_expand": 1.5, "mfe_contract": 0.6,
                        "conf_drift": 0.2}
    tr = []
    b = m.edge_baseline if m.edge_baseline != 0 else np.nan
    if np.isfinite(b) and b > 0 and (m.edge - b) / abs(b) < -th["edge_drop"]:
        tr.append("edge_degradation")
    if m.regime_now != m.regime_then:
        tr.append("regime_transition")
    if np.isfinite(m.mae) and np.isfinite(m.mfe) and m.mfe != 0 and m.mae / max(abs(m.mfe), 1e-9) > th["mae_expand"]:
        tr.append("mae_expansion")
    if np.isfinite(m.mfe) and np.isfinite(m.mae) and m.mae != 0 and m.mfe / max(abs(m.mae), 1e-9) < th["mfe_contract"]:
        tr.append("mfe_contraction")
    if abs(m.confidence_mean - 0.5) > th["conf_drift"] and m.hit_rate < 0.5:
        tr.append("confidence_drift")
    if m.cost_sens < -0.1:
        tr.append("cost_sensitivity")
    return tr


def evolve(m: MonitorState, oos_result: dict | None = None,
           historical_result: dict | None = None) -> dict:
    """Decide the evolution state for one strategy from monitored evidence.

    A candidate may only be RELEASEd when historical validation AND untouched
    OOS both pass. Otherwise it stays NO_CHANGE or SHADOW.
    """
    triggers = detect_triggers(m)
    state = NO_CHANGE
    reason = "no evidence-based trigger fired"
    if triggers:
        state = SHADOW
        reason = f"triggers={triggers}; proposing candidate, awaiting validation"
        if historical_result and historical_result.get("pass"):
            if oos_result and oos_result.get("pass"):
                state = CANDIDATE_RELEASE
                reason = f"triggers={triggers}; historical+OOS passed"
            else:
                reason = f"triggers={triggers}; historical passed, OOS not passed"
        if historical_result and historical_result.get("retire"):
            state = RETIRED
            reason = "historical validation shows persistent degradation"
    return {"state": state, "triggers": triggers, "reason": reason}
