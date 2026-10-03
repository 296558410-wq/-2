# -*- coding: utf-8 -*-
"""Launcher: compile-check, run the Quality Gate orchestrator, then the 12 mandatory tests."""
from __future__ import annotations

import os
import py_compile
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = r"C:\AIQuant\.venv\Scripts\python.exe"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

for f in ("quality_filter.py", "run_quality_r1.py", os.path.join("tests", "test_quality.py")):
    try:
        py_compile.compile(os.path.join(HERE, f), doraise=True)
        print("COMPILE OK:", f)
    except Exception as e:  # noqa: BLE001
        print("COMPILE FAIL:", f, str(e)[:400])
        sys.exit(1)

os.environ["TASK_START_TS"] = str(int(time.time()) - 3600)

print("\n=== quality gate orchestrator ===", flush=True)
r = subprocess.run([PY, os.path.join(HERE, "run_quality_r1.py")], cwd=HERE, capture_output=True, text=True,
                    encoding="utf-8", errors="replace")
print(r.stdout[-5000:])
if r.returncode != 0:
    print("STDERR:", r.stderr[-2500:])
    sys.exit(1)

print("\n=== 12 mandatory tests ===", flush=True)
t = subprocess.run([PY, os.path.join(HERE, "tests", "test_quality.py")], cwd=HERE, capture_output=True, text=True,
                    encoding="utf-8", errors="replace")
print(t.stdout[-6000:])
print("tests exit:", t.returncode)
if t.returncode != 0:
    print("STDERR:", t.stderr[-1500:])
