# -*- coding: utf-8 -*-
"""alpha_engine/evaluator.py — information-first 评估（§9）。

每个 (hypothesis, 数据) 输出：
  conditional return / IC(spearman) / directional accuracy / distribution shift /
  volatility shift —— 全部在 train/val/test 上分别给出（train 用于了解，结论只看 OOS）。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def ic(a: pd.Series, b: pd.Series) -> float:
    m = pd.concat([a, b], axis=1).dropna()
    if len(m) < 50:
        return 0.0
    return float(spearmanr(m.iloc[:, 0], m.iloc[:, 1]).statistic)


def directional_accuracy(signal: pd.Series, fwd: pd.Series, direction: str = "+") -> float:
    """direction='+'：signal>0 时 fwd 应>0 的比例（含空头侧对称）。"""
    m = pd.concat([signal, fwd], axis=1).dropna()
    if len(m) < 50:
        return 0.5
    s, r = m.iloc[:, 0].values, m.iloc[:, 1].values
    if direction == "-":
        s = -s
    mask = np.abs(s) > 1e-12
    if mask.sum() == 0:
        return 0.5
    return float(((s[mask] > 0) == (r[mask] > 0)).mean())


def conditional_returns(signal: pd.Series, fwd: pd.Series, quantiles: int = 5) -> dict:
    """信号分位组内的未来收益均值（检验单调性）。"""
    m = pd.concat([signal, fwd], axis=1).dropna()
    if len(m) < quantiles * 100:
        return {}
    m["q"] = pd.qcut(m.iloc[:, 0].rank(method="first"), quantiles, labels=False)
    out = {}
    for q in range(quantiles):
        sub = m[m["q"] == q]
        out[f"q{q+1}_mean"] = float(sub.iloc[:, 1].mean())
        out[f"q{q+1}_n"] = int(len(sub))
    return out


def volatility_shift(feature: pd.Series, future_vol: pd.Series) -> dict:
    """特征高组 vs 低组的未来波动率之比（>1 = 高特征 → 高未来波动）。"""
    m = pd.concat([feature, future_vol], axis=1).dropna()
    if len(m) < 200:
        return {}
    hi = m[m.iloc[:, 0] >= m.iloc[:, 0].quantile(0.8)].iloc[:, 1]
    lo = m[m.iloc[:, 0] <= m.iloc[:, 0].quantile(0.2)].iloc[:, 1]
    return {"ratio": float(hi.mean() / lo.mean()) if lo.mean() > 0 else float("nan"),
            "hi_n": int(len(hi)), "lo_n": int(len(lo))}


def evaluate_information(feature: pd.Series, label: pd.Series,
                         expected_direction: str = "+") -> dict:
    """对一个特征-标签对输出 information 统计包（无训练、无拟合）。"""
    icv = ic(feature, label)
    da = directional_accuracy(feature, label, expected_direction)
    cond = conditional_returns(feature, label)
    out = {"ic": round(icv, 5), "directional_accuracy": round(da, 4),
           "n": int(pd.concat([feature, label], axis=1).dropna().shape[0])}
    out.update(cond)
    if expected_direction == "|" or "vol" in str(label):
        out["vol_shift"] = volatility_shift(feature, label)
    return out
