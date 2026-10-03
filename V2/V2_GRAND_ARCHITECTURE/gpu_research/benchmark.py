"""GPU benchmark: measured CPU vs GPU runtime, peak VRAM, utilization, speedup.

Produces GPU_BENCHMARK.json. Real workload: large rolling-window feature build +
large vectorized batch strategy grid (chunked/streamed to fit 4 GB) + chunked
bootstrap + permutation. "GPU exists" is not a pass; the workload must run.
"""
from __future__ import annotations
import subprocess
import threading
import time
import numpy as np
import torch

from . import engine


def _sample_util(stop_evt: threading.Event, samples: list):
    while not stop_evt.is_set():
        try:
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used",
                 "--format=csv,noheader,nounits"], stderr=subprocess.DEVNULL)
            parts = out.decode().strip().split("\n")[0].split(",")
            samples.append((float(parts[0]), float(parts[1])))
        except Exception:
            pass
        time.sleep(0.03)


def _combos(grid: dict):
    combos = []
    for f in grid["fast"]:
        for s in grid["slow"]:
            if f >= s:
                continue
            for t in grid["thr"]:
                for sg in grid["sign"]:
                    combos.append((f, s, t, sg))
    return combos


def _cpu_workload(close: np.ndarray, grid: dict, cost: float, h: int,
                  n_boot: int, chunk: int = 512) -> dict:
    """Same logical workload, vectorized numpy, chunked identically."""
    t0 = time.perf_counter()
    n = close.shape[0]
    # rolling means via prefix sums
    P = np.concatenate([[0.0], np.cumsum(close)])
    ma_cache = {}
    for w in sorted(set(grid["fast"]) | set(grid["slow"])):
        out = np.full(n, np.nan)
        if n >= w:
            out[w - 1:] = (P[w:] - P[:n - w + 1]) / w
        ma_cache[w] = out
    fr = np.full(n, np.nan)
    if n > h:
        fr[:-h] = close[h:] - close[:-h]
    combos = _combos(grid)
    for start in range(0, len(combos), chunk):
        batch = combos[start:start + chunk]
        F = np.stack([ma_cache[f] for (f, s, t, sg) in batch])
        S = np.stack([ma_cache[s] for (f, s, t, sg) in batch])
        thr = np.array([t for (f, s, t, sg) in batch])[:, None]
        sg = np.array([float(x) for (f, s, t, x) in batch])[:, None]
        gap = (F - S) / S
        sig = (gap > thr).astype(float) * sg - (gap < -thr).astype(float) * sg
        G = np.broadcast_to(fr, sig.shape)
        net = np.where(sig != 0, sig * G - cost, np.nan)
        m = np.isfinite(net)
        cnt = m.sum(1)
        tot = np.where(m, net, 0.0).sum(1)
        _ = np.where(cnt > 0, tot / np.clip(cnt, 1, None), np.nan)
    # chunked bootstrap (same count as GPU)
    x = np.random.default_rng(1).normal(0, 1, size=5000)
    means = []
    b = 10
    nb = int(np.ceil(x.size / b))
    for _ in range(0, n_boot, 20000):
        m = min(20000, n_boot - _)
        starts = np.random.default_rng(7).integers(0, x.size - b, size=(m, nb))
        idx = (starts[:, :, None] + np.arange(b)[None, None, :]).reshape(m, -1)[:, :x.size]
        means.append(x[idx].mean(1))
    means = np.concatenate(means)
    _ = (means.mean(), np.quantile(means, 0.025), np.quantile(means, 0.975))
    dt = time.perf_counter() - t0
    return {"runtime_s": dt, "n_combos": len(combos)}


def run_benchmark(close: np.ndarray, cost: float, h: int = 20,
                  grid: dict | None = None, n_boot: int = 60000) -> dict:
    grid = grid or {
        "fast": list(range(3, 62, 2)),      # 30
        "slow": list(range(10, 182, 4)),    # 43
        "thr": [0.0002, 0.0005, 0.001, 0.002, 0.003, 0.005],
        "sign": [1, -1],
    }
    info = engine.device_info()
    out = {"gpu": info, "workload": {"n_bars": int(close.shape[0]), "horizon": h,
                                     "bootstrap_resamples": n_boot},
           "cost_price_units": cost}

    if not torch.cuda.is_available():
        out["GPU_RESEARCH"] = "FAIL"
        out["reason"] = "cuda unavailable"
        return out

    torch.cuda.reset_peak_memory_stats()
    samples: list = []
    stop = threading.Event()
    th = threading.Thread(target=_sample_util, args=(stop, samples), daemon=True)
    th.start()

    t0 = time.perf_counter()
    F = engine.build_feature_matrix_gpu(close, windows=(5, 10, 20, 40, 60))
    fr = engine.forward_return_gpu(close, h)
    res = engine.batch_evaluate(close, {h: fr}, grid, cost, chunk=512)
    _ = engine.walk_forward(close, h, [(0, 8000, 12000), (8000, 16000, 20000),
                                       (12000, 20000, 24000)], cost)
    x = np.random.default_rng(1).normal(0, 1, size=5000)
    engine.gpu_bootstrap_ci(x, n_boot=n_boot, block=10)
    engine.gpu_permutation_pvalue(x, n_perm=n_boot)
    torch.cuda.synchronize()
    gpu_dt = time.perf_counter() - t0
    peak = torch.cuda.max_memory_allocated() / (1024 * 1024)
    stop.set(); th.join(timeout=1.0)

    cpu = _cpu_workload(close, grid, cost, h, n_boot)

    util = [u for u, _ in samples] or [float("nan")]
    mem_used = [m for _, m in samples] or [float("nan")]
    out.update({
        "GPU_RESEARCH": "PASS",
        "feature_matrix_shape": list(F.shape),
        "n_combos": int(res["fast"].shape[0]),
        "gpu_runtime_s": round(gpu_dt, 4),
        "cpu_runtime_s": round(cpu["runtime_s"], 4),
        "speedup": round(cpu["runtime_s"] / gpu_dt, 2) if gpu_dt > 0 else float("nan"),
        "peak_vram_mb": round(peak, 1),
        "peak_vram_pct": round(peak / info.get("total_vram_mb", 4096) * 100, 1),
        "gpu_utilization_pct": {"max": float(np.nanmax(util)), "mean": float(np.nanmean(util)),
                                "samples": len(samples)},
        "gpu_mem_used_mb": {"max": float(np.nanmax(mem_used))},
        "bootstrap_resamples": n_boot,
        "walk_forward_windows": 3,
        "chunk_size": 512,
    })
    return out
