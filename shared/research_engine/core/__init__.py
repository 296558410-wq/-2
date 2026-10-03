# -*- coding: utf-8 -*-
"""core — 核心协议：数据集/特征/信号/成本/回测/实验/报告/质量门。"""
from .cost import CostModel
from .backtest import BacktestEngine, BacktestResult, compute_metrics
from .signal import make_signal, positions_from_sign, positions_from_thresholds, SignalResult
from .feature import FeatureSpec, FeatureMatrix, build as build_features, assert_no_lookahead
from .quality import evaluate_quality
from .experiment import Experiment, ExperimentRunner, ExperimentCtx, git_commit_short

__all__ = ["CostModel", "BacktestEngine", "BacktestResult", "compute_metrics",
           "make_signal", "positions_from_sign", "positions_from_thresholds", "SignalResult",
           "FeatureSpec", "FeatureMatrix", "build_features", "assert_no_lookahead",
           "evaluate_quality", "Experiment", "ExperimentRunner", "ExperimentCtx",
           "git_commit_short"]
