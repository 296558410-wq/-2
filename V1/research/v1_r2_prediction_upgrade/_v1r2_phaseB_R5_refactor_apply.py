# -*- coding: utf-8 -*-
"""V1-R2 PHASE B-R5 — ns_v3 scope refactor (mechanical text transform).

Creates `_v1r2_phaseB_R2_refactored.py` = copy of `_v1r2_phaseB_R2.py` with ONLY
`ns_v3` moved from inside main() closure to module level (dedented verbatim).
groups_of/rule_mu/rule_variant were already module-level -> untouched.
No rule / threshold / feature / registry / direction-mapping change.
The original frozen script is NOT modified.
Writes nothing else. GIT_COMMIT=NONE."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

UP = r"C:\AIQuant\research\hermes\trader_v1\v1_r2_prediction_upgrade"
SRC = os.path.join(UP, "_v1r2_phaseB_R2.py")
DST = os.path.join(UP, "_v1r2_phaseB_R2_refactored.py")

src = open(SRC, encoding="utf-8").read()

# locate the ns_v3 definition nested inside main(): line starts with 4-space indent
pat = re.compile(r"^    def ns_v3\(r\):.*?(?=^    v3 = \[ns_v3)", re.M | re.S)
m = pat.search(src)
if not m:
    print("FATAL: ns_v3 block not found as expected (pattern mismatch)")
    sys.exit(2)
block = m.group(0)
# verbatim dedent of exactly 4 spaces
lines = block.split("\n")
dedented = []
for ln in lines:
    if ln.startswith("    "):
        dedented.append(ln[4:])
    elif ln == "":
        dedented.append("")
    else:
        print("FATAL: unexpected non-indented line in ns_v3 block:", repr(ln))
        sys.exit(2)
ns_def = "\n".join(dedented) + "\n"

# remove the block from main() and insert before `def main():`
src_new = src[: m.start()] + src[m.end():]
anchor = "\n\ndef main():"
idx = src_new.index(anchor)
# keep one blank line before the inserted def (mirrors module style)
src_new = src_new[: idx] + "\n" + ns_def.rstrip("\n") + "\n" + src_new[idx:]

with open(DST, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(src_new)

src_hash = hashlib.sha256(src.encode("utf-8")).hexdigest()
dst_hash = hashlib.sha256(src_new.encode("utf-8")).hexdigest()
print("SOURCE_HASH_BEFORE =", src_hash)
print("SOURCE_HASH_AFTER  =", dst_hash)
print("new module written ->", DST)

# quick sanity: the only top-level difference should be the added ns_v3 FunctionDef
import ast  # noqa: E402
t1 = ast.parse(src)
t2 = ast.parse(src_new)
m1 = [n.name for n in t1.body if isinstance(n, ast.FunctionDef)]
m2 = [n.name for n in t2.body if isinstance(n, ast.FunctionDef)]
print("module fns before:", m1)
print("module fns after :", m2)
print("added:", sorted(set(m2) - set(m1)), "| removed:", sorted(set(m1) - set(m2)))
