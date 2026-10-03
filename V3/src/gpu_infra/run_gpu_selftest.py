# -*- coding: utf-8 -*-
"""V3_GPU_INFRA self-test: CPU/GPU parity, chunking, OOM fallback, determinism, benchmark.

INFRASTRUCTURE ONLY — no alpha, no hypotheses, no signals, no orders. Synthetic data only.
Writes: GPU_SELFTEST_RESULTS.json (+ prints summary).
"""
from __future__ import annotations
import datetime as dt, json, os, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:\AIQuant\research\hermes\trader_v3\research\v3_r4_temporal_f5")
import v3_gpu_lib as G  # noqa: E402
import torch  # noqa: E402

R = {"schema": "v3_gpu_infra_selftest/1", "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
     "purpose": "compute infrastructure verification only", "tests": {}}


def T(name, ok, detail):
    R["tests"][name] = {"verdict": "PASS" if ok else "FAIL", "detail": str(detail)[:300]}
    print(f"  {'PASS' if ok else 'FAIL'}  {name}  {str(detail)[:120]}")


R["device"] = G.device_info()
print("device:", json.dumps(R["device"]))

rng = np.random.default_rng(20261002)
n = 512
x = rng.normal(0, 0.01, size=n)
reps = 2000

# 1) exact CPU/GPU parity on identical sign matrices
S = (rng.integers(0, 2, size=(reps, n)).astype(np.int8) * 2 - 1).astype(np.float64)
p_cpu = G.sign_perm_from_matrix(x, torch.as_tensor(S))
p_gpu = G.sign_perm_from_matrix(torch.as_tensor(x, dtype=torch.float64), torch.as_tensor(S, device="cuda"))
T("parity_sign_perm_exact", abs(p_cpu - p_gpu) <= 1e-12, f"cpu={p_cpu} gpu={p_gpu}")

# 2) chunked matrix accumulation invariance
xt = torch.as_tensor(x, dtype=torch.float64); St = torch.as_tensor(S)
means_full = (St * xt).mean(dim=1)
chunks = torch.cat([((St[i:i + 64] * xt).mean(dim=1)) for i in range(0, reps, 64)])
T("chunk_invariance", int((means_full - chunks).abs().max().item() * 1e12) == 0, "chunked vs full means identical")

# 3) determinism (same seed twice on GPU)
p1 = G.gpu_sign_perm(x, reps=500, seed=7, dev="cuda")
p2 = G.gpu_sign_perm(x, reps=500, seed=7, dev="cuda")
T("determinism_same_seed", p1 == p2, f"p={p1} twice equal")

# 4) OOM fallback mechanics: inject a synthetic OOM once -> must retry smaller & still return
orig = G._sign_perm_chunked
state = {"raised": 0}


def flaky(x_, reps_, seed_, dev_, chunk_):
    if state["raised"] == 0:
        state["raised"] = 1
        raise torch.cuda.OutOfMemoryError("synthetic OOM for fallback test")
    return orig(x_, reps_, seed_, dev_, chunk_)


G._sign_perm_chunked = flaky
p_fb = G.gpu_sign_perm(x, reps=300, seed=3, dev="cuda", chunk=100, max_bytes=10 ** 9)
G._sign_perm_chunked = orig
ref = G.gpu_sign_perm(x, reps=300, seed=3, dev="cuda", chunk=100)
T("oom_fallback_recovers", state["raised"] == 1 and p_fb == ref, f"recovered p={p_fb} == ref {ref}")

# 5) true tiny-budget run (chunk=1 path) + VRAM no-leak check
free0, _ = torch.cuda.mem_get_info()
p_tiny = G.gpu_sign_perm(x, reps=200, seed=5, dev="cuda", max_bytes=8)
torch.cuda.empty_cache()
free1, _ = torch.cuda.mem_get_info()
T("tiny_chunk_runs", 0.0 <= p_tiny <= 1.0, f"p={p_tiny}")
T("vram_no_growth", free1 >= free0 - 64 * 2 ** 20, f"free {free0/2**20:.0f}->{free1/2**20:.0f} MiB")

# 6) tick features parity + batch mode
m = 500_000
ts = np.sort(rng.integers(0, 86_400_000, size=m)).astype(np.int64)
bid = 4000 + np.cumsum(rng.normal(0, 0.01, size=m)); ask = bid + 0.14
f_np = G.tick_features_np(ts, bid, ask)
f_gp = G.tick_features(ts, bid, ask, dev="cuda")
dmax = max(float((torch.as_tensor(f_np[k]) - f_gp[k].cpu()).abs().max()) for k in ("spread_bps", "ret", "roll_absret"))
T("tick_features_parity", dmax < 1e-9, f"max|diff|={dmax:.2e} over {m} ticks")
# batch processing: 4 slices -> concat equals single pass
parts = []
for i in range(0, m, m // 4):
    sl = slice(i, i + m // 4)
    parts.append(G.tick_features(ts[sl], bid[sl], ask[sl], w=300, dev="cuda"))
batch_spread = torch.cat([p["spread_bps"] for p in parts])
T("batch_processing_parity", float((batch_spread - f_gp["spread_bps"]).abs().max()) < 1e-9, "4-way batch == single pass")

# 7) benchmark: R4-semantics permutation + bootstrap, CPU vs GPU
xb = rng.normal(0, 0.001, size=1000)
t0 = time.perf_counter(); pc = G.cpu_sign_perm(xb, reps=4000, seed=11); t_cpu = time.perf_counter() - t0
torch.cuda.synchronize()
t0 = time.perf_counter(); pg = G.gpu_sign_perm(xb, reps=4000, seed=11, dev="cuda"); torch.cuda.synchronize(); t_gpu = time.perf_counter() - t0
t0 = time.perf_counter(); bc = G.cpu_block_bootstrap(xb, reps=2000, nblocks=50, seed=12); t_bc = time.perf_counter() - t0
t0 = time.perf_counter(); bg = G.gpu_block_bootstrap(xb, reps=2000, nblocks=50, seed=12, dev="cuda"); torch.cuda.synchronize(); t_bg = time.perf_counter() - t0
R["benchmark"] = {"perm_cpu_s": round(t_cpu, 3), "perm_gpu_s": round(t_gpu, 3), "perm_speedup": round(t_cpu / max(t_gpu, 1e-9), 2),
                   "boot_cpu_s": round(t_bc, 3), "boot_gpu_s": round(t_bg, 3), "boot_speedup": round(t_bc / max(t_bg, 1e-9), 2),
                   "config": {"reps_perm": 4000, "n": 1000, "reps_boot": 2000, "nblocks": 50}}
print("benchmark:", json.dumps(R["benchmark"]))

npass = sum(1 for t in R["tests"].values() if t["verdict"] == "PASS")
R["verdict"] = "GPU_INFRA_SELFTEST_PASS" if npass == len(R["tests"]) else "GPU_INFRA_SELFTEST_FAIL"
R["passed"] = npass; R["total"] = len(R["tests"])
json.dump(R, open(os.path.join(HERE, "GPU_SELFTEST_RESULTS.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
print(f"{npass}/{len(R['tests'])} -> {R['verdict']}")
