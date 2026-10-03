# -*- coding: utf-8 -*-
"""research_engine — AIQuant 量化研究引擎（Phase 1 Foundation, v0.2）。

统一研究协议：
  * 任何研究 = Experiment（core.experiment.ExperimentRunner）
  * 数据集带版本（core.dataset.SyntheticXAUUSDGenerator）
  * 特征/标签严格时间对齐，禁止 look-ahead（core.feature.assert_no_lookahead）
  * CPU/GPU 自动调度（compute.dispatcher），4GB 显存安全
  * 统计验证：bootstrap / permutation / BH-FDR / robustness
  * OOS / Walk-Forward / Placebo / Cost-Stress 内置
  * 自动产物：experiments/<id>/{config.json, metrics.json, results.parquet, report.md, log.txt}
  * 结论词汇表：SUPPORTED / REJECTED / EDGE_UNCERTAIN
"""
from .compute import (BackendResult, CPUBackend, GPUBackend, Dispatcher, get_backend,
                      run_bootstrap, run_permutation, run_monte_carlo, run_parameter_sweep)
from .core import (CostModel, BacktestEngine, Experiment, ExperimentRunner,
                   FeatureSpec, build_features, assert_no_lookahead,
                   evaluate_quality, make_signal)
from .core.dataset import SyntheticXAUUSDGenerator, ensure_synthetic, SyntheticDataset
from .engine import ResearchEngine  # v0.1 兼容外壳

__version__ = "0.2.0"
__all__ = [
    "BackendResult", "CPUBackend", "GPUBackend", "Dispatcher", "get_backend",
    "run_bootstrap", "run_permutation", "run_monte_carlo", "run_parameter_sweep",
    "CostModel", "BacktestEngine", "Experiment", "ExperimentRunner",
    "FeatureSpec", "build_features", "assert_no_lookahead", "evaluate_quality",
    "make_signal", "SyntheticXAUUSDGenerator", "ensure_synthetic", "SyntheticDataset",
    "ResearchEngine",
]
