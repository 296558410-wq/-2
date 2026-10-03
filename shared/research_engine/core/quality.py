# -*- coding: utf-8 -*-
"""core/quality.py — Research Quality Gate（§18）。

实验完成后自动检查清单；任一关键项失败 → 结论不允许 SUPPORTED。
检查项从实验记录字段自动评估。
"""
from __future__ import annotations

from dataclasses import dataclass, field

CRITICAL = [
    ("no_lookahead_checked", "no_lookahead_checked", "No look-ahead（截断重算校验）"),
    ("no_leakage", "no_leakage", "No leakage（特征/标签时间隔离）"),
    ("oos_exists", "oos_exists", "OOS exists（样本外区间）"),
    ("walk_forward_done", "walk_forward_done", "Walk-forward exists"),
    ("cost_included", "cost_included", "Cost included"),
    ("multiple_testing_done", "multiple_testing_done", "Multiple testing considered"),
    ("shuffle_test_done", "shuffle_test_done", "Shuffle test"),
    ("placebo_test_done", "placebo_test_done", "Placebo test"),
    ("seed_recorded", "seed_recorded", "Seed recorded"),
    ("git_commit_recorded", "git_commit_recorded", "Git commit recorded"),
    ("dataset_version_recorded", "dataset_version_recorded", "Dataset version recorded"),
]


@dataclass
class QualityReport:
    items: dict = field(default_factory=dict)   # key -> bool
    critical_failed: list = field(default_factory=list)
    passed: bool = False

    def to_dict(self) -> dict:
        return {"passed": self.passed, "critical_failed": self.critical_failed,
                "items": self.items}


def evaluate_quality(record: dict) -> QualityReport:
    """record: 实验最终记录（含 quality_* 字段或由 runner 汇总的字段）。"""
    items: dict[str, bool] = {}
    failed: list[str] = []
    for key, field_name, label in CRITICAL:
        if key == "seed_recorded":
            val = record.get("random_seed") is not None
        elif key == "git_commit_recorded":
            gc = record.get("git_commit")
            val = bool(gc) and gc not in ("no-git",)
        elif key == "dataset_version_recorded":
            val = bool(record.get("dataset_version"))
        else:
            val = bool(record.get(field_name))
        ok = bool(val) if val is not None else False
        items[key] = ok
        if not ok:
            failed.append(key)
    return QualityReport(items=items, critical_failed=failed,
                         passed=len(failed) == 0)


def quality_summary_md(q: QualityReport) -> str:
    lines = ["| 检查项 | 状态 |", "|---|---|"]
    for key, field_name, label in CRITICAL:
        ok = q.items.get(key, False)
        lines.append(f"| {label} | {'✅' if ok else '❌'} |")
    return "\n".join(lines)
