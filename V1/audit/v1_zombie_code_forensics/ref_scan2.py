# -*- coding: utf-8 -*-
"""ref_scan2.py — scan V1 runtime for references to reset-deleted state dirs + archive/reset semantics."""
import os, re, subprocess
REPO = r"C:\AIQuant"
def git(*a): return subprocess.run(["git","-C",REPO,*a],capture_output=True,text=True,encoding="utf-8",errors="replace").stdout
files = [f for f in git("ls-files","research/hermes/trader_v1").split("\n")
         if f.endswith(".py") and (re.match(r"research/hermes/trader_v1/[^/]+\.py$", f) or "/v1_upgrade/" in f)]
pats = ["decisions", "positions", "\"archive\"", "archive/", "reset", "run_state"]
print("files:", len(files))
for f in files:
    p = os.path.join(REPO, f)
    if not os.path.exists(p): continue
    txt = open(p, encoding="utf-8", errors="replace").read().splitlines()
    for i, ln in enumerate(txt, 1):
        for s in pats:
            if s.strip('"') in ln and ("decisions" in ln or "positions" in ln or "archive" in ln or "reset" in ln):
                print(f"  {f.replace('research/hermes/trader_v1/','')}:{i}  {ln.strip()[:120]}")
                break
# does the deleted decisions dir exist now, and is there an archive dir?
for d in ("run_state/decisions", "run_state/positions", "run_state/archive", "run_state/tmp"):
    p = os.path.join(REPO, "research", "hermes", "trader_v1", d)
    n = len(os.listdir(p)) if os.path.isdir(p) else None
    print(f"[dir] {d}: exists={os.path.isdir(p)} entries={n}")
