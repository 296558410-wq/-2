# -*- coding: utf-8 -*-
"""compute — CPU/GPU 统一计算层。"""
from .common import BackendResult, estimate_workload_bytes, gpu_available, vram_bytes
from .cpu_backend import CPUBackend
from .gpu_backend import GPUBackend
from .dispatcher import (Dispatcher, get_backend, run_bootstrap,
                         run_permutation, run_monte_carlo, run_parameter_sweep)

__all__ = ["BackendResult", "CPUBackend", "GPUBackend", "Dispatcher",
           "get_backend", "run_bootstrap", "run_permutation",
           "run_monte_carlo", "run_parameter_sweep",
           "estimate_workload_bytes", "gpu_available", "vram_bytes"]
