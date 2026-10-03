# -*- coding: utf-8 -*-
"""V1-R2 PHASE B-R5 — apply ns_v3 scope refactor IN PLACE to _v1r2_phaseB_R2.py.

1. Backs up the pre-refactor file to _v1r2_phaseB_R2.py.bak_before_ns_v3_refactor
   (preserves the exact B-R2-era source as evidence; its hash is recorded in the
   BEFORE evidence file).
2. Writes the module-level-refactored source over _v1r2_phaseB_R2.py.
Only ns_v3 moves out of main()'s closure; groups_of/rule_mu/rule_variant already module-level.
No rule/threshold/feature/registry/direction change. GIT_COMMIT=NONE."""
from __future__ import annotations

import hashlib
import os
import shutil

UP = r"C:\AIQuant\research\hermes\trader_v1\v1_r2_prediction_upgrade"
TARGET = os.path.join(UP, "_v1r2_phaseB_R2.py")
REFACTORED = os.path.join(UP, "_v1r2_phaseB_R2_refactored.py")
BACKUP = os.path.join(UP, "_v1r2_phaseB_R2.py.bak_before_ns_v3_refactor")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


orig_hash = sha(TARGET)
ref_hash = sha(REFACTORED)
if not os.path.exists(BACKUP):
    shutil.copy2(TARGET, BACKUP)
print("backup written ->", BACKUP, "| backup sha256:", sha(BACKUP))
print("original sha256 :", orig_hash)
print("refactored sha256:", ref_hash)
shutil.copy2(REFACTORED, TARGET)
print("in-place refactor applied ->", TARGET)
print("target sha256 now:", sha(TARGET))
assert sha(TARGET) == ref_hash
print("APPLY OK")
