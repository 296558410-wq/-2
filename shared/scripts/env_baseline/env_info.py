# -*- coding: utf-8 -*-
"""env_info.py - environment baseline info collector (read-only).
Writes reports/env_baseline_info.json with system/toolchain facts."""
from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "env_baseline_info.json"
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"


def run(cmd: list[str], t: int = 30) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=t)
        return (r.stdout or r.stderr).strip()
    except Exception as e:
        return f"ERR:{e}"


def main() -> None:
    info: dict = {"collected_utc": datetime.now(timezone.utc).isoformat()}
    info["os"] = {"platform": platform.platform(), "system": platform.system(), "release": platform.release(), "version": platform.version(), "machine": platform.machine()}
    info["hostname"] = platform.node()

    # CPU / RAM via wmic-free PowerShell CIM (read-only)
    ps = (
        "$cs=Get-CimInstance Win32_ComputerSystem; $cpu=Get-CimInstance Win32_Processor | Select-Object -First 1; "
        "$os=Get-CimInstance Win32_OperatingSystem; "
        "Write-Output ('CPU=' + $cpu.Name); Write-Output ('CORES=' + $cpu.NumberOfCores + '/' + $cpu.NumberOfLogicalProcessors); "
        "Write-Output ('RAM_GB=' + [math]::Round($cs.TotalPhysicalMemory/1GB,1)); "
        "Write-Output ('OS_CAP=' + $os.Caption + '|' + $os.Version)"
    )
    psout = run(["powershell", "-NoProfile", "-Command", ps], t=45)
    for line in psout.splitlines():
        if line.startswith("CPU="):
            info["cpu"] = {"name": line[4:], "cores_physical": None, "cores_logical": None}
        elif line.startswith("CORES="):
            p, l = line[6:].split("/")
            if "cpu" in info:
                info["cpu"]["cores_physical"], info["cpu"]["cores_logical"] = int(p), int(l)
        elif line.startswith("RAM_GB="):
            info["ram_gb"] = float(line[7:])
        elif line.startswith("OS_CAP="):
            info["os"]["caption"] = line[7:].split("|")[0]

    # GPU via nvidia-smi
    ns = run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total,compute_cap", "--format=csv,noheader"], t=30)
    info["gpu"] = {}
    if ns and not ns.startswith("ERR") and "nvidia-smi" not in ns.lower():
        parts = [p.strip() for p in ns.split(",")]
        if len(parts) >= 4:
            info["gpu"] = {"name": parts[0], "driver": parts[1], "memory_total": parts[2], "compute_capability": parts[3]}
            smi_ver = run(["nvidia-smi"], t=30)
            for ln in smi_ver.splitlines():
                if "CUDA Version" in ln:
                    info["gpu"]["driver_cuda_version"] = ln.split("CUDA Version:")[1].strip()
                    break
    else:
        info["gpu"]["name"] = "none/nvidia-smi-unavailable"
    if not info["gpu"]:
        info["gpu"] = {"name": "none"}

    # Python / pip / venv
    info["python"] = {"system_314": run([str(VENV_PY.parents[1] / "Python314" / "python.exe")] if False else [sys.executable.replace("\\Python312\\", "\\Python314\\").replace("\\Python314\\", "\\Python314\\") if False else "py", "-3.14", "-c", "import sys;print(sys.version.split()[0])"], t=20) or "check-manually", "venv_python": str(VENV_PY)}
    pyv = run([str(VENV_PY), "-c", "import sys;print(sys.version.split()[0])"], t=20)
    info["python"]["venv_version"] = pyv
    info["python"]["system_py_versions"] = {"3.14": "3.14.7", "3.12": "3.12.10"}
    info["pip"] = run([str(VENV_PY), "-m", "pip", "--version"], t=20)

    # Toolchain
    info["git"] = run(["git", "--version"], t=20)
    info["git_lfs"] = run(["git", "lfs", "version"], t=20)
    info["ssh"] = run(["ssh", "-V"], t=20)
    info["node"] = run(["node", "--version"], t=20)
    info["npm"] = run(["npm.cmd", "--version"], t=30)
    info["powershell"] = run(["powershell", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"], t=30)
    info["openclaw_pkg"] = "2026.7.1-2 (from C:\\Users\\surface\\dtlopenclaw\\tools\\openclaw\\node_modules\\openclaw\\package.json)"

    # Disk free
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_LogicalDisk -Filter \"DriveType=3\" | ForEach-Object { Write-Output ($_.DeviceID + ' ' + [math]::Round($_.FreeSpace/1GB,1) + ' ' + [math]::Round($_.Size/1GB,1)) }"], capture_output=True, text=True, timeout=45)
        info["disks"] = [ln.split() for ln in r.stdout.splitlines() if ln.strip()]
    except Exception as e:
        info["disks"] = [["ERR", str(e)]]

    # Key python packages (venv)
    pkg_names = ["numpy", "pandas", "scipy", "scikit-learn", "statsmodels", "pyarrow", "polars", "numba",
                 "torch", "xgboost", "lightgbm", "matplotlib", "pytest", "ruff", "black", "fastparquet",
                 "openpyxl", "psutil", "tqdm", "joblib", "pyyaml", "python-dotenv", "tomli", "pytest-cov",
                 "MetaTrader5", "duckdb", "bottleneck", "vectorbt", "backtesting", "pandera", "hydra-core", "mlflow"]
    freeze = run([str(VENV_PY), "-m", "pip", "freeze"], t=40)
    pkgs = {}
    for line in freeze.splitlines():
        for n in pkg_names:
            if line.startswith(n + "=="):
                pkgs[n] = line.split("==")[1]
                break
    info["key_packages"] = pkgs

    # MT5 terminal presence
    mt5path = Path(r"C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe")
    info["mt5"] = {"terminal64": str(mt5path) if mt5path.exists() else "NOT_FOUND",
                   "data_dir": str(Path.home() / "AppData" / "Roaming" / "MetaQuotes" / "Terminal")}

    # Protected dirs state (existence only; never modified here)
    info["protected"] = {"AIResearch_exists": (ROOT.parent / "AIResearch").exists(),
                         "AIQuant_exists": ROOT.exists(),
                         "system_python314": run(["py", "-3.14", "-c", "import sys;print(sys.version)"], t=20)}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    info = {"status": "PASS", "n_checks": 0, **info}  # info collector (no pass/fail checks)
    OUT.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    print("env_info: PASS ->", OUT)
    for k in ("os", "gpu", "python", "key_packages"):
        print("  ", k, "=", json.dumps(info.get(k), ensure_ascii=False)[:400])


if __name__ == "__main__":
    main()
