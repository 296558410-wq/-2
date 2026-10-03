# -*- coding: utf-8 -*-
"""benchmarks/cpu_gpu.py — CPU vs GPU 自动基准（§9，CLI: python -m research_engine benchmark）。

对 bootstrap / permutation / monte_carlo 在多种规模下实测 CPU vs GPU（取最优 3 次），
并记录 dispatcher 的 auto 决策。GPU 更慢则如实记录。
"""
from __future__ import annotations

import time

import numpy as np

from ..compute import Dispatcher
from ..compute.common import gpu_available, vram_bytes


def _best(fn, repeat: int = 3) -> tuple[float, dict]:
    best_t, last = None, None
    for _ in range(repeat):
        t0 = time.perf_counter()
        last = fn()
        dt = (time.perf_counter() - t0) * 1000
        best_t = dt if best_t is None else min(best_t, dt)
    return best_t, last


def run_benchmark_suite(sizes=(1000, 10000, 100000), backend: str = "auto",
                        seed: int = 42) -> str:
    gpu = gpu_available()
    lines = ["# CPU vs GPU 自动基准（真实计时）", "",
             f"- 时间: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}",
             f"- GPU available: {gpu}" + (f" | VRAM {vram_bytes()/1e9:.1f}GB" if gpu else ""),
             "", "方法：同一任务同一 seed，CPU/GPU 各重复 3 次取最优；"
                  "auto 列为 dispatcher 实际决策（可能=CPU 或 GPU）。", ""]

    rows: list[list[str]] = []

    def bench(label: str, cpu_fn, gpu_fn, auto_ctx: dict):
        if backend in ("auto", "cpu"):
            t_cpu, _ = _best(cpu_fn)
        else:
            t_cpu = float("nan")
        if backend in ("auto", "gpu") and gpu:
            try:
                t_gpu, _ = _best(gpu_fn)
            except Exception as e:
                t_gpu = float("nan")
                lines.append(f"> GPU {label} 失败: {str(e)[:120]}")
        else:
            t_gpu = float("nan")
        # auto 决策记录
        d = Dispatcher(seed=seed, prefer="auto")
        dec_name, dec_reason = d.decide(**auto_ctx)
        speed = "" if not (t_cpu == t_cpu and t_gpu == t_gpu and t_gpu > 0) else f"{t_cpu/t_gpu:.1f}x"
        rows.append([label, f"{t_cpu:.1f}" if t_cpu == t_cpu else "-",
                     f"{t_gpu:.1f}" if t_gpu == t_gpu else "-",
                     speed if speed else "-", dec_name, dec_reason])
        return t_cpu, t_gpu

    x_sizes = list(sizes)
    for n in x_sizes:
        x = np.random.default_rng(seed).standard_normal(n)
        d = Dispatcher(seed=seed, prefer="auto")
        bench(f"bootstrap n={n} (iter=2000)",
              lambda: d.run_bootstrap(x, n_iter=2000, backend="cpu"),
              lambda: d.run_bootstrap(x, n_iter=2000, backend="gpu"),
              {"task": "bootstrap", "n_iter": 2000, "n": n})
        bench(f"permutation n={n} (iter=2000)",
              lambda: d.run_permutation(x, n_iter=2000, backend="cpu"),
              lambda: d.run_permutation(x, n_iter=2000, backend="gpu"),
              {"task": "permutation", "n_iter": 2000, "n": n})
    for np_ in (100_000, 1_000_000):
        d = Dispatcher(seed=seed, prefer="auto")
        bench(f"monte_carlo paths={np_} (steps=128)",
              lambda: d.run_monte_carlo(n_paths=np_, n_steps=128, backend="cpu"),
              lambda: d.run_monte_carlo(n_paths=np_, n_steps=128, backend="gpu"),
              {"task": "monte_carlo", "n_steps": 128, "n_paths": np_})

    lines += ["| workload | CPU ms | GPU ms | speedup | auto→ | 决策原因 |", "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append("| " + " | ".join(r) + " |")
    lines += ["", "注：GPU 启动/拷贝开销在小规模占主导 → auto 会选 CPU；"
                  "规模越大 GPU 优势越明显；若某行 GPU 更慢则如实保留数字。"]
    return "\n".join(lines)
