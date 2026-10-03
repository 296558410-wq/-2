# -*- coding: utf-8 -*-
"""gpu_benchmark.py — CPU vs GPU 真实基准（写 reports/gpu_benchmark.md）。

覆盖测试 A-M：
A torch.cuda.is_available / B 设备识别 / C CC / D 矩阵乘 / E FP32 / F FP16 /
G BF16 / H Monte Carlo / I Bootstrap+Permutation / J XGBoost GPU / K LightGBM GPU /
L Numba CUDA / M CuPy 评估
原则：真实计时、真实结果；不支持/未装 → SKIP+REASON，绝不编造。
4GB VRAM 适配：MC/Bootstrap/Permutation 的 GPU 内核按块处理（统计等价），
单块峰值显存 <1.5GB；任何组出错按 FAIL 记录，不中断整轮。
用法: python benchmarks/gpu_benchmark.py
"""
from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "gpu_benchmark.md"

RESULTS: list[dict] = []


def rec(test: str, status: str, detail: str, extra: dict | None = None):
    row = {"test": test, "status": status, "detail": detail}
    if extra:
        row.update(extra)
    RESULTS.append(row)
    print(f"[{status:>4}] {test}: {detail}")


def timed(fn, repeat=3):
    times = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return min(times) * 1000  # ms, 取最优


def bench_matrix():
    torch = __import__("torch")
    n = 2048
    a_cpu = np.random.default_rng(0).standard_normal((n, n)).astype(np.float32)
    cpu_ms = timed(lambda: a_cpu @ a_cpu)
    a_gpu = torch.as_tensor(a_cpu, device="cuda")
    gpu_ms = timed(lambda: (a_gpu @ a_gpu).cpu())
    rec("D_matrix_fp32_2048", "PASS", f"CPU {cpu_ms:.1f}ms | GPU {gpu_ms:.1f}ms | speedup {cpu_ms/gpu_ms:.1f}x",
        {"cpu_ms": round(cpu_ms, 1), "gpu_ms": round(gpu_ms, 1), "speedup": round(cpu_ms / gpu_ms, 2)})
    # FP16 / BF16
    for dtype, name in ((torch.float16, "FP16"), (torch.bfloat16, "BF16")):
        try:
            g = torch.as_tensor(a_cpu, device="cuda", dtype=dtype)
            ms = timed(lambda: (g @ g).cpu())
            rec(f"F_{name}_matmul", "PASS", f"GPU {ms:.1f}ms (dtype={name})", {"gpu_ms": round(ms, 1)})
        except Exception as e:
            rec(f"F_{name}_matmul", "FAIL", str(e)[:200])
    # FP64 参考（预期很慢，如实记录）
    a64 = torch.as_tensor(a_cpu, device="cuda", dtype=torch.float64)
    try:
        ms = timed(lambda: (a64 @ a64).cpu(), repeat=1)
        rec("E_FP64_matmul_ref", "PASS", f"GPU FP64 {ms:.1f}ms（预期远慢于 FP32，高精度统计建议 CPU）")
    except Exception as e:
        rec("E_FP64_matmul_ref", "FAIL", str(e)[:200])


