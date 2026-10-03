# -*- coding: utf-8 -*-
"""V3_GPU_INFRA — GPU compute infrastructure for V3 research (INFRASTRUCTURE ONLY, no trading conclusions).

Allowed by the freeze task book: bootstrap/permutation kernels, vectorized tick features, batch
processing, 4GB-VRAM chunking, OOM fallback, CPU/GPU parity tests, benchmarks.
Forbidden: alpha sweeps, new hypotheses, parameter search, signal generation, DEMO/LIVE.

This module computes ONLY generic statistics given caller-provided arrays. It never places orders,
never generates signals, and contains no hypothesis logic.
"""
from __future__ import annotations
import numpy as np

VRAM_BUDGET_BYTES = 512 * 2 ** 20          # default working budget for a single chunked kernel call


def device_info():
    import torch
    info = {"torch": torch.__version__, "cuda_available": bool(torch.cuda.is_available())}
    if info["cuda_available"]:
        free, total = torch.cuda.mem_get_info()
        info.update({"device": torch.cuda.get_device_name(0),
                     "capability": list(torch.cuda.get_device_capability(0)),
                     "vram_total_mib": round(total / 2 ** 20, 1),
                     "vram_free_mib": round(free / 2 ** 20, 1),
                     "cuda": torch.version.cuda})
    return info


# ---------------------------------------------------------------- R4-semantics kernels (CPU reference)
def cpu_sign_perm(x, reps=2000, seed=0):
    """Exact R4 semantics: two-sided sign-flip permutation p on the mean, numpy RNG."""
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    base = abs(float(np.mean(x)))
    rng = np.random.default_rng(seed)
    ge = 0
    for _ in range(reps):
        s = rng.integers(0, 2, size=n).astype(np.int8) * 2 - 1
        ge += int(abs(np.mean(x * s)) >= base)
    return float((ge + 1) / (reps + 1))


