# -*- coding: utf-8 -*-
"""compute/cpu_backend.py — CPU 后端（numpy 实现）。

统一接口（均返回 BackendResult）：
  run_monte_carlo / run_bootstrap / run_permutation / run_parameter_sweep
兼容旧用法：CPUBackend(seed=11).run_bootstrap(x, n_iter=500)（返回 BackendResult）。
"""
from __future__ import annotations

import time
from typing import Any, Callable

import numpy as np

from .common import BackendResult, elapsed_ms


class CPUBackend:
    name = "cpu"
    device = "cpu"

    def __init__(self, seed: int = 42):
        self.seed = seed

    # ---------------- Monte Carlo ----------------
    def run_monte_carlo(self, n_paths: int = 200_000, n_steps: int = 128,
                        mu: float = 0.0, sigma: float = 0.2, dt: float = 1.0 / (252.0 * 48.0),
                        s0: float = 2400.0, **kw) -> BackendResult:
        t0 = time.perf_counter()
        rng = np.random.default_rng(self.seed)
        z = rng.standard_normal((n_steps, n_paths))
        drift = (mu - 0.5 * sigma ** 2) * dt
        shock = sigma * np.sqrt(dt)
        log_paths = np.cumsum(drift + shock * z, axis=0)
        paths = s0 * np.exp(np.vstack([np.zeros((1, n_paths)), log_paths]))
        payload = {
            "task": "monte_carlo", "n_paths": n_paths, "n_steps": n_steps,
            "final_mean": float(paths[-1].mean()), "final_std": float(paths[-1].std()),
            "last_close": float(paths[-1, 0]),
        }
        return BackendResult(self.name, self.device, self.seed, elapsed_ms(t0), payload)

    # ---------------- Bootstrap ----------------
    @staticmethod
    def _bootstrap_stat(dist: np.ndarray, stat: str) -> np.ndarray:
        if stat == "mean":
            return dist.mean(axis=1)
        if stat == "std":
            return dist.std(axis=1, ddof=1)
        if stat == "median":
            return np.median(dist, axis=1)
        raise ValueError(f"unsupported stat: {stat}")

    def run_bootstrap(self, x, n_iter: int = 2000, stat: str = "mean", full_dist: bool = False, **kw) -> BackendResult:
        t0 = time.perf_counter()
        xa = np.asarray(x, dtype=float)
        n = len(xa)
        rng = np.random.default_rng(self.seed)
        idx = rng.integers(0, n, size=(n_iter, n))
        dist = self._bootstrap_stat(xa[idx], stat)
        payload = {
            "task": "bootstrap", "n_iter": n_iter, "n": n, "stat": stat,
            "dist_mean": float(dist.mean()), "dist_std": float(dist.std()),
            "ci95": [float(np.percentile(dist, 2.5)), float(np.percentile(dist, 97.5))],
        }
        if full_dist:
            payload["dist"] = dist.tolist()
        return BackendResult(self.name, self.device, self.seed, elapsed_ms(t0), payload)

    # ---------------- Permutation（符号翻转） ----------------
    def run_permutation(self, x, n_iter: int = 2000, **kw) -> BackendResult:
        t0 = time.perf_counter()
        xa = np.asarray(x, dtype=float)
        n = len(xa)
        rng = np.random.default_rng(self.seed)
        obs = xa.mean()
        signs = rng.choice([-1.0, 1.0], size=(n_iter, n))
        dist = (signs * xa).mean(axis=1)
        p_two = float((np.abs(dist) >= abs(obs)).mean())
        p_one = float((dist >= obs).mean())
        payload = {
            "task": "permutation", "n_iter": n_iter, "n": n,
            "stat_obs": float(obs), "p_value_two_sided": p_two, "p_value_greater": p_one,
            "dist_mean": float(dist.mean()), "dist_std": float(dist.std()),
        }
        return BackendResult(self.name, self.device, self.seed, elapsed_ms(t0), payload)

    # ---------------- Parameter sweep ----------------
    def run_parameter_sweep(self, fn: Callable, grid: list[dict], **kw) -> BackendResult:
        """fn(params: dict) -> float；串行网格搜索。"""
        t0 = time.perf_counter()
        out = []
        for params in grid:
            try:
                out.append({"params": params, "value": float(fn(params))})
            except Exception as e:
                out.append({"params": params, "error": f"{type(e).__name__}: {str(e)[:120]}"})
        payload = {"task": "parameter_sweep", "n_grid": len(grid), "results": out}
        return BackendResult(self.name, self.device, self.seed, elapsed_ms(t0), payload)


def get_cpu_backend(seed: int = 42) -> CPUBackend:
    return CPUBackend(seed=seed)
