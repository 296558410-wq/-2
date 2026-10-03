"""snapshot_env.py — 一键输出环境快照 JSON（可复现五元组之"硬件"部分）。

用法: python tools/snapshot_env.py [--json 输出路径]
输出包含: python/pip/关键包版本/git commit/GPU 属性/驱动/CUDA/torch。
"""
from __future__ import annotations

import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

IMPORTANT = [
    "numpy", "pandas", "scipy", "numba", "pyarrow", "polars", "duckdb",
    "statsmodels", "arch", "sklearn", "xgboost", "lightgbm",
    "torch", "pandera", "mlflow", "hydra", "vectorbt", "backtesting", "matplotlib",
]


def pkg_versions() -> dict:
    out = {}
    for name in IMPORTANT:
        try:
            mod = __import__(name)
            out[name] = getattr(mod, "__version__", "?")
        except Exception as e:
            out[name] = f"NOT_IMPORTABLE:{type(e).__name__}"
    return out


def git_head() -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else "(no commit)"
    except Exception:
        return None


def gpu_info() -> dict:
    info = {"driver": None, "cuda_max": None}
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total",
                            "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            parts = r.stdout.strip().split(",")
            info["name"] = parts[0].strip()
            info["driver"] = parts[1].strip()
            info["vram_mb"] = parts[2].strip()
        r2 = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=15)
        for line in r2.stdout.splitlines():
            if "CUDA Version" in line:
                info["cuda_max"] = line.split("CUDA Version")[-1].strip()
                break
    except Exception:
        pass
    try:
        import torch
        info["torch"] = torch.__version__
        info["torch_cuda"] = torch.version.cuda
        info["cuda_available"] = bool(torch.cuda.is_available())
        if torch.cuda.is_available():
            p = torch.cuda.get_device_properties(0)
            info["cc"] = f"{p.major}.{p.minor}"
    except Exception as e:
        info["torch_error"] = str(e)[:120]
    return info


def main() -> None:
    snap = {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "host": platform.node(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "python_exe": sys.executable,
        "git_head": git_head(),
        "packages": pkg_versions(),
        "gpu": gpu_info(),
    }
    text = json.dumps(snap, indent=2, ensure_ascii=False)
    print(text)
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(text, encoding="utf-8")
        print(f"\n已写入 {sys.argv[1]}")


if __name__ == "__main__":
    main()
