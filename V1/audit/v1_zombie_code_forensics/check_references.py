# -*- coding: utf-8 -*-
"""check_references.py — runtime reference check for deleted artifacts + destructive-op scan (READ-ONLY)."""
import os, re, subprocess, json
REPO = r"C:\AIQuant"
OUT = os.path.join(REPO, "research", "hermes", "trader_v1", "audit", "v1_zombie_code_forensics")
def git(*a): return subprocess.run(["git","-C",REPO,*a],capture_output=True,text=True,encoding="utf-8",errors="replace").stdout

# 1) does the agent's 'openclaw' author touch V1 at all?
print("=== commits by author openclaw touching trader_v1 ===")
o = git("log","--all","--author=openclaw","--date=short","--pretty=format:%h|%ad|%s","--name-only","--","research/hermes/trader_v1")
print(o.strip() or "(none)")

# 2) tracked runtime files of V1 (old engine + v1_upgrade)
files = [f for f in git("ls-files","research/hermes/trader_v1").split("\n")
         if f.endswith(".py") and ("/v1_upgrade/" in f or re.match(r"research/hermes/trader_v1/[^/]+\.py$", f))]
print("\nV1 runtime .py files tracked:", len(files))

# 3) references to deleted artifacts from the 09-24 reset
deleted_syms = ["trader_summary", "run_state/decisions", "run_state\\\\decisions", "state_package_latest", "RUN_META", "run_state/positions"]
print("\n=== references to reset-deleted artifacts inside V1 runtime ===")
for f in files:
    try: txt = open(os.path.join(REPO, f), encoding="utf-8", errors="replace").read()
    except Exception: continue
    for s in deleted_syms:
        for m in re.finditer(re.escape(s), txt):
            ln = txt[:m.start()].count("\n")+1
            print(f"  {f.replace('research/hermes/trader_v1/','')}:{ln}  <-{s}->  {txt.splitlines()[ln-1].strip()[:110]}")

# 4) destructive ops in V1 runtime + R8 scripts
print("\n=== destructive ops (os.remove/shutil.rmtree/unlink/rmdir) in V1 runtime + R8 trees ===")
scan = files + [f for f in git("ls-files").split("\n") if "/v1_r8_" in f or "prediction_route" in f]
scan += []
# also include UNTRACKED R8 scripts on disk
for d in ("v1_r8_target_redesign","v1_r8_b_validation","v1_hermes_prediction_route_archive","v1_r2_prediction_upgrade"):
    p = os.path.join(REPO,"research","hermes","trader_v1",d)
    for root,_,fs in os.walk(p):
        for x in fs:
            if x.endswith(".py"): scan.append(os.path.join(root,x))
for f in set(scan):
    p = f if os.path.isabs(f) else os.path.join(REPO, f)
    if not os.path.exists(p): continue
    try: txt = open(p, encoding="utf-8", errors="replace").read()
    except Exception: continue
    for m in re.finditer(r"(os\.remove|os\.unlink|shutil\.rmtree|\.unlink\(|os\.rmdir|Path\([^)]*\)\.unlink)", txt):
        ln = txt[:m.start()].count("\n")+1
        print(f"  {os.path.relpath(p,REPO)}:{ln}  {txt.splitlines()[ln-1].strip()[:110]}")

# 5) cron / scheduled-task / requirements changes
print("\n=== tracked cron/scheduler/requirements files ===")
for pat in ("*.ps1","*cron*","*schedule*","requirements*.txt","pyproject.toml","*.xml"):
    for f in git("ls-files","*"+pat).split("\n"):
        if f: print("  ", f)
