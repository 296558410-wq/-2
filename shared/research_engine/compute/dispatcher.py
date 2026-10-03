# -*- coding: utf-8 -*-
"""compute/dispatcher.py — CPU/GPU 自动调度（§7）。

auto 决策规则（非纯数据量硬编码）：
  1. GPU 不可用 → CPU（记录原因）
  2. 估算主数组 > VRAM×0.45 → CPU（内存受限，记录原因）
  3. 估算主数组 < 1MB → CPU（GPU 启动/拷贝开销主导，记录原因）
  4. 其余 → GPU
GPU 执行遇 CUDA OOM → 自动回退 CPU 并记录 fallback_reason。
每次调用记录：workload size / estimated memory / backend / execution time / GPU device / fallback reason。
"""
from __future__ import annotations

from typing import Any, Callable

from .common import (BackendResult, estimate_workload_bytes, gpu_available,
                     vram_bytes)
from .cpu_backend import CPUBackend
from .gpu_backend import GPUBackend

CPU_SMALL_BYTES = 1_000_000   # <1MB 估算 → CPU
GPU_MEM_FRACTION = 0.45


class Dispatcher:
    def __init__(self, seed: int = 42, prefer: str = "auto"):
        self.seed = seed
        self.prefer = prefer if prefer in ("auto", "cpu", "gpu") else "auto"
        self._cpu = CPUBackend(seed=seed)
        self._gpu = None
        self.decisions: list[dict] = []

    # ---- 决策 ----
    def decide(self, task: str, **kw) -> tuple[str, str]:
        """返回 (backend_name, reason)。"""
        est = estimate_workload_bytes(task, **kw)
        if self.prefer == "cpu":
            return "cpu", "prefer=cpu"
        if self.prefer == "gpu":
            if gpu_available():
                return "gpu", "prefer=gpu"
            return "cpu", "prefer=gpu but CUDA unavailable"
        # auto
        if not gpu_available():
            return "cpu", "CUDA unavailable"
        vram = vram_bytes()
        if not (est > 0):
            return "gpu", "GPU available, estimate n/a"
        if est > vram * GPU_MEM_FRACTION:
            return "cpu", f"est {est/1e6:.0f}MB > {GPU_MEM_FRACTION*100:.0f}% VRAM ({vram/1e9:.1f}GB)"
        if est < CPU_SMALL_BYTES:
            return "cpu", f"est {est/1e6:.3f}MB < small-workload threshold (1MB)"
        return "gpu", f"est {est/1e6:.0f}MB fits budget"

    def _log(self, rec: dict) -> None:
        self.decisions.append(rec)

    # ---- 统一执行入口（带 OOM 回退） ----
    def _run(self, task: str, fn_cpu: Callable, fn_gpu: Callable, **kw) -> BackendResult:
        name, reason = self.decide(task, **kw)
        start_info = {
            "task": task, "decided_backend": name, "reason": reason,
            "estimated_bytes": estimate_workload_bytes(task, **kw),
        }
        try:
            if name == "gpu":
                self._ensure_gpu()
                try:
                    res = fn_gpu()
                    self._log({**start_info, "ok": True, "backend": "gpu",
                               "elapsed_ms": res.elapsed_ms,
                               "gpu_mem_used_mb": res.gpu_mem_used_mb})
                    return res
                except Exception as e:
                    if "out of memory" in str(e).lower() or "cuda" in str(e).lower() and "memory" in str(e).lower():
                        # OOM → 回退 CPU
                        res = fn_cpu()
                        res.backend = "cpu"
                        res.device = "cpu"
                        res.fallback_reason = f"gpu OOM: {str(e)[:150]}"
                        self._log({**start_info, "ok": True, "backend": "cpu",
                                   "fallback_reason": res.fallback_reason})
                        return res
                    raise
            res = fn_cpu()
            self._log({**start_info, "ok": True, "backend": "cpu", "elapsed_ms": res.elapsed_ms})
            return res
        except Exception as e:
            self._log({**start_info, "ok": False, "error": str(e)[:200]})
            raise

    def _ensure_gpu(self) -> None:
        if self._gpu is None:
            self._gpu = GPUBackend(seed=self.seed)

    # ---- 统一统计接口（§8） ----
    def run_monte_carlo(self, n_paths=200_000, n_steps=128, mu=0.0, sigma=0.2,
                        dt=1.0 / (252.0 * 48.0), s0=2400.0, backend="auto") -> BackendResult:
        if backend in ("auto", "cpu", "gpu"):
            self.prefer = backend if backend != "auto" else self.prefer
        return self._run("monte_carlo",
                         lambda: self._cpu.run_monte_carlo(n_paths, n_steps, mu, sigma, dt, s0),
                         lambda: self._gpu.run_monte_carlo(n_paths, n_steps, mu, sigma, dt, s0),
                         n_paths=n_paths, n_steps=n_steps)

    def run_bootstrap(self, x, n_iter=2000, stat="mean", backend="auto") -> BackendResult:
        if backend in ("auto", "cpu", "gpu"):
            self.prefer = backend if backend != "auto" else self.prefer
        xa = list(x) if not hasattr(x, "__len__") else x
        return self._run("bootstrap",
                         lambda: self._cpu.run_bootstrap(xa, n_iter=n_iter, stat=stat),
                         lambda: self._gpu.run_bootstrap(xa, n_iter=n_iter, stat=stat),
                         n_iter=n_iter, n=len(xa))

    def run_permutation(self, x, n_iter=2000, backend="auto") -> BackendResult:
        if backend in ("auto", "cpu", "gpu"):
            self.prefer = backend if backend != "auto" else self.prefer
        xa = list(x) if not hasattr(x, "__len__") else x
        return self._run("permutation",
                         lambda: self._cpu.run_permutation(xa, n_iter=n_iter),
                         lambda: self._gpu.run_permutation(xa, n_iter=n_iter),
                         n_iter=n_iter, n=len(xa))

    def run_parameter_sweep(self, fn: Callable, grid: list[dict], backend="auto") -> BackendResult:
        if backend in ("auto", "cpu", "gpu"):
            self.prefer = backend if backend != "auto" else self.prefer
        return self._run("parameter_sweep",
                         lambda: self._cpu.run_parameter_sweep(fn, grid),
                         lambda: self._gpu.run_parameter_sweep(fn, grid),
                         n_grid=len(grid))

    def summary(self) -> dict:
        return {"prefer": self.prefer, "n_decisions": len(self.decisions),
                "last": self.decisions[-1] if self.decisions else None}


