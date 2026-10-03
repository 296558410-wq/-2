# -*- coding: utf-8 -*-
"""enumerate_git.py — enumerate all git changes under research/hermes/trader_v1 (READ-ONLY).
Classifies commits by change type and whether the touched path is a V1 *runtime* path vs research/state.
Writes git_changes_raw.json + prints summaries. Does NOT modify the repo.
"""
from __future__ import annotations
import json, os, subprocess, collections, re

REPO = r"C:\AIQuant"
OUT = os.path.join(REPO, "research", "hermes", "trader_v1", "audit", "v1_zombie_code_forensics")
os.makedirs(OUT, exist_ok=True)

def git(*args):
    return subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout

raw = git("log", "--all", "--no-merges", "--date=iso-strict", "--pretty=format:\x01%H|%ad|%an|%s", "--name-status")
commits = []
cur = None
for line in raw.split("\n"):
    if line.startswith("\x01"):
        h, ad, an, s = line[1:].split("|", 3)
        cur = {"hash": h, "date": ad, "author": an, "subject": s, "changes": []}
        commits.append(cur)
    elif line.strip() and cur is not None:
        parts = line.split("\t")
        if len(parts) >= 2:
            st = parts[0]
            cur["changes"].append({"status": st, "path": parts[-1], "src": parts[1] if st[0] in "RC" and len(parts) > 2 else None})

V1 = "research/hermes/trader_v1/"
v1commits = [c for c in commits if any(ch["path"].startswith(V1) for ch in c["changes"])]
print("total commits:", len(commits), "| touching trader_v1:", len(v1commits))

RUNTIME_RE = re.compile(r"(^|/)(v1_upgrade/)?(cycle|gates|run_gates|engine|trader_core|trigger|position|position_decision|signal_baseline|label_adapter|ledger|invariants|state_package|metrics|review|opportunity|candlestick|stop_authority|replay_study|broker_mt5_demo)\.py$")
def is_runtime(p):
    p2 = p[len(V1):]
    return bool(RUNTIME_RE.search(p2)) or "/registry/" in p2 or p2.endswith("registry.json") or "/truth/" in p2

# commits with deletions or renames anywhere under trader_v1
dr = [c for c in v1commits if any(ch["status"][0] in "DR" for ch in c["changes"])]
print("\n=== commits under trader_v1 with DELETE/RENAME ===")
for c in dr:
    dels = [ch for ch in c["changes"] if ch["status"][0] == "D"]
    rens = [ch for ch in c["changes"] if ch["status"][0] == "R"]
    rt = [ch for ch in dels if is_runtime(ch["path"])]
    print(f"{c['hash'][:9]}|{c['date'][:10]}|{c['author']}|D={len(dels)} R={len(rens)} runtimeD={len(rt)} :: {c['subject'][:90]}")
    for ch in (rt or dels)[:8]:
        print("      -", ch["status"], ch["path"][len(V1):])

# commits touching V1 runtime files (any status)
print("\n=== commits touching V1 RUNTIME files (any status) ===")
rt_commits = [c for c in v1commits if any(is_runtime(ch["path"]) for ch in c["changes"])]
for c in rt_commits:
    rt = [ch for ch in c["changes"] if is_runtime(ch["path"])]
    print(f"{c['hash'][:9]}|{c['date'][:10]}|{c['author']}|n_rt={len(rt)} :: {c['subject'][:95]}")

json.dump({"schema": "zombie_git_raw/1", "n_commits": len(v1commits), "commits": v1commits},
          open(os.path.join(OUT, "git_changes_raw.json"), "w", encoding="utf-8", newline="\n"), ensure_ascii=False)
print("\nwrote git_changes_raw.json ; v1commits:", len(v1commits), "dr:", len(dr), "runtime-touch:", len(rt_commits))