def bench_mc():
    torch = __import__("torch")
    n_paths, n_steps = 2_000_000, 128
    s0, mu, sigma, dt = 2400.0, 0.0, 0.2, 1 / (252 * 48)

    def mc_numpy():
        rng = np.random.default_rng(1)
        z = rng.standard_normal((n_steps, n_paths))
        lp = np.cumsum((mu - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * z, axis=0)
        return float(np.exp(np.vstack([np.zeros((1, n_paths)), lp])).mean())

    def mc_torch():
        # 4GB VRAM: 路径分 4 块逐块 cumsum/exp/mean（每条路径独立，块均值 = 全量均值，统计等价）
        g = torch.Generator(device="cuda").manual_seed(1)
        drift = (mu - 0.5 * sigma ** 2) * dt
        vol = sigma * np.sqrt(dt)
        acc = 0.0
        per = n_paths // 4
        for c in range(4):
            z = torch.randn((n_steps, per), device="cuda", generator=g)
            lp = torch.cumsum(drift + vol * z, dim=0)
            acc += float(torch.exp(torch.vstack([torch.zeros((1, per), device="cuda"), lp])).mean().item())
            del z, lp
        torch.cuda.synchronize()
        return acc / 4

    cpu_ms = timed(mc_numpy, repeat=2)
    gpu_ms = timed(mc_torch, repeat=2)
    rec("H_monte_carlo_2Mx128", "PASS",
        f"CPU {cpu_ms:.0f}ms | GPU {gpu_ms:.0f}ms | speedup {cpu_ms/gpu_ms:.1f}x",
        {"cpu_ms": round(cpu_ms), "gpu_ms": round(gpu_ms), "speedup": round(cpu_ms / gpu_ms, 2)})


def bench_bootstrap():
    torch = __import__("torch")
    rng = np.random.default_rng(7)
    x = rng.standard_normal(200_000).astype(np.float64)
    for n_iter in (2000, 10000):
        def boot_np():
            r = np.random.default_rng(2)
            idx = r.integers(0, len(x), (n_iter, len(x)))
            return float(x[idx].mean(axis=1).mean())

        def boot_torch():
            # 4GB VRAM: 按 400 迭代分块（单块峰值 ≈ 400×200k×8B×2 ≈ 1.3GB），均值统计等价
            g = torch.Generator(device="cuda").manual_seed(2)
            xt = torch.as_tensor(x, device="cuda")
            batch = 400
            acc = 0.0
            for b0 in range(0, n_iter, batch):
                idx = torch.randint(0, len(x), (batch, len(x)), device="cuda", generator=g)
                acc += float(xt[idx].mean(dim=1).mean().item())
                del idx
            torch.cuda.synchronize()
            return acc / (n_iter // batch)

        cpu_ms = timed(boot_np, repeat=2)
        gpu_ms = timed(boot_torch, repeat=2)
        rec(f"I_bootstrap_{n_iter}it", "PASS",
            f"CPU {cpu_ms:.0f}ms | GPU {gpu_ms:.0f}ms | speedup {cpu_ms/gpu_ms:.1f}x",
            {"cpu_ms": round(cpu_ms), "gpu_ms": round(gpu_ms), "speedup": round(cpu_ms / gpu_ms, 2)})


def bench_permutation():
    torch = __import__("torch")
    rng = np.random.default_rng(3)
    x = rng.standard_normal(100_000)
    n_iter = 10000

    def perm_np():
        r = np.random.default_rng(4)
        signs = r.choice([-1.0, 1.0], (n_iter, len(x)))
        return float((signs * x).mean(axis=1).std())

    def perm_torch():
        # 4GB VRAM: 按 1000 迭代分块，concat 后统一 std（统计等价）
        g = torch.Generator(device="cuda").manual_seed(4)
        xt = torch.as_tensor(x, device="cuda")
        batch = 1000
        means = []
        for b0 in range(0, n_iter, batch):
            signs = torch.where(torch.rand((batch, len(x)), device="cuda", generator=g) < 0.5,
                                torch.tensor(-1.0, device="cuda"), torch.tensor(1.0, device="cuda"))
            means.append((signs * xt).mean(dim=1))
            del signs
        m = torch.cat(means)
        out = float(m.std().item())
        torch.cuda.synchronize()
        return out

    cpu_ms = timed(perm_np, repeat=2)
    gpu_ms = timed(perm_torch, repeat=2)
    rec("I_permutation_10kit", "PASS",
        f"CPU {cpu_ms:.0f}ms | GPU {gpu_ms:.0f}ms | speedup {cpu_ms/gpu_ms:.1f}x",
        {"cpu_ms": round(cpu_ms), "gpu_ms": round(gpu_ms), "speedup": round(cpu_ms / gpu_ms, 2)})


def test_xgboost_gpu():
    try:
        import xgboost as xgb
        rng = np.random.default_rng(5)
        n = 50_000
        X = rng.standard_normal((n, 10))
        y = X[:, 0] + 0.5 * X[:, 1] ** 2 + rng.standard_normal(n) * 0.1
        d = xgb.DMatrix(X, y)
        t0 = time.perf_counter()
        m = xgb.train({"tree_method": "hist", "device": "cuda", "max_depth": 6, "seed": 5}, d, num_boost_round=50)
        ms = (time.perf_counter() - t0) * 1000
        rec("J_xgboost_gpu", "PASS", f"50 rounds {ms:.0f}ms (device=cuda)")
    except Exception as e:
        rec("J_xgboost_gpu", "FAIL", f"{type(e).__name__}: {str(e)[:300]}")


def test_lightgbm_gpu():
    try:
        import lightgbm as lgb
        rng = np.random.default_rng(6)
        n = 50_000
        X = rng.standard_normal((n, 10))
        y = X[:, 0] + rng.standard_normal(n) * 0.1
        ds = lgb.Dataset(X, y)
        t0 = time.perf_counter()
        lgb.train({"objective": "regression", "device": "cuda", "seed": 6, "verbose": -1}, ds, num_boost_round=50)
        ms = (time.perf_counter() - t0) * 1000
        rec("K_lightgbm_gpu", "PASS", f"50 rounds {ms:.0f}ms (device=cuda)")
    except Exception as e:
        rec("K_lightgbm_gpu", "FAIL", f"{type(e).__name__}: {str(e)[:300]} (Windows 需 OpenCL，预期走 CPU)")


def test_numba_cuda():
    try:
        from numba import cuda
        rec("L_numba_cuda", "SKIP", "Numba CUDA target 需要 CUDA Toolkit；按决策当前不安装 Toolkit → 跳过",
            {"reason": "requires CUDA Toolkit (not installed by design)"})
    except Exception as e:
        rec("L_numba_cuda", "SKIP", f"numba cuda 不可用: {str(e)[:150]} → 按决策跳过")


def test_cupy():
    try:
        import cupy as cp
        a = cp.arange(1_000_000, dtype=cp.float32)
        b = (a * 2 + 1).sum()
        rec("M_cupy_cuda12x", "PASS", f"cupy {cp.__version__} 计算正常 sum={b}")
    except Exception as e:
        rec("M_cupy_cuda12x", "SKIP", f"{type(e).__name__}: {str(e)[:200]} → 未安装/不可用，暂不引入")


def main() -> None:
    print("=" * 60)
    print("AIQuant GPU Benchmark — 真实测量")
    print(platform.platform(), "| python", platform.python_version())
    # A/B/C
    try:
        import torch
        rec("A_cuda_available", "PASS" if torch.cuda.is_available() else "FAIL",
            f"torch {torch.__version__} cuda.is_available={torch.cuda.is_available()} cuda={torch.version.cuda}")
        if torch.cuda.is_available():
            p = torch.cuda.get_device_properties(0)
            rec("B_device", "PASS", f"{p.name} | VRAM {p.total_memory/1e9:.2f}GB")
            rec("C_compute_capability", "PASS", f"CC {p.major}.{p.minor} | sm_{p.major}{p.minor}")
            for fn, label in ((bench_matrix, "D/E/F 矩阵"), (bench_mc, "H MonteCarlo"),
                              (bench_bootstrap, "I Bootstrap"), (bench_permutation, "I Permutation")):
                try:
                    fn()
                except Exception as e:
                    rec(label, "FAIL", f"{type(e).__name__}: {str(e)[:300]}")
            test_xgboost_gpu()
            test_lightgbm_gpu()
    except Exception as e:
        rec("A_cuda_available", "FAIL", f"{type(e).__name__}: {str(e)[:300]}")
    test_numba_cuda()
    test_cupy()

    # 汇总写报告
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# GPU Benchmark Report（真实结果）", "",
        f"- 时间：{time.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"- 机器：{platform.node()} | {platform.platform()}",
        "- GPU：NVIDIA RTX A2000 Laptop 4GB (CC 8.6) | Driver 591.55 (CUDA 13.1)",
        "", "## 结果", "", "| 测试 | 状态 | 详情 |", "|---|---|---|",
    ]
    for r in RESULTS:
        d = r["detail"].replace("|", "/")
        lines.append(f"| {r['test']} | {r['status']} | {d} |")
    lines += ["", "## A2000 4GB 能力结论", "",
              "- **能**：Monte Carlo/Bootstrap/Permutation 批量并行（实测加速见上表）、中小规模矩阵、FP16/BF16、小模型 DL/ML",
              "- **不能/不建议**：>4GB 显存占用的大模型训练、FP64 高精度统计（走 CPU）、依赖 CUDA Toolkit 的工具链（Numba CUDA/CuPy 原生编译）",
              "- XGBoost/LightGBM GPU 实测见上表（失败即如实记录，不强行装 Toolkit）"]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n报告已写入 {REPORT}")
    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_skip = sum(1 for r in RESULTS if r["status"] == "SKIP")
    print(f"PASS={n_pass} SKIP={n_skip} FAIL={sum(1 for r in RESULTS if r['status']=='FAIL')}")
    sys.exit(0 if not any(r["status"] == "FAIL" for r in RESULTS if r["test"].startswith(("A", "B", "C"))) else 1)


if __name__ == "__main__":
    main()
