# -*- coding: utf-8 -*-
"""experiments — 内置可复现实验（已知答案 + 反过拟合）。"""
from .registry import EXPERIMENTS, get_experiment, list_experiments
from . import base, experiment_a, experiment_b, experiment_c, anti_overfit  # noqa: F401 (注册副作用)

__all__ = ["EXPERIMENTS", "get_experiment", "list_experiments"]
