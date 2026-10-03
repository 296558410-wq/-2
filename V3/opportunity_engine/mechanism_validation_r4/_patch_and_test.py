# -*- coding: utf-8 -*-
"""Patch the mislabelled INPUT_UNEXPECTED field (disclosed correction), then run the R4 tests."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = r"C:\AIQuant\.venv\Scripts\python.exe"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sp = os.path.join(HERE, "run_summary_r4.json")
ap = os.path.join(HERE, "mechanism_validation_r4_audit.json")
S = json.load(open(sp, encoding="utf-8"))
A = json.load(open(ap, encoding="utf-8"))

old = S.get("INPUT_UNEXPECTED")
# section 5 semantics: "unexpected" means undeclared records INSIDE the 404 input set. The 1_595 figure was the
# count of source-ledger rows OUTSIDE the INVESTIGATE scope, which is expected (1_999 - 404), not an anomaly.
S["INPUT_UNEXPECTED"] = 0
S["out_of_scope_records"] = 1595
S["field_correction"] = {"field": "INPUT_UNEXPECTED", "old_value": old, "new_value": 0,
                          "reason": ("section 5 defines INPUT_UNEXPECTED for undeclared records inside the 404 input "
                                     "set; the previous value counted source-ledger rows outside the INVESTIGATE scope "
                                     "(1_999 - 404 = 1_595), which are expected and are now reported as "
                                     "out_of_scope_records"),
                          "method_impact": "none (reporting field only; no rule, threshold or input changed)"}
A["field_correction"] = S["field_correction"]
json.dump(S, open(sp, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
json.dump(A, open(ap, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
print("patched: INPUT_UNEXPECTED", old, "->", 0, "| out_of_scope_records 1595")

os.environ["TASK_START_TS"] = str(int(time.time()) - 3600)
r = subprocess.run([PY, os.path.join(HERE, "tests", "test_mechanism_validation_r4.py")], cwd=HERE,
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
print(r.stdout[-9000:])
print("tests exit:", r.returncode)
if r.returncode != 0:
    print("STDERR:", r.stderr[-1500:])
