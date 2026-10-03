"""Incremental GPU batch for Phase 2.

Reuses Phase-1 `gpu_research/engine.py` (RTX A2000 4GB). Does NOT re-run the
full 13,296-combo search (spec section 12); only incremental work justified by
the new shadow outcomes: bootstrap + permutation + FDR, a small incremental
batch grid evaluation, and cross-strategy correlation.

Records GPU runtime, CPU baseline, speedup, VRAM and batch size -> GPU_USAGE_REPORT.md.

CLI:  python runner/gpu_batch.py
"""
from __future__ import annotations
import os
import sys
import time
import json
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths as PP  # noqa: E402
from common import data as D, cost as C, metrics as M  # noqa: E402
from strategy_factory import factory as F  # noqa: E402
from gpu_research import engine as GE  # noqa: E402

N_BOOT = 20000
N_PERM = 20000
BLOCK = 5
FDR_Q = 0.05
BATCH = 256


def _primary(spec):
    return min(PP.HORIZONS_MIN, key=lambda h: abs(h - spec.expected_horizon))


def _series():
    specs = F.generate_specs()
    outcomes = PP.jl_read(PP.OUTCOMES)
    cost = None
    df15, man = D.load_research_dataset("15min")
    cost = C.round_trip_cost_price(df15["spread"].to_numpy())
    nets = {}
    for s in specs:
        prim = _primary(s)
        xs = []
        for o in outcomes:
            if o.get("source") != "SHADOW" or o["strategy_id"] != s.strategy_id or o["horizon_min"] != prim:
                continue
            if o.get("data_gap") or o.get("future_return") is None:
                continue
            xs.append(float(o["future_return"]) - cost)
        nets[s.strategy_id] = np.asarray(xs, dtype=np.float64)
    return specs, nets, cost, man


def _cpu_bootstrap(x, n_boot, block, seed):
    x = x[np.isfinite(x)]
    n = x.size
    if n < block * 2:
        return float("nan")
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / block))
    idx = (rng.integers(0, n - block, size=(n_boot, nb))[:, :, None] + np.arange(block)).reshape(n_boot, -1)[:, :n]
    return float(np.quantile(x[idx].mean(axis=1), 0.025))


def run_gpu():
    PP.ensure_dirs()
    t0 = time.time()
    specs, nets, cost, man = _series()
    info = GE.device_info()
    gpu_stats = {}
    # --- GPU cumulative bootstrap + permutation across all strategies ---
    torch.cuda.reset_peak_memory_stats() if torch.cuda.is_available() else None
    t_gpu0 = time.time()
    gross_map = {}
    raw_p = {}
    for s in specs:
        x = nets[s.strategy_id]
        sid = s.strategy_id
        if x.size >= BLOCK * 2 and np.isfinite(x).sum() >= 10:
            mean, lo, hi = GE.gpu_bootstrap_ci(x, n_boot=N_BOOT, block=BLOCK, seed=PP.SEED)
            obs, p = GE.gpu_permutation_pvalue(x + cost, n_perm=N_PERM, seed=PP.SEED)
        else:
            mean = lo = hi = float("nan"); obs = p = float("nan")
        raw_p[sid] = float(p)
        gpu_stats[sid] = {"bootstrap": {"mean": _f(mean), "lo": _f(lo), "hi": _f(hi)},
                          "permutation": {"obs": _f(obs), "p": _f(p)}, "n_eff": int(x.size)}
        gross_map[sid] = x
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    t_gpu = time.time() - t_gpu0
    peak = (torch.cuda.max_memory_allocated() / (1024 * 1024)) if torch.cuda.is_available() else 0.0

    # --- CPU baseline: same bootstrap on the largest series, equal n_boot ---
    big = max(nets.values(), key=lambda a: a.size) if nets else np.asarray([])
    t_cpu0 = time.time()
    _cpu_bootstrap(big, N_BOOT, BLOCK, PP.SEED)
    t_cpu = time.time() - t_cpu0
    cpu_seq = t_cpu
    # scale CPU baseline to the same number of series as GPU processed
    n_series = max(1, sum(1 for v in nets.values() if v.size >= BLOCK * 2))
    cpu_scaled = cpu_seq * n_series
    speedup = (cpu_scaled / t_gpu) if t_gpu > 0 else float("nan")

    # --- FDR across strategies (BH) ---
    pvals = [raw_p[s.strategy_id] for s in specs]
    q = M.benjamini_hochberg(pvals, FDR_Q)
    for s, ok in zip(specs, q):
        gpu_stats[s.strategy_id]["fdr_pass"] = bool(ok)

    # --- fair pooled benchmark: identical large bootstrap on GPU vs CPU ---
    pool = np.concatenate([v for v in nets.values() if v.size]) if nets else np.asarray([])
    pool = pool[np.isfinite(pool)]
    bench_n = 60000
    t_pg = time.time()
    GE.gpu_bootstrap_ci(pool, n_boot=bench_n, block=10, seed=PP.SEED)
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    bench_gpu = time.time() - t_pg
    t_pc = time.time()
    _cpu_bootstrap(pool, bench_n, 10, PP.SEED)
    bench_cpu = time.time() - t_pc
    bench_speedup = (bench_cpu / bench_gpu) if bench_gpu > 0 else float("nan")

    # --- incremental batch grid (small; NOT the full 13,296 search) ---
    close = df15_close()
    fr = {20: GE.forward_return_gpu(close, 20)}
    grid = {"fast": [5, 10, 20], "slow": [20, 40, 60], "thr": [0.0005, 0.001], "sign": [1, -1]}
    n_combos = len([1 for f in grid["fast"] for s in grid["slow"] if f < s
                    for _t in grid["thr"] for _s in grid["sign"]])
    t_b0 = time.time()
    be = GE.batch_evaluate(close, fr, grid, cost, chunk=BATCH)
    t_batch = time.time() - t_b0

    meta = {
        "device": info.get("device"), "cuda": bool(torch.cuda.is_available()),
        "gpu_runtime_s": round(t_gpu, 4), "cpu_runtime_s": round(cpu_scaled, 4),
        "cpu_single_series_s": round(cpu_seq, 4), "speedup": round(speedup, 2),
        "peak_vram_mb": round(peak, 1), "batch": BATCH,
        "n_bootstrap": N_BOOT, "n_permutation": N_PERM, "block": BLOCK, "fdr_q": FDR_Q,
        "n_series": n_series, "incremental_combos": n_combos, "incremental_batch_s": round(t_batch, 4),
        "pool_size": int(pool.size), "bench_n_boot": bench_n,
        "bench_gpu_s": round(bench_gpu, 4), "bench_cpu_s": round(bench_cpu, 4),
        "bench_speedup": round(float(bench_speedup), 2),
        "purpose": "incremental bootstrap/permutation/FDR on shadow outcomes + small incremental grid; "
                   "full 13,296-combo search intentionally NOT re-run (spec section 12)",
    }
    out = {"strategies": gpu_stats, "meta": meta, "generated_utc": PP.now_utc()}
    PP.write_json_if_changed(os.path.join(PP.SHADOW, "gpu_stats.json"), out,
                             ignore_keys=("generated_utc",))
    PP.write_text_if_changed(PP.GPU_REPORT, _gpu_md(out))
    PP.log_event("gpu_batch", {"speedup": meta["speedup"], "peak_vram_mb": meta["peak_vram_mb"]})
    print(f"[gpu_batch] device={info.get('device')} per_strategy_gpu={t_gpu:.3f}s "
          f"pooled_bench gpu={bench_gpu:.3f}s cpu={bench_cpu:.3f}s speedup={bench_speedup:.2f}x "
          f"peak={peak:.0f}MB combos={n_combos}")
    return out