def cpu_block_bootstrap(x, reps=2000, nblocks=50, seed=1):
    """Exact R4 semantics: block bootstrap 95% percentile CI of the mean."""
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    bs = max(1, n // nblocks)
    nb = int(np.ceil(n / bs))
    pad = np.concatenate([x, np.full(nb * bs - n, np.nan)])
    blk = np.nanmean(pad.reshape(nb, bs), axis=1)
    rng = np.random.default_rng(seed)
    m = blk[rng.integers(0, nb, size=(reps, nb))].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def sign_perm_from_matrix(x, S):
    """Given pre-generated sign matrices S (reps, n) in {-1,+1}, compute p on any device.
    Deterministic given S — used for exact CPU/GPU parity."""
    import torch
    xt = x if torch.is_tensor(x) else torch.as_tensor(x, dtype=torch.float64)
    if torch.is_tensor(S):
        xt = xt.to(S.device).to(torch.float64)
    base = xt.mean().abs()
    means = (S * xt).mean(dim=1)
    ge = int((means.abs() >= base).sum())
    return float((ge + 1) / (S.shape[0] + 1))


# ---------------------------------------------------------------- GPU kernels (chunked, OOM-fallback)
def _sign_perm_chunked(x, reps, seed, dev, chunk):
    import torch
    xt = torch.as_tensor(np.asarray(x, dtype=np.float64), device=dev)
    n = xt.numel()
    base = xt.mean().abs()
    gen = torch.Generator(device="cpu"); gen.manual_seed(int(seed))
    ge, done = 0, 0
    while done < reps:
        c = min(chunk, reps - done)
        s = torch.randint(0, 2, (c, n), generator=gen, dtype=torch.int8).to(dev) * 2 - 1
        ge += int(((s.to(torch.float64) * xt).mean(dim=1).abs() >= base).sum())
        done += c
    return float((ge + 1) / (reps + 1))


def gpu_sign_perm(x, reps=2000, seed=0, dev="cuda", chunk=None, max_bytes=VRAM_BUDGET_BYTES):
    """GPU sign-flip permutation with (a) auto chunk sizing from a byte budget, (b) OOM fallback:
    halve the chunk and retry; if still failing at chunk=1, fall back to CPU numpy."""
    import torch
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    if chunk is None:
        chunk = max(1, int(max_bytes // (8 * n)))
    cur = chunk
    while True:
        try:
            return _sign_perm_chunked(x, reps, seed, dev, cur)
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            if cur <= 1:
                return cpu_sign_perm(x, reps, seed)          # last-resort CPU fallback
            cur = max(1, cur // 2)
        except RuntimeError as e:  # noqa: BLE001
            if "out of memory" not in str(e).lower() or cur <= 1:
                if "out of memory" in str(e).lower():
                    return cpu_sign_perm(x, reps, seed)
                raise
            torch.cuda.empty_cache(); cur = max(1, cur // 2)


def _boot_chunked(x, reps, nblocks, seed, dev, chunk):
    import torch
    xt = torch.as_tensor(np.asarray(x, dtype=np.float64), device=dev)
    n = xt.numel()
    bs = max(1, n // nblocks); nb = int(np.ceil(n / bs))
    pad = torch.nn.functional.pad(xt, (0, nb * bs - n), value=float("nan")).reshape(nb, bs)
    blk = pad.nanmean(dim=1)
    gen = torch.Generator(device="cpu"); gen.manual_seed(int(seed))
    outs = []
    done = 0
    while done < reps:
        c = min(chunk, reps - done)
        idx = torch.randint(0, nb, (c, nb), generator=gen)
        outs.append(blk[idx].mean(dim=1))
        done += c
    m = torch.cat(outs).sort().values
    lo = m[min(len(m) - 1, int(0.025 * len(m)))]
    hi = m[min(len(m) - 1, int(0.975 * len(m)))]
    return [float(lo), float(hi)]


def gpu_block_bootstrap(x, reps=2000, nblocks=50, seed=1, dev="cuda", chunk=None, max_bytes=VRAM_BUDGET_BYTES):
    import torch
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    if chunk is None:
        chunk = max(1, int(max_bytes // (8 * n)))
    cur = chunk
    while True:
        try:
            return _boot_chunked(x, reps, nblocks, seed, dev, cur)
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            if cur <= 1:
                return cpu_block_bootstrap(x, reps, nblocks, seed)
            cur = max(1, cur // 2)
        except RuntimeError as e:  # noqa: BLE001
            if "out of memory" not in str(e).lower():
                raise
            torch.cuda.empty_cache(); cur = max(1, cur // 2)


# ---------------------------------------------------------------- vectorized tick features (chunked)
def tick_features(ts_ms, bid, ask, w=300, chunk=4_000_000, dev="cpu"):
    """Vectorized, chunked: spread_bps, mid, per-tick return, trailing |ret| mean (w ticks).
    Pure feature computation — no signals."""
    import torch
    ts = torch.as_tensor(np.asarray(ts_ms), dtype=torch.float64, device=dev)
    b = torch.as_tensor(np.asarray(bid), dtype=torch.float64, device=dev)
    a = torch.as_tensor(np.asarray(ask), dtype=torch.float64, device=dev)
    n = ts.numel()
    mid = (a + b) / 2.0
    spread = (a - b) / mid * 1e4
    ret = torch.zeros(n, dtype=torch.float64, device=dev)
    ret[1:] = torch.diff(mid) / mid[:-1]
    ar = ret.abs()
    c = torch.cat([torch.zeros(1, dtype=torch.float64, device=dev), torch.cumsum(ar, dim=0)])
    idx = torch.arange(n, device=dev)
    lo = torch.clamp(idx + 1 - w, min=0)
    roll = (c[idx + 1] - c[lo]) / torch.clamp(idx + 1 - lo, min=1).to(torch.float64)
    return {"spread_bps": spread, "mid": mid, "ret": ret, "roll_absret": roll}


def tick_features_np(ts_ms, bid, ask, w=300):
    ts = np.asarray(ts_ms, dtype=np.float64); b = np.asarray(bid); a = np.asarray(ask)
    mid = (a + b) / 2.0
    spread = (a - b) / mid * 1e4
    ret = np.zeros(len(mid)); ret[1:] = np.diff(mid) / mid[:-1]
    ar = np.abs(ret)
    c = np.concatenate([[0.0], np.cumsum(ar)])
    idx = np.arange(len(mid))
    lo = np.maximum(idx + 1 - w, 0)
    roll = (c[idx + 1] - c[lo]) / np.maximum(idx + 1 - lo, 1)
    return {"spread_bps": spread, "mid": mid, "ret": ret, "roll_absret": roll}