# 模块级便捷入口（统一 backend="auto"|"cpu"|"gpu"）
_default = None


def _get_default(prefer: str) -> Dispatcher:
    global _default
    if _default is None or _default.prefer != prefer:
        _default = Dispatcher(seed=42, prefer=prefer)
    return _default


def get_backend(name: str = "auto", seed: int = 42):
    """兼容旧 API：返回具体 backend 实例（auto→GPU 可用则 GPU）。"""
    if name == "cpu":
        return CPUBackend(seed=seed)
    if name == "gpu":
        return GPUBackend(seed=seed)
    return GPUBackend(seed=seed) if gpu_available() else CPUBackend(seed=seed)


def run_bootstrap(x, n_iter=2000, stat="mean", backend="auto", seed=42) -> dict:
    d = Dispatcher(seed=seed, prefer=backend)
    return d.run_bootstrap(x, n_iter=n_iter, stat=stat, backend=backend).to_dict()


def run_permutation(x, n_iter=2000, backend="auto", seed=42) -> dict:
    d = Dispatcher(seed=seed, prefer=backend)
    return d.run_permutation(x, n_iter=n_iter, backend=backend).to_dict()


def run_monte_carlo(n_paths=200_000, n_steps=128, backend="auto", seed=42, **kw) -> dict:
    d = Dispatcher(seed=seed, prefer=backend)
    return d.run_monte_carlo(n_paths=n_paths, n_steps=n_steps, backend=backend, **kw).to_dict()


def run_parameter_sweep(fn, grid, backend="auto", seed=42) -> dict:
    d = Dispatcher(seed=seed, prefer=backend)
    return d.run_parameter_sweep(fn, grid, backend=backend).to_dict()
