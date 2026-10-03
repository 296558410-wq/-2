# -*- coding: utf-8 -*-
"""core/experiment.py — 统一 Experiment Protocol（§3）。

Experiment ID: YYYYMMDD_HHMMSS_<name>（UTC）
生命周期：DRAFT → RUNNING → PASS/FAIL/REJECT/EDGE_UNCERTAIN
任何实验必须记录：hypothesis/dataset/feature_version/parameters/seed/git_commit/
machine/backend/start/end/metrics/validation/status + 质量门。
自动产出（registry 目录）：
  config.json / metrics.json / results.parquet / report.md / log.txt
"""
from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from ..registry.experiment_registry import ExperimentDir
from .quality import evaluate_quality, quality_summary_md

STATUSES = ("DRAFT", "RUNNING", "PASS", "FAIL", "REJECT", "EDGE_UNCERTAIN")
CONCLUSIONS = ("SUPPORTED", "REJECTED", "EDGE_UNCERTAIN")
FORBIDDEN_CONCLUSIONS = ("PROFITABLE", "GUARANTEED", "HIGH CONFIDENCE ALPHA")

ROOT = Path(__file__).resolve().parents[2]


def git_commit_short() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT),
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else "no-git"
    except Exception:
        return "no-git"


def machine_snapshot() -> dict:
    snap = {"host": platform.node(), "platform": platform.platform(),
            "python": platform.python_version(),
            "ts_utc": datetime.now(timezone.utc).isoformat()}
    try:
        import torch
        snap["torch"] = torch.__version__
        snap["cuda_available"] = bool(torch.cuda.is_available())
        if torch.cuda.is_available():
            p = torch.cuda.get_device_properties(0)
            snap["gpu"] = p.name
            snap["vram_gb"] = round(p.total_memory / 1e9, 2)
            snap["cc"] = f"{p.major}.{p.minor}"
    except Exception:
        pass
    return snap


@dataclass
class Experiment:
    name: str
    hypothesis: str
    dataset_version: str
    seed: int = 42
    backend: str = "auto"
    parameters: dict = field(default_factory=dict)
    feature_version: str = "features-v1"
    label_version: str = "labels-v1"
    status: str = "DRAFT"

    def new_id(self) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"{ts}_{self.name}"


class ExperimentRunner:
    """运行一个 Experiment 并落盘全部产物。"""

    def __init__(self, exp: Experiment, registry_root: Path | None = None):
        self.exp = exp
        self.registry = ExperimentDir(registry_root or (ROOT / "experiments"))
        self.start_ts = datetime.now(timezone.utc)

    def run(self, execute: Callable[["ExperimentCtx"], dict]) -> ExperimentDir:
        """execute(ctx) → dict，须包含:
           metrics: dict; results_df: pd.DataFrame; validation: dict;
           建议字段: status/conclusion/no_lookahead_checked/no_leakage/oos_exists/
           walk_forward_done/cost_included/multiple_testing_done/shuffle_test_done/
           placebo_test_done
        """
        exp_id = self.exp.new_id()
        ctx = ExperimentCtx(exp=self.exp, experiment_id=exp_id, registry=self.registry)
        self.registry.create(exp_id)
        self._log(ctx, "START " + exp_id)
        rec = self._base_record(exp_id, "RUNNING")
        self.registry.save_json(exp_id, "config.json", rec)

        t0 = time.perf_counter()
        try:
            result = execute(ctx)
        except Exception as e:
            import traceback
            self._log(ctx, "ERROR\n" + traceback.format_exc())
            rec = self._base_record(exp_id, "FAIL")
            rec["status"] = "FAIL"
            rec["error"] = f"{type(e).__name__}: {str(e)[:500]}"
            self.registry.save_json(exp_id, "metrics.json", {"status": "FAIL", "error": rec["error"]})
            self._write_report(ctx, rec)
            raise
        elapsed = time.perf_counter() - t0

        rec = self._base_record(exp_id, result.get("status", "PASS"))
        rec.update({
            "end_time": datetime.now(timezone.utc).isoformat(),
            "elapsed_s": round(elapsed, 2),
            "backend": self.exp.backend,
            "metrics": result.get("metrics", {}),
            "validation": result.get("validation", {}),
            "conclusion": _sanitize_conclusion(result.get("conclusion")),
            "no_lookahead_checked": bool(result.get("no_lookahead_checked")),
            "no_leakage": bool(result.get("no_leakage")),
            "oos_exists": bool(result.get("oos_exists")),
            "walk_forward_done": bool(result.get("walk_forward_done")),
            "cost_included": bool(result.get("cost_included")),
            "multiple_testing_done": bool(result.get("multiple_testing_done")),
            "shuffle_test_done": bool(result.get("shuffle_test_done")),
            "placebo_test_done": bool(result.get("placebo_test_done")),
        })
        q = evaluate_quality(rec)
        rec["quality"] = q.to_dict()
        # 质量门：关键项失败 → 不得 SUPPORTED
        if not q.passed and rec.get("conclusion") == "SUPPORTED":
            rec["conclusion"] = "EDGE_UNCERTAIN"
            rec["status"] = "REJECT" if result.get("status") == "PASS" else rec["status"]
            rec["quality"]["downgraded_to_uncertain"] = True

        self.registry.save_json(exp_id, "metrics.json", rec)
        df = result.get("results_df")
        if df is not None:
            self.registry.save_parquet(exp_id, "results.parquet", df)
        self._write_report(ctx, rec, extra=result)
        self._log(ctx, f"DONE {rec['status']} conclusion={rec.get('conclusion')}")
        return self.registry.get(exp_id)

    # ---- 内部 ----
    def _base_record(self, exp_id: str, status: str) -> dict:
        return {
            "experiment_id": exp_id,
            "name": self.exp.name,
            "hypothesis": self.exp.hypothesis,
            "status": status,
            "dataset_version": self.exp.dataset_version,
            "feature_version": self.exp.feature_version,
            "label_version": self.exp.label_version,
            "parameters": self.exp.parameters,
            "random_seed": self.exp.seed,
            "git_commit": git_commit_short(),
            "machine": machine_snapshot(),
            "start_time": self.start_ts.isoformat(),
        }

    def _write_report(self, ctx: "ExperimentCtx", rec: dict, extra: Optional[dict] = None) -> None:
        from .report import build_report_md
        md = build_report_md(rec, extra or {})
        self.registry.save_text(ctx.experiment_id, "report.md", md)

    def _log(self, ctx: "ExperimentCtx", line: str) -> None:
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.registry.append_text(ctx.experiment_id, "log.txt", f"[{ts}] {line}")


class ExperimentCtx:
    """传给 execute 的上下文：提供产物写入接口与常用服务。"""

    def __init__(self, exp: Experiment, experiment_id: str, registry: "ExperimentDir"):
        self.exp = exp
        self.experiment_id = experiment_id
        self.registry = registry

    def save_artifact(self, name: str, obj) -> None:
        self.registry.save_artifact(self.experiment_id, name, obj)

    def log(self, line: str) -> None:
        self.registry.append_text(self.experiment_id, "log.txt",
                                  f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] {line}")


def _sanitize_conclusion(c: Optional[str]) -> str:
    if c is None:
        return "EDGE_UNCERTAIN"
    c = str(c).upper()
    if c in FORBIDDEN_CONCLUSIONS:
        raise ValueError(f"禁止的结论词: {c}")
    return c if c in CONCLUSIONS else "EDGE_UNCERTAIN"
