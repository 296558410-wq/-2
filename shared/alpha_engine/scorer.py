# -*- coding: utf-8 -*-
"""alpha_engine/scorer.py — 单候选评分聚合（供 pipeline 调用）。

把 evaluator/filters 结果合成为候选记录：
  stage: RAW → OOS_SIG → FDR → WF → COST → SUBPERIOD → FINAL
"""
from __future__ import annotations

import numpy as np


def make_candidate_record(h: dict, info: dict, perm: dict, boot: dict) -> dict:
    return {
        "hypothesis_id": h["hypothesis_id"],
        "family": h["family"],
        "feature": h["feature"],
        "label": h["label"],
        "holding": h["holding"],
        "expected_direction": h["expected_direction"],
        "info": info,
        "perm": perm,
        "bootstrap": boot,
        "stage": "RAW",
    }


def apply_oos_stage(rec: dict, alpha: float = 0.05) -> dict:
    """OOS 显著性门槛：|perm p| < alpha 且方向与 expected 一致（"|" 只看显著）。"""
    p = rec["perm"]["p_value"]
    ic = rec["perm"]["ic_oos"]
    exp = rec["expected_direction"]
    if exp == "|":
        ok = p < alpha
    else:
        want = 1.0 if exp == "+" else -1.0
        ok = p < alpha and (np.sign(ic) == want or abs(ic) < 1e-12 and p >= alpha)
    rec["stage"] = "OOS_SIG" if ok else "REJECTED_OOS"
    return rec
