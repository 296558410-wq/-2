# -*- coding: utf-8 -*-
"""V3 freeze finalize: baseline V1/V2 status -> patch acceptance -> commit -> record commit.

Path-limited to research/hermes/trader_v3/**. Does not touch V1/V2.
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys

REPO = r"C:\AIQuant"
V3 = os.path.join(REPO, "research", "hermes", "trader_v3")
D = os.path.join(V3, "research", "v3_freeze_handoff")
ACC = os.path.join(D, "V3_FREEZE_ACCEPTANCE.json")
DOC = os.path.join(D, "V3_RESEARCH_FINAL_STATUS.md")
MAN = os.path.join(D, "V3_FREEZE_MANIFEST.json")


def git(*args):
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return (r.stdout or "").strip(), (r.stderr or "").strip(), r.returncode


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


# 1) baseline V1/V2 status
st, _, _ = git("status", "--short", "--", "research/hermes/trader_v1", "research/hermes/trader_v2")
lines = [l for l in st.splitlines() if l.strip()]
base = {"count": len(lines), "sha256": hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()}
acc = json.load(open(ACC, encoding="utf-8"))
acc["checks"]["v1_v2_untouched"]["baseline_status_count"] = base["count"]
acc["checks"]["v1_v2_untouched"]["baseline_status_sha256"] = base["sha256"]
json.dump(acc, open(ACC, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
print("baseline v1/v2 status:", base["count"], "entries |", base["sha256"][:16])

# 2) commit 1 (freeze commit)
git("add", "research/hermes/trader_v3/gpu_infra")
git("add", "research/hermes/trader_v3/research/v3_freeze_handoff")
out, err, rc = git("commit", "-m",
                   "feat(v3-research-freeze): freeze & handoff - final status + 414-artifact SHA256 manifest + "
                   "acceptance (TEMPORAL_HOLD RUNNING, TRADING_EXECUTION DISABLED) + GPU infra selftest 8/8",
                   "--", "research/hermes/trader_v3")
c1, _, _ = git("rev-parse", "HEAD")
print("commit1:", c1, "| rc:", rc, "|", out.splitlines()[-1] if out else err[:120])

# 3) patch acceptance + doc with c1
acc = json.load(open(ACC, encoding="utf-8"))
acc["freeze_commit"] = c1 + " (initial; record commit follows)"
json.dump(acc, open(ACC, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
doc = open(DOC, encoding="utf-8").read()
doc = doc.replace("（本收尾 commit 见 §10）", f"收尾 commit `{c1[:7]}`（+ 记录提交）")
open(DOC, "w", encoding="utf-8", newline="\n").write(doc)

# 4) regenerate freeze_dir_files in the manifest (exclude the manifest itself)
man = json.load(open(MAN, encoding="utf-8"))
fd = {}
for f in sorted(os.listdir(D)):
    p = os.path.join(D, f)
    if os.path.isfile(p) and f != "V3_FREEZE_MANIFEST.json":
        fd[f] = {"sha256": sha_file(p), "bytes": os.path.getsize(p)}
man["freeze_dir_files"] = fd
json.dump(man, open(MAN, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
print("freeze_dir_files:", len(fd))

# 5) commit 2 (record commit)
git("add", "research/hermes/trader_v3/research/v3_freeze_handoff")
out, err, rc = git("commit", "-m",
                   "docs(v3-freeze): record freeze commit hash, V1/V2 baseline, and freeze_dir_files hashes",
                   "--", "research/hermes/trader_v3")
c2, _, _ = git("rev-parse", "HEAD")
print("commit2:", c2, "| rc:", rc, "|", out.splitlines()[-1] if out else err[:120])
print(json.dumps({"freeze_commit": c1, "record_commit": c2, "v1v2_baseline": base,
                  "freeze_dir_files": list(fd.keys())}, ensure_ascii=False))
