# -*- coding: utf-8 -*-
"""gpu_bench.py - real GPU compute validation + CPU/GPU mini-benchmarks.
Sections: device, fp32 correctness, fp16, bf16, memory alloc, H2D/D2H,
matmul/MC/bootstrap/permutation CPU-vs-GPU timings. Writes JSON."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "env_smoke_gpu_bench.json"


def main() -> None:
    checks: list[dict] = []
    info: dict = {}

    def add(name: str, ok: bool, detail: str = "", status: str | None = None):
        checks.append({"name": name, "status": status or ("PASS" if ok else "FAIL"), "detail": detail})

    import torch
    info["torch"] = torch.__version__
    info["cuda_build"] = torch.version.cuda
    avail = torch.cuda.is_available()
    add("cuda_available", avail)
    if not avail:
        OUT.write_text(json.dumps({"status": "FAIL", "checks": checks, "info": info}, indent=2), encoding="utf-8")
        print("gpu_bench: FAIL (no cuda)"); return

    dev = torch.device("cuda:0")
    props = torch.cuda.get_device_properties(0)
    info["device"] = props.name
    info["cc"] = f"{props.major}.{props.minor}"
    info["memory_total_mb"] = round(props.total_memory / 1e6, 1)
    info["driver"] = torch.cuda.get_device_name(0)
    add("device_props", props.major >= 7, f"{props.name} CC {props.major}.{props.minor} mem {props.total_memory/1e9:.2f}GB")

    rng = np.random.default_rng(42)

    # --- FP32 correctness: CPU numpy vs GPU ---
    a = rng.standard_normal((1024, 1024)).astype(np.float32)
    cpu_r = a @ a
    g = torch.as_tensor(a, device=dev)
    gpu_r = (g @ g).cpu().numpy()
    ok = np.allclose(cpu_r, gpu_r, rtol=1e-3, atol=1e-2)
    add("fp32_matmul_correctness", ok, f"max_abs_diff={np.abs(cpu_r - gpu_r).max():.4f}")

    # --- FP16 / BF16 on GPU ---
    for dt, name, tol in ((torch.float16, "fp16", 0.03), (torch.bfloat16, "bf16", 0.05)):
        try:
            t = torch.randn(1024, 1024, device=dev, dtype=dt)
            r16 = (t @ t).float()
            ref = (t.float() @ t.float())
            rel = (r16 - ref).abs().max().item() / (ref.abs().max().item() + 1e-8)
            add(f"{name}_matmul", bool(np.isfinite(rel)) and rel < tol, f"rel_max={rel:.5f} (tol {tol})")
        except Exception as e:
            add(f"{name}_matmul", False, f"{type(e).__name__}: {e}")

    # --- Memory alloc / free ---
    torch.cuda.reset_peak_memory_stats()
    try:
        big = torch.empty(256 * 1024 * 1024 // 4, dtype=torch.float32, device=dev)  # 256 MiB
        big.fill_(1.0)
        used = torch.cuda.memory_allocated() / 1e6
        del big
        torch.cuda.empty_cache()
        add("memory_alloc_free", used > 200, f"peak={torch.cuda.max_memory_allocated()/1e6:.0f}MB, alloc_ok={used:.0f}MB")
    except Exception as e:
        add("memory_alloc_free", False, str(e))

    # --- H2D / D2H ---
    x = rng.standard_normal(8_000_000).astype(np.float32)
    try:
        t0 = time.perf_counter(); t = torch.as_tensor(x, device=dev); torch.cuda.synchronize(); t_h2d = time.perf_counter() - t0
        y = (t * 2.0); torch.cuda.synchronize()
        t0 = time.perf_counter(); back = y.cpu().numpy(); t_d2h = time.perf_counter() - t0
        ok = np.allclose(back, x * 2.0, rtol=1e-5)
        add("h2d_d2h", ok, f"h2d={t_h2d*1000:.1f}ms d2h={t_d2h*1000:.1f}ms (32MB)")

        # --- Benchmarks CPU vs GPU ---
        def bench(name: str, cpu_fn, gpu_fn, check=None):
            torch.cuda.synchronize()
            t0 = time.perf_counter(); cpu_v = cpu_fn(); t_cpu = time.perf_counter() - t0
            t0 = time.perf_counter(); gpu_v = gpu_fn(); torch.cuda.synchronize(); t_gpu = time.perf_counter() - t0
            ok = True
            if check is not None:
                ok = check(cpu_v, gpu_v)
            speedup = t_cpu / t_gpu if t_gpu > 0 else float("inf")
            info.setdefault("benchmarks", {})[name] = {"cpu_s": round(t_cpu, 4), "gpu_s": round(t_gpu, 4), "speedup": round(speedup, 2), "gpu_peak_mb": round(torch.cuda.max_memory_allocated() / 1e6, 1)}
            add(f"bench_{name}", ok, f"cpu={t_cpu:.3f}s gpu={t_gpu:.3f}s speedup={speedup:.1f}x")

        N = 4096
        am = rng.standard_normal((N, N)).astype(np.float32)
        def cpu_mm(): return am @ am
        def gpu_mm():
            g2 = torch.as_tensor(am, device=dev)
            r = g2 @ g2
            return r
        bench("matmul4096", cpu_mm, gpu_mm, check=lambda c, g: bool(torch.isfinite(g).all().item()))

        # Monte Carlo pi
        n_draws = 30_000_000
        def cpu_mc():
            x2 = rng.random(n_draws); y2 = rng.random(n_draws)
            return 4.0 * np.mean(x2 * x2 + y2 * y2 < 1.0)
        def gpu_mc():
            x2 = torch.rand(n_draws, device=dev); y2 = torch.rand(n_draws, device=dev)
            return 4.0 * (x2 * x2 + y2 * y2 < 1.0).float().mean().item()
        bench("montecarlo_pi", cpu_mc, gpu_mc, check=lambda c, g: abs(c - g) < 1e-3)

        # Bootstrap (mean, 400 resamples of 100k)
        xb = rng.standard_normal(100_000).astype(np.float32)
        def cpu_bs():
            idx = rng.integers(0, 100_000, size=(400, 100_000))
            return float(xb[idx].mean(axis=1).std())
        xbt = torch.as_tensor(xb, device=dev)
        def gpu_bs():
            idx = torch.randint(0, 100_000, (400, 100_000), device=dev)
            return float(xbt[idx].float().mean(dim=1).std().item())
        bench("bootstrap_400x100k", cpu_bs, gpu_bs, check=lambda c, g: abs(c - g) < 5e-3)

        # Permutation test (mean diff, 400 shuffles of 2x50k)
        pa = rng.standard_normal(50_000).astype(np.float32); pb = rng.standard_normal(50_000).astype(np.float32) + 0.01
        merged = np.concatenate([pa, pb])
        def cpu_perm():
            obs = float(pa.mean() - pb.mean())
            cnt = 0
            for _ in range(400):
                m2 = rng.permutation(merged)
                cnt += abs(m2[:50000].mean() - m2[50000:].mean()) >= abs(obs)
            return cnt / 400.0
        mt = torch.as_tensor(merged, device=dev)
        def gpu_perm():
            obs = float(torch.as_tensor(pa, device=dev).mean() - torch.as_tensor(pb, device=dev).mean())
            idx = torch.argsort(torch.rand(400, 100_000, device=dev), dim=1)
            s = mt[idx].float()
            left = s[:, :50000].mean(dim=1); right = s[:, 50000:].mean(dim=1)
            return float((left - right).abs().ge(abs(obs)).float().mean().item())
        bench("permutation_400x100k", cpu_perm, gpu_perm, check=lambda c, g: abs(c - g) < 0.05)

        status = "PASS" if all(c["status"] == "PASS" for c in checks) else ("WARN" if any(c["status"] == "FAIL" for c in checks) is False else "FAIL")
        # recompute: any FAIL -> FAIL else PASS
        status = "FAIL" if any(c["status"] == "FAIL" for c in checks) else "PASS"
        OUT.write_text(json.dumps({"status": status, "checks": checks, "info": info, "n_checks": len(checks)}, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"gpu_bench: {status} ({len(checks)} checks)")
        for c in checks:
            print(f"  [{c['status']}] {c['name']} - {c['detail']}")
    except Exception as e:
        add("bench_suite", False, f"{type(e).__name__}: {e}")
        OUT.write_text(json.dumps({"status": "FAIL", "checks": checks, "info": info}, indent=2), encoding="utf-8")
        print("gpu_bench: FAIL -", e)


if __name__ == "__main__":
    main()
