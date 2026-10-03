# -*- coding: utf-8 -*-
"""alpha_engine — Alpha Discovery Engine（Phase 2 §10）。

原则（§9）：先研究 INFORMATION（IC/条件收益/分布漂移），不急着研究 STRATEGY。
原则（§14）：hypothesis 预登记并冻结 —— hypothesis_registry.json 生成后
  实验期间不得修改（防止 P-hacking）。
"""
from .hypothesis import Hypothesis, HypothesisFamily, FAMILIES
from .registry import register_candidate, update_status, summary as alpha_summary
from .pipeline import run_round

__all__ = ["Hypothesis", "HypothesisFamily", "FAMILIES",
           "register_candidate", "update_status", "alpha_summary", "run_round"]
