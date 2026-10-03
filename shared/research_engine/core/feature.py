# -*- coding: utf-8 -*-
"""core/feature.py — Feature Engine（§5）：装配 + 对齐纪律 + 无前视校验。

设计：
  * FeatureSpec: {name, func, params, lookback} —— lookback 缺省由 func 的
    FEATURE_LOOKBACKS 或 params.window 推断
  * FeatureEngine.build(bars, specs) → FeatureMatrix(X, lookback_max)
  * 所有特征按 ts_utc 对齐到同一索引；管线必须丢弃前 lookback_max 行
  * assert_no_lookahead(bars, specs, t)：用截断数据重算并与全量结果比对，
    证明特征只用 ≤t 的信息（防前视回归测试用）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd


def _infer_lookback(spec: "FeatureSpec") -> int:
    if spec.lookback is not None:
        return spec.lookback
    for key in ("window", "long", "slow"):
        w = spec.params.get(key)
        if w:
            return int(w)
    return 1


@dataclass
class FeatureSpec:
    name: str
    func: Callable[..., pd.Series]
    params: dict = field(default_factory=dict)
    lookback: int | None = None

    def effective_lookback(self) -> int:
        return _infer_lookback(self)


@dataclass
class FeatureMatrix:
    X: pd.DataFrame                    # index = ts_utc（bar 收盘时刻）
    lookback_max: int                  # 需丢弃的头部行数
    specs: list = field(default_factory=list)

    def drop_warmup(self) -> "FeatureMatrix":
        return FeatureMatrix(self.X.iloc[self.lookback_max:], self.lookback_max, self.specs)


def build(bars: pd.DataFrame, specs: list[FeatureSpec]) -> FeatureMatrix:
    if "ts_utc" in bars.columns:
        bars = bars.set_index("ts_utc")
    bars = bars.sort_index()
    cols: dict[str, pd.Series] = {}
    look_max = 1
    for spec in specs:
        lb = spec.effective_lookback()
        look_max = max(look_max, lb)
        s = spec.func(bars, **spec.params)
        if s is None:
            raise ValueError(f"feature {spec.name} 返回 None")
        if not isinstance(s, pd.Series):
            s = pd.Series(s, index=bars.index)
        s = s.reindex(bars.index)
        cols[spec.name] = s
    X = pd.DataFrame(cols)
    return FeatureMatrix(X, look_max, list(specs))


def assert_no_lookahead(bars: pd.DataFrame, specs: list[FeatureSpec],
                        probes: int = 5, seed: int = 0) -> dict:
    """对若干随机时间点 t：截断重算特征 vs 全量特征在 t 的值，应完全一致。"""
    bars = bars.sort_values("ts_utc") if "ts_utc" in bars.columns else bars.sort_index()
    idx = bars.index if "ts_utc" not in bars.columns else bars["ts_utc"]
    full = build(bars, specs)
    lb = full.lookback_max
    rng = np.random.default_rng(seed)
    n = len(bars)
    positions = rng.integers(lb + 5, n - 5, size=probes)
    mismatches: list[dict] = []
    for t in positions:
        head = bars.iloc[: t + 1]
        head_matrix = build(head, specs).X
        for col in full.X.columns:
            a = full.X[col].iloc[t]
            b = head_matrix[col].iloc[-1]
            if pd.isna(a) and pd.isna(b):
                continue
            if pd.isna(a) != pd.isna(b) or (not np.isclose(a, b, equal_nan=True)):
                mismatches.append({"t": int(t), "feature": col, "full": a, "truncated": b})
    return {"probes": positions.tolist(), "mismatches": mismatches,
            "passed": len(mismatches) == 0}
