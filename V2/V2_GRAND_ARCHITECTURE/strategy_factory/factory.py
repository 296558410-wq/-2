"""Strategy Factory: phenomenon -> hypothesis -> candidate mechanism -> strategy spec.

Generates genuinely diverse strategy candidates (not copies of V1/V2), each with
full metadata: strategy_id, hypothesis_id, mechanism, feature_set, parameters,
expected_horizon, applicable_regime, entry/exit/invalidation logic, cost model,
PIT requirements, creation commit, dataset hash.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, field
import numpy as np

from common import hashing
from common import data as data_mod
from . import mechanisms as mech

ENTRY_TEXT = {
    "TREND": "fast/slow MA gap sign confirmed by gap slope; trade with trend",
    "MOMENTUM": "|z(ret_w)| > thr and vol_ratio < vol_cap; trade with move",
    "REVERSAL": "stretched move (z>thr) near range extreme -> fade",
    "RANGE": "RSI extreme inside RANGE regime -> fade",
    "BREAKOUT": "close beyond rolling Donchian high/low",
    "VOL_EXPANSION": "vol_ratio spike; trade last-bar direction",
    "VOL_CONTRACTION": "post-squeeze break of prior quiet range",
    "MTF_STRUCTURE": "5/20/60-bar returns aligned",
    "EVENT": "single-bar shock > 1.5*ATR; trade direction",
    "MACRO": "slow MA slope/ATR resonance",
    "HYBRID": "trend_strength sign gated by vol_ratio",
}

@dataclass
class StrategySpec:
    strategy_id: str
    hypothesis_id: str
    mechanism: str
    feature_set: list
    parameters: dict
    expected_horizon: int
    applicable_regime: list
    entry_logic: str
    exit_logic: str
    invalidation: str
    cost_model: str
    pit_requirements: str
    creation_commit: str
    dataset_hash: str
    config_hash: str = ""
    lifecycle: str = "RESEARCH"

    def to_dict(self) -> dict:
        return asdict(self)


FEATURE_SETS = {
    "TREND": ["ma5", "ma20", "trend_strength"],
    "MOMENTUM": ["ret20", "atr14", "vol_ratio"],
    "REVERSAL": ["ret20", "atr14", "range_pos20"],
    "RANGE": ["rsi14", "regime"],
    "BREAKOUT": ["close", "hh20", "ll20"],
    "VOL_EXPANSION": ["vol_ratio", "close"],
    "VOL_CONTRACTION": ["vol_ratio", "hh20", "ll20", "close"],
    "MTF_STRUCTURE": ["ret5", "ret20", "ret60"],
    "EVENT": ["close", "atr14"],
    "MACRO": ["ma60", "atr14"],
    "HYBRID": ["trend_strength", "vol_ratio"],
}


def config_hash(spec_kwargs: dict) -> str:
    return hashing.sha256_json(spec_kwargs)


def generate_specs(commit: str | None = None, dhash: str | None = None) -> list[StrategySpec]:
    commit = commit or hashing.git_commit()
    dhash = dhash or data_mod.dataset_hash()
    specs: list[StrategySpec] = []
    for mech_name, grid in mech.PARAM_GRIDS.items():
        for j, params in enumerate(grid):
            sid = f"SF-{mech_name}-{j:02d}"
            hyp = f"HYP-{mech_name}"
            kw = {"mechanism": mech_name, "params": params,
                  "horizon": mech.HORIZONS[mech_name]}
            specs.append(StrategySpec(
                strategy_id=sid,
                hypothesis_id=hyp,
                mechanism=mech_name,
                feature_set=FEATURE_SETS[mech_name],
                parameters=params,
                expected_horizon=mech.HORIZONS[mech_name],
                applicable_regime=mech.APPLICABLE_REGIME[mech_name],
                entry_logic=ENTRY_TEXT[mech_name],
                exit_logic=f"hold {mech.HORIZONS[mech_name]} bars or opposite signal",
                invalidation="adverse excursion > 1.5x expected MFE; regime flip",
                cost_model="observed median round-trip spread (price units), charged once per position",
                pit_requirements="features<=t only; label from t+1..t+h; no lookahead",
                creation_commit=commit,
                dataset_hash=dhash,
                config_hash=config_hash(kw),
            ))
    return specs


def run_mechanism(df, spec: StrategySpec) -> np.ndarray:
    fn = mech.MECHANISMS[spec.mechanism]
    return fn(df, **spec.parameters)
