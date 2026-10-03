# -*- coding: utf-8 -*-
"""compute/common.py — 后端公共类型与工具。

BackendResult: 所有后端方法统一返回（含 backend/device/seed/elapsed_ms/payload/fallback）。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict

import numpy as np


def elapsed_ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000.0


@dataclass
class BackendResult:
    backend: str                       # "cpu" | "gpu"
    device: str                        # 具体设备名
    seed: int
    elapsed_ms: float
    payload: Dict[str, Any] = field(default_factory=dict)
    fallback_reason: str = ""          # 若发生 GPU→CPU 回退，记录原因
    gpu_mem_used_mb: float = 0.0       # GPU 峰值显存（MB）

    def to_dict(self) -> dict:
        return {
            "backend": self.backend,
            "device": self.device,
            "seed": self.seed,
            "elapsed_ms": round(self.elapsed_ms, 3),
            "fallback_reason": self.fallback_reason,
            "gpu_mem_used_mb": round(self.gpu_mem_used_mb, 1),
            **self.payload,
        }


def estimate_workload_bytes(task: str, **kw) -> float:
    """粗估主数组占用（字节）。用于 dispatcher 的 auto 决策，不做精确承诺。

    bootstrap/permutation 主数组 = n_iter × n × dtype_bytes
    monte_carlo = n_steps × n_paths × 4 (fp32)
    """
    try:
        if task in ("bootstrap", "permutation"):
            n = int(kw.get("n", kw.get("len_x", 0)))
            n_iter = int(kw.get("n_iter", 0))
            dt = 8 if task == "bootstrap" else 8  # fp64 输入
            return float(n_iter) * float(n) * dt
        if task == "monte_carlo":
            return float(kw.get("n_steps", 128)) * float(kw.get("n_paths", 0)) * 4.0
        if task == "matrix":
            n = float(kw.get("n", 0))
            return n * n * 4.0
    except Exception:
        pass
    return float("nan")


def gpu_available() -> bool:
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def vram_bytes() -> float:
    try:
        import torch
        if torch.cuda.is_available():
            return float(torch.cuda.get_device_properties(0).total_memory)
    except Exception:
        pass
    return 0.0


def mem_after_gc_mb() -> float:
    try:
        import torch
        if torch.cuda.is_available():
            return round(torch.cuda.max_memory_allocated() / 1e6, 1)
    except Exception:
        pass
    return 0.0
