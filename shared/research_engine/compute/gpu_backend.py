# -*- coding: utf-8 -*-
"""compute/gpu_backend.py — GPU 后端（PyTorch CUDA，无需 CUDA Toolkit）。

4GB VRAM 安全原则（§19）：
  * 大 workload 一律分块处理（统计等价）
  * 每块峰值显存受控（默认预算 1.2GB）
  * 记录 torch.cuda.max_memory_allocated
OOM 由 dispatcher 捕获并回退 CPU（本类不做静默回退）。
"""
from __future__ import annotations

import time
from typing import Any, Callable

import numpy as np

from .common import BackendResult, elapsed_ms


def _torch():
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA not available")
    return torch


class GPUBackend:
    name = "gpu"

    def __init__(self, seed: int = 42, mem_budget_bytes: float = 1.2e9):
        self.seed = seed
        self._t = _torch()
        self.device = self._t.cuda.get_device_name(0)
        self.mem_budget = mem_budget_bytes

    # ---------------- Monte Carlo（分块） ----------------
    def run_monte_carlo(self, n_paths: int = 200_000, n_steps: int = 128,
                        mu: float = 0.0, sigma: float = 0.2, dt: float = 1.0 / (252.0 * 48.0),
                        s0: float = 2400.0, **kw) -> BackendResult:
        torch = self._t
        t0 = time.perf_counter()
        # 每块路径数：峰值 ~ 3 个 (n_steps, chunk) fp32 张量
        chunk = max(1, int(self.mem_budget / (3.0 * n_steps * 4)))
        n_chunks = int(np.ceil(n_paths / chunk))
        g = torch.Generator(device="cuda").manual_seed(self.seed)
        drift = (mu - 0.5 * sigma ** 2) * dt
        shock = sigma * np.sqrt(dt)
        final = []
        for _ in range(n_chunks):
            z = torch.randn((n_steps, chunk), device="cuda", generator=g)
            lp = torch.cumsum(drift + shock * z, dim=0)
            paths = s0 * torch.exp(torch.vstack([torch.zeros((1, chunk), device="cuda"), lp]))
            final.append(paths[-1])
            del z, lp, paths
        finals = torch.cat(final)[:n_paths]
        torch.cuda.synchronize()
        payload = {
            "task": "monte_carlo", "n_paths": n_paths, "n_steps": n_steps,
            "final_mean": float(finals.mean().item()), "final_std": float(finals.std().item()),
            "last_close": float(finals[0].item()),
        }
        return BackendResult(self.name, self.device, self.seed, elapsed_ms(t0), payload,
                             gpu_mem_used_mb=torch.cuda.max_memory_allocated() / 1e6)

    # ---------------- Bootstrap（分块） ----------------
    def run_bootstrap(self, x, n_iter: int = 2000, stat: str = "mean", full_dist: bool = False, **kw) -> BackendResult:
        if stat not in ("mean", "std"):
            raise ValueError(f"GPU bootstrap 暂不支持 stat={stat}")
        torch = self._t
        t0 = time.perf_counter()
        arr = np.asarray(x, dtype=np.float64)
        if not arr.flags.writeable:
            arr = arr.copy()
        xa = torch.as_tensor(arr, device="cuda")
        n = xa.shape[0]
        g = torch.Generator(device="cuda").manual_seed(self.seed)
        # 分块：idx(batch,n) int64 + gather fp64 → 每块 ~2 × batch×n×8 B
        batch = max(1, int(self.mem_budget / (2.0 * n * 8)))
        dists = []
        for b0 in range(0, n_iter, batch):
            b = min(batch, n_iter - b0)
            idx = torch.randint(0, n, (b, n), device="cuda", generator=g)
            samples = xa[idx]
            if stat == "mean":
                d = samples.mean(dim=1)
            else:
                d = samples.std(dim=1, correction=1)
            dists.append(d.cpu())
            del idx, samples, d
        dist = torch.cat(dists).numpy()
        torch.cuda.synchronize()
        payload = {
            "task": "bootstrap", "n_iter": n_iter, "n": int(n), "stat": stat,
            "dist_mean": float(dist.mean()), "dist_std": float(dist.std()),
            "ci95": [float(np.percentile(dist, 2.5)), float(np.percentile(dist, 97.5))],
        }
        if full_dist:
            payload["dist"] = dist.tolist()
        return BackendResult(self.name, self.device, self.seed, elapsed_ms(t0), payload,
                             gpu_mem_used_mb=torch.cuda.max_memory_allocated() / 1e6)

    # ---------------- Permutation（分块符号翻转） ----------------
    def run_permutation(self, x, n_iter: int = 2000, **kw) -> BackendResult:
        torch = self._t
        t0 = time.perf_counter()
        arr = np.asarray(x, dtype=np.float64)
        if not arr.flags.writeable:
            arr = arr.copy()
        xa = torch.as_tensor(arr, device="cuda")
        n = xa.shape[0]
        obs = float(xa.mean().item())
        g = torch.Generator(device="cuda").manual_seed(self.seed)
        batch = max(1, int(self.mem_budget / (2.0 * n * 8)))
        dists = []
        for b0 in range(0, n_iter, batch):
            b = min(batch, n_iter - b0)
            u = torch.rand((b, n), device="cuda", generator=g)
            signs = torch.where(u < 0.5, torch.tensor(-1.0, device="cuda"),
                                torch.tensor(1.0, device="cuda"))
            dists.append((signs * xa).mean(dim=1).cpu())
            del u, signs
        dist = torch.cat(dists).numpy()
        torch.cuda.synchronize()
        p_two = float((np.abs(dist) >= abs(obs)).mean())
        p_one = float((dist >= obs).mean())
        payload = {
            "task": "permutation", "n_iter": n_iter, "n": int(n),
            "stat_obs": float(obs), "p_value_two_sided": p_two, "p_value_greater": p_one,
            "dist_mean": float(dist.mean()), "dist_std": float(dist.std()),
        }
        return BackendResult(self.name, self.device, self.seed, elapsed_ms(t0), payload,
                             gpu_mem_used_mb=torch.cuda.max_memory_allocated() / 1e6)

    # ---------------- Parameter sweep（网格逐点 GPU 化由 fn 自行决定） ----------------
    def run_parameter_sweep(self, fn: Callable, grid: list[dict], **kw) -> BackendResult:
        t0 = time.perf_counter()
        out = []
        for params in grid:
            try:
                out.append({"params": params, "value": float(fn(params))})
            except Exception as e:
                out.append({"params": params, "error": f"{type(e).__name__}: {str(e)[:120]}"})
        payload = {"task": "parameter_sweep", "n_grid": len(grid), "results": out}
        return BackendResult(self.name, self.device, self.seed, elapsed_ms(t0), payload,
                             gpu_mem_used_mb=self._t.cuda.max_memory_allocated() / 1e6)


def get_gpu_backend(seed: int = 42) -> GPUBackend:
    return GPUBackend(seed=seed)
