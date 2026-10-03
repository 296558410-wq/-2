# -*- coding: utf-8 -*-
"""statistics — 统计验证工具箱（§10）。"""
from .bootstrap import bootstrap_ci, run_bootstrap as run_bootstrap_stats
from .permutation import run_permutation as run_permutation_stats
from .multiple_testing import benjamini_hochberg, bonferroni, summarize_fdr
from .robustness import cost_stress_summary, subperiod_stability

__all__ = [
    "bootstrap_ci", "run_bootstrap_stats",
    "run_permutation_stats",
    "benjamini_hochberg", "bonferroni", "summarize_fdr",
    "cost_stress_summary", "subperiod_stability",
]