_df15 = {}


def df15_close():
    if "close" not in _df15:
        df15, _ = D.load_research_dataset("15min")
        _df15["close"] = df15["close"].to_numpy(dtype=np.float64)
    return _df15["close"]


def _f(x):
    try:
        x = float(x)
        return x if np.isfinite(x) else None
    except Exception:
        return None


def _gpu_md(out):
    m = out["meta"]
    lines = ["# GPU_USAGE_REPORT", "",
             "> 复用 Phase-1 `gpu_research/engine.py`；**不重复** 13,296 组合全量搜索（spec §12），",
             "> 只做新增 shadow 结果驱动的增量批处理。", "",
             "## 真机与耗时", "",
             f"- device: **{m['device']}** (cuda={m['cuda']})",
             f"- per-strategy bootstrap+permutation GPU runtime: **{m['gpu_runtime_s']}s**",
             f"- pooled benchmark (identical {m['bench_n_boot']}-resample block bootstrap on "
             f"{m['pool_size']} values): GPU **{m['bench_gpu_s']}s** vs CPU **{m['bench_cpu_s']}s** "
             f"→ speedup **{m['bench_speedup']}x**",
             f"- peak VRAM: **{m['peak_vram_mb']}MB**, batch size: {m['batch']}",
             f"- n_bootstrap: {m['n_bootstrap']}, n_permutation: {m['n_permutation']}, block: {m['block']}, FDR q: {m['fdr_q']}",
             f"- series processed: {m['n_series']}; incremental grid combos: {m['incremental_combos']} ({m['incremental_batch_s']}s)",
             f"- purpose: {m['purpose']}", "",
             "## 每策略统计（GPU）", "",
             "| strategy_id | n_eff | boot_lo | boot_hi | perm_p | fdr_pass |",
             "|---|---|---|---|---|---|"]
    for sid, v in out["strategies"].items():
        b = v["bootstrap"]; p = v["permutation"]
        lines.append(f"| {sid} | {v['n_eff']} | {b.get('lo')} | {b.get('hi')} | {p.get('p')} | {v.get('fdr_pass')} |")
    lines += ["", "## 说明", "",
              "- GPU 仅用于**加速**，不改变任何口径；失败的统计仍如实标注。",
              "- CPU baseline 对同一序列做等量 bootstrap 后按序列数缩放比较。"]
    return "\n".join(lines) + "\n"


def main():
    run_gpu()


if __name__ == "__main__":
    main()
