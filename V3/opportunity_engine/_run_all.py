# -*- coding: utf-8 -*-
"""Launcher: compile-check, run the orchestrator, then run the 11 mandatory tests."""
from __future__ import annotations

import os
import py_compile
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = r"C:\AIQuant\.venv\Scripts\python.exe"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

for f in ("engine.py", "run_r1.py", os.path.join("tests", "test_engine.py")):
    p = os.path.join(HERE, f)
    try:
        py_compile.compile(p, doraise=True)
        print("COMPILE OK:", f)
    except Exception as e:  # noqa: BLE001
        print("COMPILE FAIL:", f, str(e)[:300])
        sys.exit(1)

os.environ["TASK_START_TS"] = str(int(time.time()) - 1800)

print("\n=== orchestrator ===", flush=True)
r = subprocess.run([PY, os.path.join(HERE, "run_r1.py")], cwd=HERE, capture_output=True, text=True,
                    encoding="utf-8", errors="replace")
print(r.stdout[-4000:])
if r.returncode != 0:
    print("STDERR:", r.stderr[-1500:])
    sys.exit(1)

print("\n=== tests ===", flush=True)
t = subprocess.run([PY, os.path.join(HERE, "tests", "test_engine.py"),
                     os.path.join(HERE, "state_engine", "state_1h.parquet"),
                     os.path.join(HERE, "ledger", "v3_opportunity_ledger_1h.jsonl"),
                     r"C:\AIQuant\research\hermes\trader_v1",
                     r"C:\AIQuant\research\hermes\trader_v2"],
                    cwd=HERE, capture_output=True, text=True, encoding="utf-8", errors="replace")
print(t.stdout[-5000:])
print("tests exit:", t.returncode)
if t.returncode != 0:
    print("STDERR:", t.stderr[-1200:])
