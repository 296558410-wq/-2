# -*- coding: utf-8 -*-
"""diff_versions.py — recoverable cycle.py versions + unified diffs (READ-ONLY)."""
import os, subprocess, hashlib, difflib
REPO = r"C:\AIQuant"
OUT = os.path.join(REPO, "research", "hermes", "trader_v1", "audit", "v1_restart_behavior_forensics")
WS = r"C:\Users\surface\.openclaw\workspace"
def blob(sha):
    return subprocess.run(["git", "-C", REPO, "cat-file", "blob", sha], capture_output=True).stdout
V = {
 "V0_20260928_baseline": open(os.path.join(WS, "_cycle.py.backup_20260930_073745"), "rb").read(),
 "V2_20261001_1433_pre_fix": open(os.path.join(REPO, r"research\hermes\trader_v1\v1_upgrade\backup\20261002T034821Z\cycle.py"), "rb").read(),
 "V3_20261002_63d5a22": blob("565a74c04b8ef74534287dda36eafd00d707fb6e"),
 "V4_20261002_eceeec2": blob("fcc686251b0f683c55b739fa6dc1454476ffd00b"),
 "V5_20261002_current": blob("ea2a0fa350cd1f86fce183d1f560ca1845f47dff"),
}
for k, v in V.items():
    print(f"{k:<28} size={len(v):>6} sha256={hashlib.sha256(v).hexdigest()[:16]} docstring={'NEW V1 cycle runner' in v.decode('utf-8','replace')} reconcile={'reconcile_broker_closes(' in v.decode('utf-8','replace')}")

os.makedirs(os.path.join(OUT, "_diff"), exist_ok=True)
pairs = [("V0_20260928_baseline", "V2_20261001_1433_pre_fix"),
         ("V2_20261001_1433_pre_fix", "V3_20261002_63d5a22"),
         ("V3_20261002_63d5a22", "V4_20261002_eceeec2"),
         ("V4_20261002_eceeec2", "V5_20261002_current")]
for a, b in pairs:
    da = V[a].decode("utf-8", "replace").splitlines(keepends=True)
    db = V[b].decode("utf-8", "replace").splitlines(keepends=True)
    d = list(difflib.unified_diff(da, db, fromfile=a, tofile=b, n=2))
    fn = os.path.join(OUT, "_diff", f"{a}__TO__{b}.diff")
    open(fn, "w", encoding="utf-8", newline="\n").writelines(d)
    adds = sum(1 for x in d if x.startswith("+") and not x.startswith("+++"))
    dels = sum(1 for x in d if x.startswith("-") and not x.startswith("---"))
    hunks = sum(1 for x in d if x.startswith("@@"))
    print(f"\nDIFF {a} -> {b}: +{adds} -{dels} hunks={hunks}  ({os.path.relpath(fn, REPO)})")
    for x in [y.rstrip() for y in d if y.startswith('@@')][:20]:
        print("   ", x)
print("\n--- V0 -> V2 hunk bodies (first 80 lines) ---")
dd = open(os.path.join(OUT, "_diff", "V0_20260928_baseline__TO__V2_20261001_1433_pre_fix.diff"), encoding="utf-8").read().splitlines()
print("\n".join(dd[:80]))
