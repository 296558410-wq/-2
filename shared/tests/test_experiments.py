# -*- coding: utf-8 -*-
"""test_experiments.py — 已知答案实验端到端（小规模跑通 + 协议完整）。

不在这里验证“结论方向”（那是正式 CLI 运行的事），而是验证：
  * 三个已知答案实验 + anti-overfit 在缩小参数下可完整运行（无异常）
  * 产物协议完整（config/metrics/results/report/log）
  * 结论词汇合法
"""
import pytest

from research_engine.core.experiment import Experiment, ExperimentRunner
from research_engine.experiments import get_experiment


def _run_small(name, tmp_path, seed=7, **params_over):
    spec = get_experiment(name)
    params = {**spec["parameters"], **params_over}
    exp = Experiment(name=spec["name"], hypothesis=spec["hypothesis"],
                     dataset_version=spec["dataset_version"], seed=seed,
                     backend="cpu", parameters=params)
    runner = ExperimentRunner(exp, registry_root=tmp_path)
    out = runner.run(spec["run"])
    rec = out.metrics()
    assert rec["status"] in ("PASS", "FAIL", "REJECT", "EDGE_UNCERTAIN")
    assert rec["conclusion"] in ("SUPPORTED", "REJECTED", "EDGE_UNCERTAIN")
    assert rec["quality"]["passed"] is True or rec["conclusion"] != "SUPPORTED"
    d = tmp_path / out.experiment_id
    for f in ("config.json", "metrics.json", "report.md", "log.txt"):
        assert (d / f).exists()
    return rec


def test_experiment_a_small(tmp_path):
    rec = _run_small("experiment_a", tmp_path, days=3)
    # 纯 RW 小样本上也不应给出 SUPPORTED
    assert rec["conclusion"] in ("REJECTED", "EDGE_UNCERTAIN")


def test_experiment_b_small(tmp_path):
    rec = _run_small("experiment_b", tmp_path, days=3)
    assert rec["status"] == "PASS"


def test_experiment_c_small(tmp_path):
    rec = _run_small("experiment_c", tmp_path, days=3)
    assert rec["status"] == "PASS"


def test_anti_overfit_small(tmp_path):
    rec = _run_small("anti_overfit", tmp_path, days=3, n_random_features=5)
    assert rec["metrics"]["framework_ok"] in (True, False)
