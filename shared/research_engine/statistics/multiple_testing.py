# -*- coding: utf-8 -*-
"""statistics/multiple_testing.py — 多重检验校正（§10）。

Benjamini-Hochberg FDR：100/1000/10000 个 hypothesis 时禁止直接使用原始 p-value。
"""
from __future__ import annotations

import numpy as np


def benjamini_hochberg(p_values, alpha: float = 0.05) -> dict:
    """BH-FDR。返回 {reject: bool[], q_values: float[], n_reject}。"""
    p = np.asarray(p_values, dtype=float)
    n = len(p)
    order = np.argsort(p)
    sorted_p = p[order]
    q = np.empty(n)
    running = 1.0
    for i in range(n - 1, -1, -1):
        running = min(sorted_p[i] * n / (i + 1), running)
        q[order[i]] = running
    reject = q < alpha
    return {"reject": reject.tolist(), "q_values": q.tolist(),
            "n_reject": int(reject.sum()), "alpha": alpha, "n": n}


def bonferroni(p_values, alpha: float = 0.05) -> dict:
    p = np.asarray(p_values, dtype=float)
    n = len(p)
    adj = np.minimum(p * n, 1.0)
    return {"adjusted": adj.tolist(), "reject": (adj < alpha).tolist(),
            "n_reject": int((adj < alpha).sum()), "alpha": alpha, "n": n}


def summarize_fdr(p_values, alpha: float = 0.05) -> dict:
    """多组 p 的 FDR 汇总：直接比较 BH vs Bonferroni 拒绝数，并警示过拟合风险。"""
    bh = benjamini_hochberg(p_values, alpha=alpha)
    bf = bonferroni(p_values, alpha=alpha)
    raw_sig = int((np.asarray(p_values) < alpha).sum())
    return {
        "n_hypotheses": int(len(p_values)),
        "raw_sig_at_alpha": raw_sig,
        "bh_reject": bh["n_reject"],
        "bonferroni_reject": bf["n_reject"],
        "min_p": float(np.min(p_values)),
        "max_q": float(np.max(bh["q_values"])) if len(p_values) else 0.0,
        "warning": "raw p-values are NOT evidence under multiple testing" if raw_sig > 0 else "",
    }
