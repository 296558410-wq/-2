# -*- coding: utf-8 -*-
"""R31.2 post-completion verification (read-only).
Confirms: no interrupted writers, freeze intact, artifacts complete, automation still disabled."""
from __future__ import annotations

import json
import hashlib
import os
import re
import subprocess
import sys

A = r"C:\AIQuant"
V1 = os.path.join(A, r"research\hermes\trader_v1")
R31D = os.path.join(A, r"research\v3_opportunity_engine\v1_r31_2_forensic")
NODE = r"C:\Users\surface\dtlopenclaw\tools\node-v24.21.0-win-x64\node.exe"
CLI = r"C:\Users\surface\dtlopenclaw\tools\openclaw\node_modules\openclaw\dist\index.js"
AID = "cd47547e-ae38-4b36-a585-8b041ee826bb"


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    print("== processes ==")
    praw = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                            "Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -match 'trader_v1|engine\\.py|state_package|_r31_|_r30_'} | "
                            "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    lines = [x for x in (praw.stdout or "").splitlines() if x.strip() and x.strip() != "null"]
    print("residual_task_processes =", len(lines) if lines != [""] else 0)
    if lines:
        print(str(lines)[:400])

    print("== freeze hashes ==")
    exp = {"engine": (os.path.join(V1, "engine.py"), "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d"),
            "ledger": (os.path.join(V1, "run_state", "plan_ledger.jsonl"), "0b90493cae0cdf7b73056bc72b1e5752f35c3eb20f9306c098d26f4bec819261"),
            "stats": (os.path.join(V1, "run_state", "statistics.json"), "ca42f624fde50df375dc877750e121e8d2d313986ea6d953766d5247ab76ee84"),
            "meta": (os.path.join(V1, "run_state", "RUN_META.json"), "597bd76970412c107c96475dfe8d5093ff7840aba73cb4ab65318f2b0f358950")}
    for k, (p, e) in exp.items():
        print(k, "MATCH" if sha(p) == e else "MISMATCH")

    print("== R31.2 artifacts ==")
    R = os.path.join(R31D, "reports")
    for n in ("V1_R31_2_FORENSIC.json", "V1_R31_2_V2_TREE_HASH.json", "V1_R31_2_REPORT.md"):
        q = os.path.join(R, n)
        ok = "n/a"
        if n.endswith(".json"):
            try:
                json.load(open(q, encoding="utf-8"))
                ok = "JSON_OK"
            except Exception as ex:  # noqa: BLE001
                ok = "JSON_FAIL:" + type(ex).__name__
        print(n, os.path.getsize(q), ok)
    j = json.load(open(os.path.join(R, "V1_R31_2_FORENSIC.json"), encoding="utf-8"))
    print("R31_GATE =", j.get("R31_GATE"), "| V1_V2_ISOLATION =", j.get("V1_V2_ISOLATION"),
          "| histogram =", json.dumps(j.get("histogram"), ensure_ascii=False))
    print("V2_UNCHANGED =", j.get("V2_UNCHANGED"), "| DETERMINISTIC =", (j.get("determinism") or {}).get("DETERMINISTIC_TEST"))

    print("== automation (read-only) ==")
    o = subprocess.run([NODE, CLI, "cron", "show", AID, "--json"], capture_output=True, text=True,
                        encoding="utf-8", errors="replace")
    m = re.search(r"\{.*\}", o.stdout or "", re.S)
    d = json.loads(m.group(0)) if m else {}
    print("AUTOMATION enabled =", d.get("enabled", "UNKNOWN"), "| status =", d.get("status", "UNKNOWN"))

    print("== tail check (no half-written files in task dirs) ==")
    n_tmp = 0
    for root in (R31D, os.path.join(A, r"research\v3_opportunity_engine\v1_r31_1_repair")):
        for r_, _, fs in os.walk(root):
            n_tmp += sum(1 for f in fs if f.endswith(".tmp"))
    print("leftover .tmp files =", n_tmp)


if __name__ == "__main__":
    main()
