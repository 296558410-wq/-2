# -*- coding: utf-8 -*-
"""backends.py — 兼容层：统一导出 CPU/GPU backend 与便捷入口。

新规范实现位于 research_engine.compute（v0.2+）；本模块仅做再导出，
保持旧代码/notebook `from research_engine.backends import CPUBackend` 可用。
"""
from .compute.common import BackendResult, estimate_workload_bytes, gpu_available, vram_bytes
from .compute.cpu_backend import CPUBackend
from .compute.gpu_backend import GPUBackend
from .compute.dispatcher import (Dispatcher, get_backend, run_bootstrap,
                                 run_permutation, run_monte_carlo, run_parameter_sweep)

__all__ = ["BackendResult", "CPUBackend", "GPUBackend", "Dispatcher", "get_backend",
           "run_bootstrap", "run_permutation", "run_monte_carlo", "run_parameter_sweep",
           "estimate_workload_bytes", "gpu_available", "vram_bytes"]
