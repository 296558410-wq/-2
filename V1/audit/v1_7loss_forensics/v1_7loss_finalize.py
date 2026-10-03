# -*- coding: utf-8 -*-
"""v1_7loss_finalize.py — SHA256SUMS + path-limited commits for the 7-loss forensic audit."""
from __future__ import annotations
import hashlib, os, subprocess

REPO = r"C:\AIQuant"
D = os.path.join(REPO, "research", "hermes", "trader_v1", "audit", "v1_7loss_forensics")
REL = "research/hermes/trader_v1/audit/v1_7loss_forensics"


def git(*args):
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "").strip(), (r.stderr or "").strip(), r.returncode


def sums():
    rows = []
    for f in sorted(os.listdir(D)):
        p = os.path.join(D, f)
        if os.path.isfile(p) and f != "SHA256SUMS.txt":
            rows.append((f, hashlib.sha256(open(p, "rb").read()).hexdigest()))
    with open(os.path.join(D, "SHA256SUMS.txt"), "w", encoding="utf-8", newline="\n") as fh:
        for f, h in rows:
            fh.write(f"{h}  {f}\n")
    return rows


rows = sums()
print("manifest files:", len(rows))
for f, h in rows:
    print(f"  {h[:16]}  {f}")

git("add", REL)
out, err, rc = git("commit", "-m",
                   "audit(v1-7loss-forensics): post-restart 7 consecutive losses - full chains + guard reconstruction "
                   "(T4/T5 preventable=RISK_GUARD_FAILURE) + NO_EVIDENCE_OF_RESTART_CAUSALITY",
                   "--", REL)
c1, _, _ = git("rev-parse", "HEAD")
print("commit1:", c1, "rc:", rc, "|", (out.splitlines()[-1] if out else err[:140]))

# patch report with c1 and refresh manifest, then record commit
rp = os.path.join(D, "V1_7_LOSS_FORENSIC_REPORT.md")
t = open(rp, encoding="utf-8").read().replace("<PENDING_COMMIT>", f"`{c1}`（+ 记录提交）")
open(rp, "w", encoding="utf-8", newline="\n").write(t)
sums()
git("add", REL)
out2, err2, rc2 = git("commit", "-m", "docs(v1-7loss): record audit commit hash + refresh SHA256SUMS", "--", REL)
c2, _, _ = git("rev-parse", "HEAD")
print("commit2:", c2, "rc:", rc2, "|", (out2.splitlines()[-1] if out2 else err2[:140]))
