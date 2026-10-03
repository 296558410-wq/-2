# -*- coding: utf-8 -*-
"""core/report.py — Research Report 自动生成（§17）。

结论词汇表只允许：SUPPORTED / REJECTED / EDGE_UNCERTAIN。
（PROFITABLE / GUARANTEED / HIGH CONFIDENCE ALPHA 被 experiment.py 直接拒绝。）
"""
from __future__ import annotations

from typing import Optional

from .quality import quality_summary_md


def _f(x, nd=6):
    if x is None:
        return "-"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def build_report_md(rec: dict, extra: Optional[dict] = None) -> str:
    extra = extra or {}
    m = rec.get("metrics", {}) or {}
    v = rec.get("validation", {}) or {}
    L: list[str] = []
    L.append(f"# Experiment Report: {rec.get('name', '')}")
    L.append("")
    L.append(f"- **experiment_id**: `{rec.get('experiment_id')}`")
    L.append(f"- **status**: {rec.get('status')}")
    L.append(f"- **conclusion**: **{rec.get('conclusion')}**")
    L.append(f"- **hypothesis**: {rec.get('hypothesis')}")
    L.append(f"- **dataset**: {rec.get('dataset_version')} | features: {rec.get('feature_version')} | labels: {rec.get('label_version')}")
    L.append(f"- **seed**: {rec.get('random_seed')} | backend: {rec.get('backend')} | git: {rec.get('git_commit')}")
    L.append(f"- **machine**: {rec.get('machine', {}).get('host')} ({rec.get('machine', {}).get('gpu', 'no-gpu')})")
    L.append(f"- **time**: {rec.get('start_time')} → {rec.get('end_time', '-')} ({rec.get('elapsed_s')}s)")
    L.append("")

    L.append("## Parameters")
    L.append("")
    L.append("```json")
    L.append(json_dumps(rec.get("parameters", {})))
    L.append("```")
    L.append("")

    L.append("## Metrics")
    L.append("")
    if m:
        L.append("| metric | value |")
        L.append("|---|---|")
        for k, val in m.items():
            L.append(f"| {k} | {_f(val) if not isinstance(val, dict) else json_dumps(val, inline=True)} |")
    else:
        L.append("(无指标)")
    L.append("")

    L.append("## Statistical Tests / Validation")
    L.append("")
    L.append("```json")
    L.append(json_dumps(v))
    L.append("```")
    L.append("")

    L.append("## Quality Gate")
    L.append("")
    q = rec.get("quality")
    if q:
        qr_items = q.get("items", {})
        L.append(quality_summary_md_from_items(qr_items))
        L.append("")
        L.append(f"**质量门通过**: {'✅' if q.get('passed') else '❌'}"
                 + (f"（未过项: {q.get('critical_failed')}）" if not q.get("passed") else ""))
    else:
        L.append("(未评估)")
    L.append("")

    L.append("## Conclusion")
    L.append("")
    L.append(f"结论：**{rec.get('conclusion')}** — 依据：hypothesis 检验 + OOS + walk-forward + "
             "多重检验校正 + shuffle/placebo + 成本压力（详见上方测试结果）。")
    L.append("")
    L.append("---")
    L.append("*由 AIQuant research_engine 自动生成；统计结论 ≠ 交易建议。*")
    return "\n".join(L)


def quality_summary_md_from_items(items: dict) -> str:
    labels = {
        "no_lookahead_checked": "No look-ahead", "no_leakage": "No leakage",
        "oos_exists": "OOS exists", "walk_forward_done": "Walk-forward",
        "cost_included": "Cost included", "multiple_testing_done": "Multiple testing",
        "shuffle_test_done": "Shuffle test", "placebo_test_done": "Placebo test",
        "seed_recorded": "Seed", "git_commit_recorded": "Git commit",
        "dataset_version_recorded": "Dataset version",
    }
    rows = ["| 检查项 | 状态 |", "|---|---|"]
    for k, label in labels.items():
        rows.append(f"| {label} | {'✅' if items.get(k) else '❌'} |")
    return "\n".join(rows)


def json_dumps(obj, inline: bool = False) -> str:
    import json
    if inline:
        return json.dumps(obj, ensure_ascii=False, default=str)
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)
