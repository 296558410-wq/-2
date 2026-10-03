# -*- coding: utf-8 -*-
"""recover.py — try to recover the pre-edit cycle.py + detect code-change traces. READ-ONLY."""
import subprocess, os, json, re, struct, sys
REPO = r"C:\AIQuant"
def git(*a, binary=False):
    r = subprocess.run(["git", "-C", REPO, *a], capture_output=True)
    out = r.stdout or b""
    return out if binary else out.decode("utf-8", "replace")

print("=== reflog / stash ===")
print(git("reflog", "--all").strip()[:800] or "(none)")
print(git("stash", "list").strip() or "(no stash)")

# 1) scan ALL git blobs for cycle.py-like content
print("\n=== scanning git objects for cycle.py-like blobs ===")
bc = git("cat-file", "--batch-all-objects", "--batch-check=%(objectname) %(objecttype) %(objectsize)")
cands = []
for line in bc.splitlines():
    p = line.split()
    if len(p) == 3 and p[1] == "blob":
        try: sz = int(p[2])
        except: continue
        if 8000 <= sz <= 40000: cands.append(p[0])
print("blobs in 8-40KB:", len(cands))
sig = re.compile(rb"(NEW V1 cycle runner|reconcile_broker_closes|v1up-baseline-transition-order-map|BASELINE_CONTROL|pick_filling|label_adapter)")
hits = []
for sha in cands:
    data = git("cat-file", "blob", sha, binary=True)
    if sig.search(data):
        hits.append((sha, len(data), {k.decode(): len(re.findall(k, data)) for k in [b"reconcile_broker_closes", b"pick_filling", b"data_age_seconds", b"m15_last_close", b"rebuild_risk_state"]}))
print("candidate blobs:", len(hits))
for sha, sz, feats in hits:
    print(f"  {sha} size={sz} {feats}")
# try to identify any that resemble cycle.py and save
for sha, sz, feats in hits:
    data = git("cat-file", "blob", sha, binary=True)
    if b"NEW V1 cycle runner" in data or b"def main(" in data and b"snapshot(" in data:
        open(os.path.join(os.environ.get("TMP", r"C:\Users\surface\AppData\Local\Temp"), f"recovered_{sha[:12]}.py"), "wb").write(data)
        print("  saved recovered_%s.py (%d bytes)" % (sha[:12], sz))

# 2) pyc header inspection + does any pyc encode a smaller source?
print("\n=== pyc headers ===")
for root, _, fs in os.walk(REPO):
    if "node_modules" in root or "site-packages" in root or "\\.git" in root: continue
    for f in fs:
        if f.endswith(".pyc") and f.startswith("cycle"):
            p = os.path.join(root, f); d = open(p, "rb").read(16)
            magic = int.from_bytes(d[:4], "little"); flags = int.from_bytes(d[4:8], "little")
            mtime = int.from_bytes(d[8:12], "little"); ssize = int.from_bytes(d[12:16], "little")
            import datetime as dt
            print(f"  {os.path.relpath(p,REPO)} magic={magic} flags={flags} src_mtime={dt.datetime.utcfromtimestamp(mtime)} src_size={ssize} file_size={os.path.getsize(p)}")
