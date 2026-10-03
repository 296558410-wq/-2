"""Generate SHA256SUMS.txt as the LAST step, then verify it.

Addresses the Phase-1 defect (manifest written before the final runner rewrite):
here the manifest is produced only after every other file is frozen, and it is
immediately re-verified.

Runtime state under `shadow/` (heartbeat log, run log, state machine, gpu cache,
shadow registry) is APPEND-ONLY and changes every cycle, so it is EXCLUDED from
the manifest. Otherwise the manifest would be stale after every heartbeat and
could never verify between checkpoints. The manifest therefore covers the frozen
research artifacts + code; runtime state is validated separately by the runner
(`stability_check.py` / heartbeat self-report).

CLI:  python runner/make_manifest.py
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths as PP  # noqa: E402
from common import hashing  # noqa: E402

OUT = "SHA256SUMS.txt"
# Volatile runtime classes, excluded on purpose (see module docstring).
EXCLUDE_DIRS = {"__pycache__", "shadow"}


def _iter_files(root):
    for p in sorted(os.path.join(dp, f) for dp, _, fs in os.walk(root) for f in fs):
        parts = p.split(os.sep)
        if os.path.basename(p) == OUT:
            continue
        if any(d in parts for d in EXCLUDE_DIRS):
            continue
        yield p


def _write(root, out_name):
    lines = []
    for p in _iter_files(root):
        rel = os.path.relpath(p, root).replace(os.sep, "/")
        lines.append(f"{hashing.sha256_file(p)}  {rel}")
    with open(os.path.join(root, out_name), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return len(lines)


def make_and_verify():
    # Record the manifest event BEFORE hashing; it lives under the excluded
    # runtime dir, so it can never make the manifest stale.
    PP.log_event("manifest", {"status": "generating"})
    n = _write(PP.P2, OUT)
    bad = []
    checked = 0
    with open(PP.SHA256SUMS, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            digest, rel = line.split("  ", 1)
            path = os.path.join(PP.P2, rel)
            if not os.path.exists(path):
                bad.append((rel, "MISSING"))
                continue
            got = hashing.sha256_file(path)
            checked += 1
            if got != digest:
                bad.append((rel, "MISMATCH"))
    status = "PASS" if not bad and checked == n else "FAIL"
    print(f"[make_manifest] entries={n} verified={checked} status={status}")
    if bad:
        print("[make_manifest] problems:", bad)
        sys.exit(1)
    return {"entries": n, "verified": checked, "status": status}


if __name__ == "__main__":
    make_and_verify()
