# -*- coding: utf-8 -*-
"""engine.py — 兼容层：ResearchEngine 便捷外壳（v0.1 API 保留）。

新规范：研究必须走 core.experiment.ExperimentRunner（统一协议 + 产物落盘）。
本类保留旧式“跑一下记一下”用法：run_bootstrap / run_monte_carlo /
run_permutation / run_parameter_sweep，自动记录 backend/device/elapsed/seed。
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .compute import CPUBackend, Dispatcher, GPUBackend


class ResearchEngine:
    def __init__(self, backend: str = "auto", seed: int = 42, log_dir: str = "C:/AIQuant/logs"):
        self.seed = seed
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.dispatcher = Dispatcher(seed=seed, prefer=backend)
        self.history: list[dict] = []

    def run_bootstrap(self, x, n_iter=2000, stat="mean") -> dict:
        return self._record("bootstrap", self.dispatcher.run_bootstrap(x, n_iter, stat).to_dict())

    def run_monte_carlo(self, n_paths=200_000, n_steps=128, **kw) -> dict:
        return self._record("monte_carlo", self.dispatcher.run_monte_carlo(n_paths, n_steps, **kw).to_dict())

    def run_permutation(self, x, n_iter=2000) -> dict:
        return self._record("permutation", self.dispatcher.run_permutation(x, n_iter).to_dict())

    def run_parameter_sweep(self, fn, grid) -> dict:
        return self._record("parameter_sweep", self.dispatcher.run_parameter_sweep(fn, grid).to_dict())

    def _record(self, task: str, result: dict) -> dict:
        rec = {"experiment_id": f"adhoc-{datetime.now(timezone.utc).strftime('%H%M%S%f')}",
               "task": task, "ts_utc": datetime.now(timezone.utc).isoformat(),
               "result": result}
        self.history.append(rec)
        with open(self.log_dir / "research_engine.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    def summary(self) -> str:
        return json.dumps({"backend": self.dispatcher.prefer,
                           "runs": len(self.history)}, indent=2)
