# -*- coding: utf-8 -*-
"""analyze_blobs.py — find all cycle.py versions in the git object DB + reachability + markers."""
import subprocess, os, hashlib, re
REPO = r"C:\AIQuant"
def git(*a, binary=False):
    r = subprocess.run(["git", "-C", REPO, *a], capture_output=True)
    return r.stdout if binary else (r.stdout or b"").decode("utf-8", "replace")
cur = open(os.path.join(REPO, r"research\hermes\trader_v1\v1_upgrade\cycle.py"), "rb").read()
bak = open(os.path.join(REPO, r"research\hermes\trader_v1\v1_upgrade\backup\20261002T034821Z\cycle.py"), "rb").read()
print("current cycle.py sha256:", hashlib.sha256(cur).hexdigest(), len(cur))
print("backup  cycle.py sha256:", hashlib.sha256(bak).hexdigest(), len(bak))
reach = set()
for line in git("rev-list", "--objects", "--all").splitlines():
    reach.add(line.split()[0])
print("reachable objects:", len(reach))
bc = git("cat-file", "--batch-all-objects", "--batch-check=%(objectname) %(objecttype) %(objectsize)").splitlines()
sig = b"NEW V1 cycle runner"
found = []
for line in bc:
    p = line.split()
    if len(p) != 3 or p[1] != "blob": continue
    sha = p[0]
    data = git("cat-file", "blob", sha, binary=True)
    if sig in data:
        found.append((sha, len(data), sha in reach, data))
print("cycle.py-like blobs (docstring match):", len(found))
def marks(d):
    return {k: d.count(k.encode()) for k in ["def main(", "def snapshot(", "def reconcile_broker_closes(", "rebuild_risk_state", "data_age_seconds", "SERVER_OFFSET_SEC", "pick_filling", "from gates import", "m15_last_close", "own_positions", "account_mode"]}
TMP = os.path.join(REPO, "research", "hermes", "trader_v1", "audit", "v1_restart_behavior_forensics", "_recovered")
os.makedirs(TMP, exist_ok=True)
for sha, sz, rch, data in sorted(found, key=lambda x: x[1]):
    print(f"  {sha} size={sz} reachable={rch} sha256={hashlib.sha256(data).hexdigest()[:16]} {marks(data)}")
    if hashlib.sha256(data).hexdigest() != hashlib.sha256(cur).hexdigest():
        open(os.path.join(TMP, f"cycle_{sha[:12]}_{sz}.py"), "wb").write(data)
print("saved to", TMP)
