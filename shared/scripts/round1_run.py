# -*- coding: utf-8 -*-
"""round1_run.py — Phase 2 第一轮：真实 XAUUSD M1 全漏斗。

输出：reports/round1_summary.md + round 详情 json（pipeline 已写 alpha_registry）。
"""
import json
import sys
import time

sys.path.insert(0, "C:/AIQuant")
from pathlib import Path

from alpha_engine.pipeline import M1_DATASET, run_round

t0 = time.perf_counter()
rep = run_round(M1_DATASET, n_perm=800, n_boot=600, train_frac=0.6, backend="auto")
rep["wall_s"] = round(time.perf_counter() - t0, 1)
Path("C:/AIQuant/reports/round1_details.json").write_text(
    json.dumps(rep, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

L = [f"# Phase 2 Round 1 — 真实 XAUUSD M1 结果", "",
     f"- dataset: `{rep['dataset_id']}` · {rep['dataset_meta']['start']} → {rep['dataset_meta']['end']}",
     f"- hypotheses tested: {rep['funnel']['n_tested']} · raw sig: {rep['funnel']['n_raw_sig']} · "
     f"**FDR sig: {rep['funnel']['n_fdr_sig']}** · survivors: {rep['n_survivors']}",
     f"- 耗时: {rep['wall_s']}s（info {rep['info_stage_s']}s）", "",
     "## Survivors", "", "| hypothesis | feature | label | IC_OOS | p | q | wf+ | ci95 |", "|---|---|---|---|---|---|---|---|"]
for s in rep.get("survivors", []):
    ci = s.get("ci95") or ["-", "-"]
    L.append(f"| {s['hypothesis_id']} | {s['feature']} | {s['label']} | {s['ic_oos']} | {s['p']} | "
             f"{s['q']} | {s.get('wf_positive_frac')} | [{ci[0]}, {ci[1]}] |")
L += ["", "## Alpha Registry", ""]
for a in rep.get("alpha_records", []):
    L.append(f"- `{a['alpha_id']}` → **{a['status']}** (ic={a['ic_oos']}, q={a['q']})")
if not rep.get("alpha_records"):
    L.append("（无 FDR 存活候选——按协议如实记录，0 candidates 可接受）")
L += ["", "## Cost rows（FDR 存活者的规则信号成本压力）", ""]
for c in rep.get("cost_rows", []):
    L.append(f"- {c['hypothesis_id']}: 1x={c['1x']} 2x={c['2x']} 3x={c['3x']} "
             f"net={c['net_total']:.4f} trades={c['n_trades']} subperiod+={c['subperiod']['sharpe_positive_frac']}")
if not rep.get("cost_rows"):
    L.append("（无）")
Path("C:/AIQuant/reports/round1_summary.md").write_text("\n".join(L), encoding="utf-8")
print(f"round1 done in {rep['wall_s']}s; funnel={rep['funnel']}; registry={rep['alpha_registry']}")
