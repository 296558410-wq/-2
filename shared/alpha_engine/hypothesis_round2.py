# -*- coding: utf-8 -*-
"""alpha_engine/hypothesis_round2.py — Phase 3 Round-2 预登记（冻结）。

新信息层（数据落地后生成 spec）：
  R1 微观结构-方向（tick imbalance / buy pressure / impact proxy → 未来收益）
  R2 微观结构-波动（tick arrival / spread 状态 → 未来波动/流动性）
  R3 spread×vol 交互（M1 spread 状态 × vol regime → 条件收益）
  R4 波动×回复交互（vol regime 下 zscore 有效性变化）
  R5 时段×微观（session × imbalance）
冻结时机：tick/M1 数据就绪后 freeze_round2() 生成文件；此后规格禁改。
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

import json

ROOT = Path(__file__).resolve().parents[1]
R2_JSON = ROOT / "alpha_engine" / "hypothesis_registry_round2.json"


@dataclass(frozen=True)
class R2Hypothesis:
    hypothesis_id: str
    family: str
    description: str
    feature: str
    source: str            # micro(m1 tick 聚合) | spread | derived
    label: str
    holding: int
    expected_direction: str
    params: dict


R2_SPECS: list[dict] = [
    # ---- R1 微观→方向 ----
    {"family": "R1_micro_direction", "feature": "tick_imb", "source": "micro", "holdings": [5, 15, 60], "direction": "+"},
    {"family": "R1_micro_direction", "feature": "vol_imb", "source": "micro", "holdings": [5, 15, 60], "direction": "+"},
    {"family": "R1_micro_direction", "feature": "buy_pressure", "source": "micro", "holdings": [5, 15, 60], "direction": "+"},
    {"family": "R1_micro_direction", "feature": "z_tick_imb", "source": "micro", "holdings": [15, 60], "direction": "+"},
    {"family": "R1_micro_direction", "feature": "z_vol_imb", "source": "micro", "holdings": [15, 60], "direction": "+"},
    # ---- R2 微观→波动/流动性 ----
    {"family": "R2_micro_vol", "feature": "tick_arrival", "source": "micro", "holdings": [15, 60], "direction": "+", "label_kind": "vol"},
    {"family": "R2_micro_vol", "feature": "impact_proxy", "source": "micro", "holdings": [15, 60], "direction": "+", "label_kind": "vol"},
    {"family": "R2_micro_vol", "feature": "z_spread", "source": "micro", "holdings": [15, 60], "direction": "+", "label_kind": "vol"},
    # ---- R3 spread 状态（M1 蜡烛 spread_close）→ 条件收益/波动 ----
    {"family": "R3_spread_info", "feature": "spread_close", "source": "spread", "holdings": [15, 60], "direction": "-", "note": "高 spread（流动性差）后收益？"},
    {"family": "R3_spread_info", "feature": "spread_close", "source": "spread", "holdings": [15, 60, 240], "direction": "+", "label_kind": "vol"},
    # ---- R4 vol×MR ----
    {"family": "R4_vol_x_mr", "feature": "zscore_60_x_vol30", "source": "derived", "holdings": [15, 60], "direction": "-"},
    # ---- R5 session×micro ----
    {"family": "R5_session_x_micro", "feature": "session_enc_x_tick_imb", "source": "derived", "holdings": [15], "direction": "+"},
]


def expand_round2() -> list[R2Hypothesis]:
    out = []
    for spec in R2_SPECS:
        kind = spec.get("label_kind", "ret")
        for h in spec["holdings"]:
            label = f"future_vol_{h}m" if kind == "vol" else f"forward_return_{h}m"
            out.append(R2Hypothesis(
                hypothesis_id=f"{spec['family']}_{spec['feature']}_h{h}",
                family=spec["family"], description=spec.get("note", spec["family"]),
                feature=spec["feature"], source=spec["source"], label=label,
                holding=h, expected_direction=spec["direction"],
                params={"note": spec.get("note", "")}))
    return out


def freeze_round2(force: bool = False) -> dict:
    if R2_JSON.exists() and not force:
        return json.loads(R2_JSON.read_text(encoding="utf-8"))
    hyps = expand_round2()
    reg = {"created_at": datetime.now(timezone.utc).isoformat(), "frozen": True,
           "round": 2, "note": "microstructure/spread 信息层；冻结后禁改",
           "n_hypotheses": len(hyps), "hypotheses": [asdict(h) for h in hyps]}
    R2_JSON.parent.mkdir(parents=True, exist_ok=True)
    R2_JSON.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    return reg
