# -*- coding: utf-8 -*-
"""Emit before/after SHA256 + a unified diff of the applied patch."""
from __future__ import annotations
import difflib, hashlib, json, os

BASE = r"C:\AIQuant\research\hermes\trader_v1\v1_upgrade"
AUDIT = r"C:\AIQuant\research\hermes\trader_v1\audit"
BACK = os.path.join(BASE, "backup", "20261002T034821Z")
FILES = {"gates.py": ("gates.py", "gates.py"), "cycle.py": ("cycle.py", "cycle.py")}
BEFORE = {
    "gates.py": "0e02a4240b517b2a987c377d4488945a75c701c144e56ca3691d0ed349f2c9d3",
    "cycle.py": "dcb7edde220cfe07be93c72cda1fa55ae48ed71316b384a38c1898d7161b523b",
    "run_gates.py": "c2fc89be0f27bb90f0fe7144e445e310c862418210d487ce483a1127ce7018a7",
    "registry/runtime_config.json": "0732456adc415587763894506e0cd981460711966b2782d3bfda89acff062b38",
    "label_adapter.py": "3e67542e8a2d3730db25d87b5eb3a3a71d52938eb8fda3d833f1350c4d5d4189",
}


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


rows, diff_chunks = [], []
for name in ("gates.py", "cycle.py"):
    a = os.path.join(BACK, name)
    b = os.path.join(BASE, name)
    rows.append({"file": name, "before_sha256": BEFORE[name], "after_sha256": sha(b),
                 "changed": BEFORE[name] != sha(b)})
    d = difflib.unified_diff(open(a, encoding="utf-8").read().splitlines(),
                             open(b, encoding="utf-8").read().splitlines(),
                             fromfile=f"a/{name}", tofile=f"b/{name}", lineterm="")
    diff_chunks.append("\n".join(d))
# untouched production files
untouched = {}
for f in ("run_gates.py", "registry/runtime_config.json", "label_adapter.py"):
    cur = sha(os.path.join(BASE, f))
    untouched[f] = {"before_sha256": BEFORE[f], "after_sha256": cur, "unchanged": BEFORE[f] == cur}
open(os.path.join(AUDIT, "V1_PATCH_DIFF.txt"), "w", encoding="utf-8", newline="\n").write(
    "V1 risk-guard wiring fix — unified diff (backup -> applied)\n\n" + "\n\n".join(diff_chunks) + "\n")
doc = {"changed_files": rows, "untouched_production_files": untouched}
json.dump(doc, open(os.path.join(AUDIT, "V1_PATCH_HASHES.json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
print(json.dumps(doc, ensure_ascii=False, indent=1))
