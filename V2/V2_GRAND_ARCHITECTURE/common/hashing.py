"""Deterministic hashing utilities for reproducibility.

Every artifact records sha256 of its inputs so numbers can be re-derived.
"""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | os.PathLike) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(obj) -> str:
    return sha256_bytes(canonical_json(obj).encode("utf-8"))


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def git_commit(repo: str = r"C:\AIQuant") -> str:
    try:
        out = subprocess.check_output(
            ["git", "-C", repo, "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        )
        return out.decode().strip()
    except Exception:
        return "UNKNOWN"


def git_dirty(repo: str = r"C:\AIQuant") -> bool:
    try:
        out = subprocess.check_output(
            ["git", "-C", repo, "status", "--porcelain"], stderr=subprocess.DEVNULL
        )
        return len(out.strip()) > 0
    except Exception:
        return True


def write_sha256sums(root: str | os.PathLike, out_name: str = "SHA256SUMS.txt") -> int:
    """Write SHA256SUMS.txt for every tracked file under root except the sums file."""
    root = Path(root)
    lines = []
    for p in sorted(root.rglob("*")):
        if p.is_dir():
            continue
        if p.name == out_name:
            continue
        if "__pycache__" in p.parts:
            continue
        rel = p.relative_to(root).as_posix()
        lines.append(f"{sha256_file(p)}  {rel}")
    (root / out_name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)
