# -*- coding: utf-8 -*-
"""Fix nested quotes in _finalize_r3.py, compile, then run it."""
from __future__ import annotations

import py_compile
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = r"C:\AIQuant\research\v3_opportunity_engine\mechanism_validation_r3\_finalize_r3.py"
t = open(P, encoding="utf-8").read()
pairs = [('为什么这个正控是"公平"的', "为什么这个正控是「公平」的"),
         ('X("## 4. 为什么这个正控是「公平」的")', 'X("## 4. 为什么这个正控是「公平」的")')]
for a, b in pairs:
    n = t.count(a)
    if n:
        print("fix", n, "x :", a[:36])
    t = t.replace(a, b)
open(P, "w", encoding="utf-8", newline="\n").write(t)
try:
    py_compile.compile(P, doraise=True)
    print("COMPILE OK")
except Exception as e:  # noqa: BLE001
    print("COMPILE FAIL:", str(e)[:300])
    raise SystemExit(1)
r = subprocess.run([r"C:\AIQuant\.venv\Scripts\python.exe", P], capture_output=True, text=True,
                    encoding="utf-8", errors="replace")
print((r.stdout or "")[-2500:])
print("STDERR:", (r.stderr or "")[-700:])
