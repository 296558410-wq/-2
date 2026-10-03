# -*- coding: utf-8 -*-
"""test_stats.py — 统计验证层 + 多重检验 + 切分 + 实验协议单元测试。"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from research_engine.compute import CPUBackend, Dispatcher, GPUBackend
from research_engine.core.cost import CostModel
from research_engine.core.experiment import Experiment, ExperimentRunner
from research_engine.core.quality import evaluate_quality
from research_engine.registry.experiment_registry import ExperimentDir
from research_engine.statistics.bootstrap import bootstrap_ci
from research_engine.statistics.multiple_testing import (benjamini_hochberg,
                                                         bonferroni, summarize_fdr)
from research_engine.statistics.permutation import time_permutation
from research_engine.validation import (label_shuffle_test, time_split,
                                        walk_forward_folds)
from research_engine.validation.walk_forward import walk_forward_evaluate


def test_cpu_bootstrap_reproducible():
    x = np.random.default_rng(0).standard_normal(5000)
    r1 = CPUBackend(seed=11).run_bootstrap(x, n_iter=500).to_dict()
    r2 = CPUBackend(seed=11).run_bootstrap(x, n_iter=500).to_dict()
    assert r1["dist_mean"] == r2["dist_mean"]
    assert abs(r1["dist_mean"]) < 0.05
    assert r1["ci95"][0] < r1["ci95"][1]


def test_bootstrap_ci_covers():
    x = np.random.default_rng(1).normal(1.0, 1.0, 2000)
    r = bootstrap_ci(x, stat_fn=lambda a: float(a.mean()), n_iter=2000, seed=2)
    assert r["ci_low"] < 1.0 < r["ci_high"]
    assert r["ci_low"] < r["est"] < r["ci_high"]


def test_gpu_backend_matches_cpu():
    torch = pytest.importorskip("torch")
    if not torch.cuda.is_available():
        pytest.skip("CUDA not available")
    x = np.random.default_rng(3).standard_normal(20000)
    cpu = CPUBackend(seed=7).run_bootstrap(x, n_iter=300).to_dict()
    gpu = GPUBackend(seed=7).run_bootstrap(x, n_iter=300).to_dict()
    assert cpu["backend"] == "cpu" and gpu["backend"] == "gpu"
    # CPU/GPU 使用不同 RNG 算法（numpy vs torch）→ 只要求统计一致（bootstrap 噪声内）
    se = float(x.std(ddof=1)) / np.sqrt(len(x))
    assert abs(cpu["dist_mean"] - gpu["dist_mean"]) < 4 * se
    # 同 seed 各自可复现
    cpu2 = CPUBackend(seed=7).run_bootstrap(x, n_iter=300).to_dict()
    assert cpu["dist_mean"] == cpu2["dist_mean"]


def test_dispatcher_auto_and_fallback():
    d = Dispatcher(seed=1, prefer="auto")
    x = np.random.default_rng(0).standard_normal(2000)
    res = d.run_bootstrap(x, n_iter=500, backend="auto")
    assert res.backend in ("cpu", "gpu")
    assert res.fallback_reason == "" or "oom" in res.fallback_reason.lower() or "cuda" in res.fallback_reason.lower()
    # 决策记录存在
    assert d.decisions and d.decisions[-1]["task"] == "bootstrap"


def test_bh_fdr_known():
    pvals = np.array([0.001, 0.01, 0.04, 0.2, 0.5])
    bh = benjamini_hochberg(pvals, alpha=0.05)
    assert bh["n_reject"] == 2
    bf = bonferroni(pvals, alpha=0.05)
    assert bf["n_reject"] == 1  # 0.001*5 < 0.05
    s = summarize_fdr(pvals)
    assert s["warning"] != ""


def test_label_shuffle_power():
    rng = np.random.default_rng(4)
    sig = np.sign(rng.normal(0, 1, 1000))
    rets = sig * 0.02 + rng.normal(0, 1, 1000) * 0.1  # 有真实信号
    r = label_shuffle_test(sig, rets, n_iter=500, seed=5)
    assert r["p_value"] < 0.05
    r2 = label_shuffle_test(sig, rng.normal(0, 1, 1000), n_iter=500, seed=6)
    assert r2["p_value"] > 0.01


def test_time_split_and_wf():
    sp = time_split(10000, 0.6, 0.2, 0.2)
    assert sp["train"].stop - sp["train"].start == 6000
    folds = walk_forward_folds(10000, n_folds=5, min_train=1000, val_frac=0.2, mode="expanding")
    assert len(folds) == 5
    for f in folds:
        assert f.test.start > f.train.stop
    # 评估函数可运行
    r = np.random.default_rng(0).normal(0, 1, 10000) * 0.001
    pos = np.zeros(10000)
    pos[::2] = 1.0
    out = walk_forward_evaluate(r, pos, folds, one_way_cost=1e-4)
    assert out["n_folds"] == 5
    assert "oos_sharpe_mean" in out


def test_time_permutation():
    r = np.random.default_rng(1).normal(0.0005, 0.01, 2000)
    tp = time_permutation(r, stat_fn=lambda x: float(x.mean()), n_iter=300, seed=2)
    assert 0 <= tp["p_value"] <= 1


def test_experiment_protocol_and_registry(tmp_path):
    calls = {}

    def execute(ctx):
        calls["id"] = ctx.experiment_id
        return {"metrics": {"x": 1.0},
                "results_df": pd.DataFrame({"a": [1, 2]}),
                "validation": {"ok": True},
                "status": "PASS", "conclusion": "SUPPORTED",
                "no_lookahead_checked": True, "no_leakage": True,
                "oos_exists": True, "walk_forward_done": True,
                "cost_included": True, "multiple_testing_done": True,
                "shuffle_test_done": True, "placebo_test_done": True,
                "seed_recorded": True, "git_commit_recorded": True,
                "dataset_version_recorded": True}

    exp = Experiment(name="unit_probe", hypothesis="h", dataset_version="v1",
                     seed=1, backend="cpu", parameters={"a": 1})
    runner = ExperimentRunner(exp, registry_root=Path(tmp_path))
    out = runner.run(execute)
    rec = out.metrics()
    assert rec["status"] == "PASS"
    assert rec["conclusion"] == "SUPPORTED"
    assert rec["quality"]["passed"] is True
    assert (Path(tmp_path) / out.experiment_id / "report.md").exists()
    assert (Path(tmp_path) / out.experiment_id / "results.parquet").exists()
    q = evaluate_quality({**rec, "no_lookahead_checked": False})
    assert q.passed is False


def test_quality_gate_blocks_supported():
    rec = {"no_lookahead_checked": False, "no_leakage": True, "oos_exists": True,
           "walk_forward_done": True, "cost_included": True, "multiple_testing_done": True,
           "shuffle_test_done": True, "placebo_test_done": True, "seed_recorded": True,
           "git_commit_recorded": True, "dataset_version_recorded": True}
    q = evaluate_quality(rec)
    assert not q.passed
    assert "no_lookahead_checked" in q.critical_failed


def test_forbidden_conclusion_rejected():
    from research_engine.core.experiment import _sanitize_conclusion
    with pytest.raises(ValueError):
        _sanitize_conclusion("PROFITABLE")
    assert _sanitize_conclusion("REJECTED") == "REJECTED"
    assert _sanitize_conclusion(None) == "EDGE_UNCERTAIN"


def test_cost_model_dict():
    cm = CostModel(spread_bps=1.0, commission_bps=0.5, slippage_bps=0.5)
    d = cm.to_dict()
    assert np.isclose(d["one_way_bps"], 1.5)
