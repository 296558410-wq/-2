# -*- coding: utf-8 -*-
"""statistics/robustness.py — 稳健性检查（§10/§12）。

cost_stress_summary: 1x/2x/3x 成本压力下策略指标是否仍成立。
subperiod_stability: 样本分半/分四，检查指标稳定性（避免“整段运气”）。
"""
from __future__ import annotations

from typing import Callable

import numpy as np


def _annualize_sharpe(returns: np.ndarray, periods_per_year: float) -> float:
    r = np.asarray(returns, dtype=float)
    if len(r) < 2 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * np.sqrt(periods_per_year))


def cost_stress_summary(net_returns_by_cost: dict, periods_per_year: float = 252.0) -> dict:
    """输入 {multiplier: net_returns_series}，输出各倍率下关键指标。"""
    out = {}
    for mult, r in net_returns_by_cost.items():
        r = np.asarray(r, dtype=float)
        out[f"{mult}x"] = {
            "net_mean": float(r.mean()),
            "net_total": float(r.sum()),
            "sharpe": round(_annualize_sharpe(r, periods_per_year), 3),
            "n": int(len(r)),
        }
    return out


def subperiod_stability(returns: np.ndarray, n_parts: int = 2, periods_per_year: float = 252.0) -> dict:
    """把收益序列均分为 n_parts 段，输出各段 Sharpe（稳定性视图）。"""
    r = np.asarray(returns, dtype=float)
    n = len(r)
    edges = np.linspace(0, n, n_parts + 1, dtype=int)
    parts = []
    for k in range(n_parts):
        seg = r[edges[k]:edges[k + 1]]
        parts.append({"segment": k + 1, "n": int(len(seg)),
                      "sharpe": round(_annualize_sharpe(seg, periods_per_year), 3),
                      "mean": float(seg.mean()) if len(seg) else 0.0})
    sh = [p["sharpe"] for p in parts]
    return {"n_parts": n_parts, "parts": parts,
            "sharpe_positive_frac": float(np.mean([s > 0 for s in sh])),
            "sharpe_min": float(np.min(sh)), "sharpe_max": float(np.max(sh)),
            "note": "子段 Sharpe 一致性低 → 结果可能依赖特定时期"}
