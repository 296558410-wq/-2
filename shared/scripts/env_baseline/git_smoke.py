# -*- coding: utf-8 -*-
"""git_smoke.py - repo / secret hygiene check for C:\\AIQuant (read-only, no mutation).
Verifies: git repo, clean-ish state, .gitignore covers secrets/data/large files,
no secret-like or large binary files tracked, LFS available, no remotes that could
auto-push (push requires explicit action anyway)."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "env_smoke_git.json"

NEEDED_PATTERNS = [r"\.env", r"\.key$|\.pem$|\.pfx$", r"secrets", r"credentials", r"\.venv", r"parquet", r"^\s*data/", r"cache", r"logs", r"\.pth|\.pt$|\.safetensors|\.onnx"]
SECRET_RE = re.compile(r"(api[_-]?key|secret|token|password|passwd|private[_-]?key|BEGIN .*PRIVATE)", re.I)
BIG_SUFFIX = (".parquet", ".pkl", ".pt", ".pth", ".onnx", ".h5", ".feather", ".bin", ".csv.gz", ".safetensors", ".zip")


def run(cmd, cwd=ROOT, timeout=60) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)
    return (r.stdout or r.stderr).strip()


def main() -> None:
    checks: list[dict] = []
    info: dict = {}

    def add(name, ok, detail="", status=None):
        checks.append({"name": name, "status": status or ("PASS" if ok else "FAIL"), "detail": detail})

    is_repo = (ROOT / ".git").is_dir()
    add("is_git_repo", is_repo, "C:\\AIQuant\\.git exists" if is_repo else "NOT a repo")
    if not is_repo:
        OUT.write_text(json.dumps({"status": "FAIL", "checks": checks, "info": info}, indent=2), encoding="utf-8")
        print("git_smoke: FAIL - not a repo"); return

    gi = ROOT / ".gitignore"
    content = gi.read_text(encoding="utf-8", errors="replace") if gi.exists() else ""
    info["gitignore_bytes"] = len(content)
    missing = [p for p in NEEDED_PATTERNS if not re.search(p, content, re.M)]
    add("gitignore_covers", len(missing) == 0, f"missing patterns: {missing if missing else 'none'}")

    remotes = run(["git", "remote"]).splitlines()
    info["remotes"] = remotes
    add("no_remotes", len(remotes) == 0, "no remotes configured (no accidental push possible)" if not remotes else f"remotes={remotes}")

    status = run(["git", "status", "--porcelain"])
    dirty = [ln for ln in status.splitlines() if ln.strip()]
    info["dirty_files"] = len(dirty)
    add("tree_state", True, f"{len(dirty)} uncommitted path(s) (expected during baseline setup)")

    tracked = run(["git", "ls-files"]).splitlines()
    info["tracked_count"] = len(tracked)
    bad = []
    for f in tracked:
        low = f.lower()
        if SECRET_RE.search(f) or any(f.endswith(s) for s in BIG_SUFFIX) or f.startswith(".env") or f == ".env":
            bad.append(f)
    add("no_secrets_tracked", len(bad) == 0, f"flagged tracked paths: {bad[:10] if bad else 'none'}")

    lfs = run(["git", "lfs", "env"], timeout=30).splitlines()
    add("git_lfs_available", any("git-lfs" in ln for ln in lfs), lfs[0] if lfs else "git lfs not available")

    status2 = "FAIL" if any(c["status"] == "FAIL" for c in checks) else ("WARN" if any(c["status"] == "WARN" for c in checks) else "PASS")
    OUT.write_text(json.dumps({"status": status2, "checks": checks, "info": info, "n_checks": len(checks)}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"git_smoke: {status2} ({len(checks)} checks)")
    for c in checks:
        print(f"  [{c['status']}] {c['name']} - {c['detail']}")


if __name__ == "__main__":
    main()
