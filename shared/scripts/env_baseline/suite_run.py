# -*- coding: utf-8 -*-
"""suite_run.py - runs every env_baseline module with the .venv interpreter and
merges per-module JSON reports into one machine-readable result file:
  reports/env_smoke_results.json  +  reports/env_smoke_summary.txt"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = ROOT / ".venv" / "Scripts" / "python.exe"
MODULES = ["env_info", "gpu_bench", "stats_smoke", "ml_smoke", "ts_leak",
           "backtest_smoke", "tick_smoke", "duka_smoke", "mt5_smoke", "git_smoke"]
OUT = ROOT / "reports" / "env_smoke_results.json"
SUM = ROOT / "reports" / "env_smoke_summary.txt"


def main() -> None:
    results = {"suite": "env_baseline", "run_utc": datetime.now(timezone.utc).isoformat(),
               "python": str(PY), "modules": {}, "summary": {}}
    lines = []
    counts = {"PASS": 0, "WARN": 0, "FAIL": 0, "SKIP": 0}
    for mod in MODULES:
        t0 = time.perf_counter()
        try:
            r = subprocess.run([str(PY), str(Path(__file__).parent / f"{mod}.py")],
                               capture_output=True, text=True, timeout=900, cwd=ROOT)
            dt = round(time.perf_counter() - t0, 1)
            # load its json report if written (module json basename strips the _smoke suffix)
            stem = "env_baseline_info" if mod == "env_info" else f"env_smoke_{mod.replace('_smoke', '')}"
            rep_path = ROOT / "reports" / f"{stem}.json"
            detail = {}
            if rep_path.exists():
                detail = json.loads(rep_path.read_text(encoding="utf-8"))
            status = detail.get("status", "FAIL")
            n_checks = detail.get("n_checks", 0)
            results["modules"][mod] = {"status": status, "n_checks": n_checks, "seconds": dt,
                                       "stderr_tail": (r.stderr or "")[-400:]}
            if status in counts:
                counts[status] += 1
            lines.append(f"{mod:18s} {status:5s} {n_checks:3d} checks  {dt:6.1f}s")
            if r.returncode != 0 and status != "FAIL":
                results["modules"][mod]["note"] = f"exit={r.returncode}"
        except Exception as e:
            counts["FAIL"] += 1
            results["modules"][mod] = {"status": "FAIL", "error": str(e)}
            lines.append(f"{mod:18s} FAIL  runner error: {e}")
    results["summary"] = counts
    results["total_checks_flagged"] = {k: v for k, v in counts.items()}
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    SUM.write_text("\n".join(lines) + f"\nTOTALS {counts}\n", encoding="utf-8")
    print("\n".join(lines))
    print("TOTALS", counts)
    print("->", OUT)


if __name__ == "__main__":
    main()
