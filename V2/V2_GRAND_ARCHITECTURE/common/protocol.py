"""Unified research protocol.

Every strategy research pass MUST carry:
  PIT -> Hypothesis Freeze -> Discovery -> Validation -> Untouched OOS ->
  Bootstrap -> Permutation -> FDR -> Stability -> Shadow
and record: input_hash / code_commit / config_hash / seed / data_source /
feature_hash / model_hash.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
import json

from . import hashing

STAGES = ["PIT", "HYPOTHESIS_FREEZE", "DISCOVERY", "VALIDATION", "UNTOUCHED_OOS",
          "BOOTSTRAP", "PERMUTATION", "FDR", "STABILITY", "SHADOW"]


@dataclass
class ResearchProtocol:
    name: str
    seed: int
    data_source: str
    input_hash: str = ""
    code_commit: str = ""
    config_hash: str = ""
    feature_hash: str = ""
    model_hash: str = ""
    stages_completed: list = field(default_factory=lambda: [])
    notes: str = ""

    def record(self, **overrides) -> None:
        for k, v in overrides.items():
            setattr(self, k, v)
        if not self.code_commit:
            self.code_commit = hashing.git_commit()

    def mark(self, stage: str) -> None:
        if stage not in STAGES:
            raise ValueError(f"unknown stage {stage}")
        if stage not in self.stages_completed:
            self.stages_completed.append(stage)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["stages_defined"] = STAGES
        return d

    def write(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
