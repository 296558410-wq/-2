# -*- coding: utf-8 -*-
"""alpha_engine/hypothesis.py — Hypothesis 结构与第一轮预登记（§8/§14）。

10 个 hypothesis families × 有限参数网格 → 全部实例化后写入
hypothesis_registry.json 并**冻结**（文件生成后实验不得改规格）。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_JSON = ROOT / "alpha_engine" / "hypothesis_registry.json"


@dataclass(frozen=True)
class Hypothesis:
    hypothesis_id: str            # family + 参数签名
    family: str
    description: str
    feature: str                  # 特征名（xauusd library CATALOG 或派生）
    feature_params: dict
    label: str                    # forward_return_{h}m | future_vol_{h}m
    timeframe: str = "M1"
    holding: int = 60             # 分钟
    expected_direction: str = "+"  # + / - / "|" (absolute/vol)
    params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def signature(self) -> str:
        return f"{self.family}:{self.feature}:{self.label}"


@dataclass(frozen=True)
class HypothesisFamily:
    family: str
    description: str
    build: list[dict]             # 预登记清单：[{feature, feature_params, holdings:[...], label_kind, expected_direction}]


# 第一轮预登记（有限、可解释；所有参数在此固定）
FAMILIES: list[HypothesisFamily] = [
    HypothesisFamily("H1_momentum", "过去收益是否预测未来收益？", [
        {"feature": "mom_5", "feature_params": {}, "holdings": [5, 15, 60], "expected_direction": "+"},
        {"feature": "mom_10", "feature_params": {}, "holdings": [5, 15, 60], "expected_direction": "+"},
        {"feature": "mom_20", "feature_params": {}, "holdings": [15, 60, 240], "expected_direction": "+"},
        {"feature": "mom_60", "feature_params": {}, "holdings": [60, 240], "expected_direction": "+"},
    ]),
    HypothesisFamily("H2_mean_reversion", "短期极端偏离是否预测回归？", [
        {"feature": "zscore_60", "feature_params": {}, "holdings": [5, 15, 60], "expected_direction": "-"},
        {"feature": "dist_mean_60", "feature_params": {}, "holdings": [5, 15, 60], "expected_direction": "-"},
        {"feature": "dist_ema_60", "feature_params": {}, "holdings": [5, 15, 60], "expected_direction": "-"},
    ]),
    HypothesisFamily("H3_breakout", "突破过去高低点是否有 drift？", [
        {"feature": "breakout_60", "feature_params": {}, "holdings": [5, 15, 60], "expected_direction": "+"},
        {"feature": "dist_hi_60", "feature_params": {}, "holdings": [5, 15, 60], "expected_direction": "+"},
        {"feature": "dist_lo_60", "feature_params": {}, "holdings": [5, 15, 60], "expected_direction": "-"},
    ]),
    HypothesisFamily("H4_volatility", "波动状态含未来 return/vol 信息？", [
        {"feature": "vol_30", "feature_params": {}, "holdings": [60, 240], "label_kind": "vol", "expected_direction": "+"},
        {"feature": "atr_14", "feature_params": {}, "holdings": [60, 240], "label_kind": "vol", "expected_direction": "+"},
        {"feature": "rvol_60", "feature_params": {}, "holdings": [60, 240], "label_kind": "vol", "expected_direction": "+"},
        {"feature": "vol_ratio_15_60", "feature_params": {}, "holdings": [15, 60], "label_kind": "vol", "expected_direction": "+"},
    ]),
    HypothesisFamily("H5_trend_regime", "趋势状态是否影响未来收益分布？", [
        {"feature": "sma_dist_60", "feature_params": {}, "holdings": [15, 60, 240], "expected_direction": "+"},
        {"feature": "ema_dist_60", "feature_params": {}, "holdings": [15, 60, 240], "expected_direction": "+"},
        {"feature": "trend_str", "feature_params": {}, "holdings": [15, 60, 240], "label_kind": "vol", "expected_direction": "+"},
        {"feature": "slope_60", "feature_params": {}, "holdings": [60, 240], "expected_direction": "+"},
    ]),
    HypothesisFamily("H6_session", "不同 session 是否存在条件分布差异？", [
        {"feature": "session_enc", "feature_params": {}, "holdings": [5, 15, 60], "expected_direction": "|"},
        {"feature": "hour", "feature_params": {}, "holdings": [5, 60], "expected_direction": "|"},
    ]),
    HypothesisFamily("H7_vol_x_momentum", "波动 regime 下 momentum 是否变化？", [
        {"feature": "mom_10_x_vol30", "feature_params": {}, "holdings": [15, 60], "expected_direction": "+"},
        {"feature": "mom_60_x_vol30", "feature_params": {}, "holdings": [60, 240], "expected_direction": "+"},
    ]),
    HypothesisFamily("H8_trend_x_vol", "趋势与波动状态是否存在交互？", [
        {"feature": "trend_str_x_vol30", "feature_params": {}, "holdings": [60, 240], "expected_direction": "+"},
    ]),
    HypothesisFamily("H9_range_x_momentum", "range regime 是否改变 momentum 有效性？", [
        {"feature": "mom_10_x_compression", "feature_params": {}, "holdings": [15, 60], "expected_direction": "-"},
        {"feature": "mom_60_x_compression", "feature_params": {}, "holdings": [60], "expected_direction": "-"},
    ]),
    HypothesisFamily("H10_multi_timeframe", "H1 状态是否改变 M1 条件分布？", [
        {"feature": "h1_mom_4", "feature_params": {}, "holdings": [15, 60], "expected_direction": "+"},
        {"feature": "h1_vol_ratio", "feature_params": {}, "holdings": [15, 60, 240], "label_kind": "vol", "expected_direction": "+"},
        {"feature": "h1_breakout", "feature_params": {}, "holdings": [15, 60], "expected_direction": "+"},
    ]),
]


def expand_hypotheses() -> list[Hypothesis]:
    """把 FAMILIES 展开为 Hypothesis 列表（含交互特征派生说明）。"""
    out: list[Hypothesis] = []
    for fam in FAMILIES:
        for i, spec in enumerate(fam.build):
            feature = spec["feature"]
            for h in spec["holdings"]:
                label_kind = spec.get("label_kind", "ret")
                label = f"future_vol_{h}m" if label_kind == "vol" else f"forward_return_{h}m"
                hid = f"{fam.family}_{i+1:02d}_{feature}_h{h}"
                out.append(Hypothesis(
                    hypothesis_id=hid, family=fam.family, description=fam.description,
                    feature=feature, feature_params=spec.get("feature_params", {}),
                    label=label, timeframe="M1", holding=h,
                    expected_direction=spec.get("expected_direction", "+"),
                    params={"derived": _derived_note(feature)},
                ))
    return out


def _derived_note(feature: str) -> str:
    """标注派生特征（需要两特征相乘/拼接）——由 generator 实现。"""
    return feature


def freeze_registry() -> dict:
    """生成 hypothesis_registry.json（预登记+冻结）。已存在则不改写。"""
    if REGISTRY_JSON.exists():
        return json.loads(REGISTRY_JSON.read_text(encoding="utf-8"))
    hyps = expand_hypotheses()
    reg = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "frozen": True,
        "note": "第一轮预登记规格，冻结后实验不得修改（anti-P-hacking）",
        "n_hypotheses": len(hyps),
        "hypotheses": [h.to_dict() for h in hyps],
    }
    REGISTRY_JSON.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_JSON.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    return reg


def load_frozen() -> dict:
    return json.loads(REGISTRY_JSON.read_text(encoding="utf-8"))
