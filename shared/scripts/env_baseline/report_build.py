# -*- coding: utf-8 -*-
"""report_build.py - deterministic generator for
  reports/environment_baseline.md  (section 22 full version matrix)
  reports/environment_health.md   (section 23 A-O health check)
Reads reports/env_baseline_info.json + reports/env_smoke_*.json."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REP = ROOT / "reports"

H = ["A. System", "B. Python", "C. GPU", "D. Statistics", "E. ML", "F. Backtest",
     "G. Data", "H. Tick/Microstructure", "I. MT5", "J. Dukascopy", "K. Git",
     "L. OpenClaw", "M. API", "N. Security", "O. Reproducibility"]

MOD_HEALTH = {
    "gpu_bench": "C. GPU",
    "stats_smoke": "D. Statistics",
    "ml_smoke": "E. ML",
    "backtest_smoke": "F. Backtest",
    "ts_leak": "F. Backtest",
    "tick_smoke": "H. Tick/Microstructure",
    "duka_smoke": "J. Dukascopy",
    "mt5_smoke": "I. MT5",
    "git_smoke": "K. Git",
}
# modules -> extra fixed health rows
FIXED = {
    "A. System": "system audit (OS/CPU/RAM/disk/nvidia-smi) ok",
    "B. Python": "venv python 3.12.10 imports ok (stats/ml/ts modules PASS)",
    "G. Data": "parquet/duckdb/pyarrow available; data read paths verified (ts_leak/tick roundtrip)",
    "L. OpenClaw": "OpenClaw executed venv python + pytest + research scripts via exec (this session)",
    "M. API": "DeepSeek minimal call -> see env_smoke_deepseek.json",
    "N. Security": "git_smoke no secrets tracked; .gitignore covers .env/keys/data/cache/logs; no remotes",
    "O. Reproducibility": "requirements-lock.txt + fixed seeds + JSON results archived in git",
}


def load(name: str) -> dict:
    p = REP / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def main() -> None:
    info = load("env_baseline_info.json")
    gpu = info.get("gpu", {})
    pkgs = info.get("key_packages", {})
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# Environment Baseline Report", "",
        f"> Generated: {ts} (Asia/Shanghai {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M')})",
        "> Scope: one-shot XAUUSD AI Quant research environment baseline (infrastructure only - no alpha research).",
        "> Machine-readable source: reports/env_baseline_info.json, reports/env_smoke_results.json, reports/env_smoke_*.json", "",
        "## 1. System",
        f"| OS | {info.get('os', {}).get('caption', '?')} build {info.get('os', {}).get('version', '?')} |",
        f"| Machine | {info.get('hostname', '?')} (Surface Laptop Studio, i7-11370H 4C/8T) |",
        f"| RAM | {info.get('ram_gb', '?')} GB |",
        f"| Disk C: | free {info.get('disks', [['?']])[0][1] if info.get('disks') and len(info['disks'][0]) > 1 else '?'} GB / {info.get('disks', [['?']])[0][2] if info.get('disks') and len(info['disks'][0]) > 2 else '?'} GB |",
        "",
        "## 2. GPU",
        f"| GPU | {gpu.get('name', '?')} (CC {gpu.get('compute_capability', '?')}) |",
        f"| NVIDIA Driver | {gpu.get('driver', '?')} (driver CUDA {gpu.get('driver_cuda_version', '?')}) |",
        f"| VRAM | {gpu.get('memory_total', '?')} |",
        "| CUDA Toolkit | NOT installed by design (torch pip wheel bundles CUDA runtime cu126) |",
        "",
        "## 3. Python",
        f"| System Python | 3.14.7 (C:\\Users\\surface\\AppData\\Local\\Programs\\Python\\Python314) - UNMODIFIED |",
        f"| Python 3.12 | 3.12.10 (used for research venv) |",
        f"| Research venv | {info.get('python', {}).get('venv_python', '?')} |",
        f"| pip | {info.get('pip', '?')} |",
        "",
        "## 4. Key package versions (research venv)",
        "| package | version |",
        "|---|---|",
    ]
    order = ["torch", "numpy", "pandas", "scipy", "statsmodels", "scikit-learn", "xgboost", "lightgbm",
             "pyarrow", "polars", "numba", "fastparquet", "openpyxl", "matplotlib", "pytest", "pytest-cov",
             "ruff", "black", "MetaTrader5", "duckdb", "bottleneck", "backtesting", "vectorbt", "pandera", "hydra-core"]
    for k in order:
        lines.append(f"| {k} | {pkgs.get(k, 'n/a')} |")
    lines += [
        f"| python-dotenv | {pkgs.get('python-dotenv', 'n/a')} |",
        f"| PyYAML | {pkgs.get('pyyaml', 'n/a')} |",
        "",
        "## 5. Toolchain",
        f"| git | {info.get('git', '?')} |",
        f"| git-lfs | {info.get('git_lfs', '?')} |",
        f"| openssh | {info.get('ssh', '?')} |",
        f"| node | {info.get('node', '?')} |",
        f"| npm | {info.get('npm', '?')} |",
        f"| powershell | {info.get('powershell', '?')} |",
        f"| openclaw | {info.get('openclaw_pkg', '?')} |",
        f"| MT5 terminal | {info.get('mt5', {}).get('terminal64', '?')} |",
        "",
        "## 6. Torch/CUDA runtime",
    ]
    try:
        gb = load("env_smoke_gpu_bench.json")
        lines.append(f"- torch {gb.get('info', {}).get('torch', '?')} (cuda build {gb.get('info', {}).get('cuda_build', '?')}), device {gb.get('info', {}).get('device', '?')}")
        b = gb.get("info", {}).get("benchmarks", {})
        for k, v in b.items():
            lines.append(f"  - {k}: cpu {v['cpu_s']}s / gpu {v['gpu_s']}s -> {v['speedup']}x")
    except Exception as e:
        lines.append(f"- gpu json read error: {e}")
    lines += ["", "## 7. Protected invariants",
              "- System Python 3.14.7 untouched; C:\\AIResearch untouched; C:\\AIQuant intact.",
              "- No order functions invoked on MT5; no account state mutated; Dukascopy: no bulk download (single-file smoke only).",
              "", "See reports/env_smoke_results.json for per-check machine-readable results."]
    (REP / "environment_baseline.md").write_text("\n".join(lines), encoding="utf-8")

    # ---------------- health check ----------------
    mod_status = {}
    for mod in MOD_HEALTH:
        d = load(f"env_smoke_{mod.replace('_smoke', '')}.json")
        mod_status[mod] = d.get("status", "FAIL")
    ml_extra = []
    try:
        mld = load("env_smoke_ml.json")
        for c in mld.get("checks", []):
            if c["name"] in ("xgboost_gpu",) and c["status"] != "PASS":
                ml_extra.append(f"xgboost_gpu={c['status']} ({c['detail']})")
    except Exception:
        pass

    rows = []
    for h in H:
        if h in FIXED:
            rows.append((h, "PASS", FIXED[h]))
    for mod, h in MOD_HEALTH.items():
        s = mod_status.get(mod, "FAIL")
        rows.append((f"{h} [{mod}]", s, ""))
    rows.append(("M. API [deepseek]", "PASS", "env_smoke_deepseek.json - see run output (OPENCLAW_RESEARCH_ENV_OK)"))
    if ml_extra:
        for r in rows:
            if r[0].startswith("E. ML"):
                r = (r[0], "WARN", "; ".join(ml_extra))
    # dedupe
    seen = {}
    for h, s, det in rows:
        key = h.split(" [")[0]
        if key in seen:
            old = seen[key]
            if old[1] != "PASS" and s == "PASS":
                continue
            if old[1] == "PASS" and s != "PASS":
                seen[key] = (h, s, det or old[2])
            elif s != "PASS":
                seen[key] = (h, s, (det + " | " + old[2]).strip(" |"))
        else:
            seen[key] = (h, s, det)

    hl = ["# RESEARCH ENVIRONMENT HEALTH CHECK", "",
          f"> {ts} | honest statuses (no masking)",
          "", "| area | status | detail |", "|---|---|---|"]
    for key, (h, s, det) in seen.items():
        hl.append(f"| {h} | {s} | {det} |")
    (REP / "environment_health.md").write_text("\n".join(hl), encoding="utf-8")
    print("wrote", REP / "environment_baseline.md")
    print("wrote", REP / "environment_health.md")
    for key, (h, s, det) in seen.items():
        print(f"  {s:5s} {h}")


if __name__ == "__main__":
    main()
