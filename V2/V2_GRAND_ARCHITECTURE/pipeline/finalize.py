"""Write all deliverable reports / registries / FINAL_REPORT."""
from __future__ import annotations
import json
import os
import sys
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from common import hashing

BUILD_ORDER = [
    "strategy_factory", "strategy_registry", "strategy_brain", "strategy_memory",
    "evolution", "gpu_research", "opportunity_hub", "intelligence", "pipeline",
]


def _w(name, text):
    path = os.path.join(ROOT, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def architecture_md(state):
    commit = state["commit"]
    g = state["gpu"]
    return f"""# ARCHITECTURE — V2 多策略智能交易系统（第一阶段）

> 只读 / Shadow 研究程序。生产 V2 未改动；`order_send = 0`。code_commit `{commit}`。

## 总览
把当前 V2 从「单一 Reference Decision + Opportunity Discovery」升级为
**多策略、自适应、可进化、GPU 加速、可审计**的 XAUUSD 研究系统。本阶段只做研究，不接生产。

## 模块树
```
V2_GRAND_ARCHITECTURE/
├── ARCHITECTURE.md
├── common/              共享原语：hashing / data(PIT) / pit / cost / metrics / protocol / eval
├── strategy_factory/    机制库(11 族) + 工厂(生成候选与元数据)
├── strategy_registry/   生命周期状态机 + jsonl 注册表
├── strategy_brain/      多策略聚合：一致/冲突/缺席/数据不足 → WAIT
├── strategy_memory/     逐次预测与结果档案(无 outcome leakage)
├── evolution/           证据触发式演化(无固定 48h)
├── gpu_research/        torch/CUDA 真算：特征矩阵/rolling/batch 评估/bootstrap/permutation/walk-forward
├── opportunity_hub/     多来源机会生成→排序→过滤（原 Discovery 保留为 Reference）
├── intelligence/        真实 LLM 接口预留（LLM_UNAVAILABLE，无 authority）
└── pipeline/            编排与报告生成
```

## 关键约束
- PIT：特征只用 `bar<=t`；标签取自 `t+1..t+h`；OOS 在最终揭示前不参与选择。
- 成本：中位实测 round-trip spread = **{state['cost']:.4f}** 价格单位（来自本地 FXTM tick 归档）。
- 数据：本地 XAUUSD tick 归档（{state['n_ticks']} ticks，{state['n_bars']} 根 1m bar，
  {state['date_min']}..{state['date_max']}），dataset_hash `{state['dataset_hash'][:16]}…`。
- 分裂：discovery `{state['splits']['discovery']}` / validation `{state['splits']['validation']}` /
  untouched OOS `{state['splits']['oos']}`。
- GPU：{g.get('gpu', {}).get('device')}，torch {g.get('gpu', {}).get('torch')}，CUDA {g.get('gpu', {}).get('cuda_version')}，
  peak VRAM {g.get('peak_vram_mb')} MB，speedup {g.get('speedup')}×。

## 数据流
`tick 归档 → 1m/15m bars → PIT 特征矩阵 + regime → Strategy Factory 生成候选 →
Strategy Registry 登记 → Discovery 评估 →（GPU 大规模搜索）→ Validation →
Untouched OOS → Bootstrap/Permutation/FDR → Competition 打分 → Brain 聚合 →
Memory 建档 → Evolution 监测 → Portfolio 组合 → 报告`。
"""


def factory_report(state):
    lines = ["# STRATEGY_FACTORY_REPORT", "", f"code_commit `{state['commit']}`", "",
             f"机制族：{len(state['mechanism_families'])}；生成候选策略：{len(state['specs'])}（全部为独立机制，非 V1/V2 规则复制）。", "",
             "| strategy_id | mechanism | horizon | disc_n | disc_exp | val_exp | oos_n | oos_exp | fdr |",
             "|---|---|---|---|---|---|---|---|---|"]
    for s in state["specs"]:
        r = state["results"][s.strategy_id]
        d, v, o = r["splits"]["discovery"], r["splits"]["validation"], r["splits"]["oos"]
        lines.append(f"| {s.strategy_id} | {s.mechanism} | {s.expected_horizon} | {d['n_eff']} | "
                     f"{_f(d['expectancy'])} | {_f(v['expectancy'])} | {o['n_eff']} | {_f(o['expectancy'])} | "
                     f"{'Y' if r['fdr_pass'] else 'n'} |")
    lines += ["", "每个候选的完整元数据（hypothesis_id/mechanism/feature_set/parameters/expected_horizon/"
              "applicable_regime/entry/exit/invalidation/cost_model/PIT/creation commit/dataset hash）"
              "见 `STRATEGY_REGISTRY.jsonl`。"]
    return "\n".join(lines)


def competition_report(state):
    comp = state["competition"]
    rows = sorted(comp.items(), key=lambda kv: -kv[1]["combined_score"])
    lines = ["# STRATEGY_COMPETITION", "",
             "综合分 = 0.25*Performance + 0.20*Stability + 0.20*RegimeFit + 0.15*SampleSize + 0.20*CostRobustness。",
             "**禁止按历史收益排序选冠军。**", "",
             "| rank | strategy_id | combined | perf | stab | fit | sample | cost | state |",
             "|---|---|---|---|---|---|---|---|---|"]
    for k, (sid, c) in enumerate(rows, 1):
        cc = c["components"]
        st = state["registry_records"].get(sid, {}).get("state", "?")
        lines.append(f"| {k} | {sid} | {c['combined_score']} | {cc['performance']} | {cc['stability']} | "
                     f"{cc['regime_fit']} | {cc['sample_size']} | {cc['cost_robustness']} | {st} |")
    return "\n".join(lines)


def regime_matrix_report(state):
    m = state["regime_matrix"]
    regimes = sorted({r for v in m.values() for r in v})
    lines = ["# REGIME_STRATEGY_MATRIX", "",
             "每个机制族 × regime 的期望值/样本/精度。", "",
             "| mechanism | " + " | ".join(regimes) + " |",
             "|---" * (len(regimes) + 1) + "|"]
    for mech, byreg in m.items():
        cells = []
        for r in regimes:
            d = byreg.get(r)
            cells.append(f"{_f(d['expectancy'])} (n={d['n_eff']})" if d else "—")
        lines.append(f"| {mech} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def brain_report(state):
    b = state["brain"]
    lines = ["# STRATEGY_BRAIN_REPORT", "",
             f"中位 horizon = {b['median_horizon']} bars。决策类别：ENTER_LONG / ENTER_SHORT / WAIT / WAIT_DATA_GAP。",
             "支持：策略一致 / 策略冲突 / 策略缺席 / 数据不足 → WAIT；从不强迫交易。", ""]
    for seg, s in b["stats"].items():
        lines.append(f"- **{seg}**：decisions={s['n_decisions']} enter={s['n_enter']} n_eff={s['n_eff']} "
                     f"expectancy={_f(s['expectancy'])} total={_f(s['total'])}")
    lines += ["", "冲突分布：", "```", json.dumps(b["conflict_counts"], ensure_ascii=False, indent=2), "```"]
    return "\n".join(lines)


def evolution_report(state):
    e = state["evolution"]
    lines = ["# EVOLUTION_ENGINE_REPORT", "",
             "无固定 48h；触发因素：edge degradation / regime transition / MAE expansion / MFE contraction / "
             "confidence drift / cost sensitivity。状态：NO_CHANGE / SHADOW / CANDIDATE_RELEASE / RETIRED。", "",
             f"状态计数：`{json.dumps(e['counts'], ensure_ascii=False)}`", "",
             "| strategy_id | state | triggers |",
             "|---|---|---|"]
    for sid, v in e["states"].items():
        lines.append(f"| {sid} | {v['state']} | {', '.join(v['triggers']) or '—'} |")
    return "\n".join(lines)


def gpu_report(state):
    g = state["gpu"]
    return f"""# GPU_RESEARCH_REPORT

真机 GPU 计算（非「GPU 存在」）。设备信息与实测：

- device: {g.get('gpu', {}).get('device')}
- capability: {g.get('gpu', {}).get('capability')}
- torch: {g.get('gpu', {}).get('torch')} / CUDA {g.get('gpu', {}).get('cuda_version')}
- total VRAM: {g.get('gpu', {}).get('total_vram_mb')} MB
- workload: {g.get('workload')}
- 组合数 (batch grid): {g.get('n_combos')}
- **GPU runtime**: {g.get('gpu_runtime_s')} s；**CPU runtime**: {g.get('cpu_runtime_s')} s；**speedup**: {g.get('speedup')}×
- **peak VRAM**: {g.get('peak_vram_mb')} MB（{g.get('peak_vram_pct')}%）
- GPU utilization: {g.get('gpu_utilization_pct')}
- GPU memory used: {g.get('gpu_mem_used_mb')}
- bootstrap resamples: {g.get('bootstrap_resamples')}

GPU 承担：特征矩阵、rolling window、批量策略评估、bootstrap、permutation、多窗口 walk-forward、regime 条件分析。
用 chunk/streaming 控显存以适配 4 GB。

## 大规模搜索
- searched_hypotheses = {state['gpu_search']['searched_hypotheses']}
- eligible(样本足够) = {state['gpu_search']['eligible']}
- selected_top_k = {state['gpu_search']['selected_top_k']}
"""


def lifecycle_report(state):
    d = state["decay_lab"]
    return f"""# STRATEGY_LIFECYCLE

## 状态机
`RESEARCH → SHADOW → CANDIDATE → VALIDATED → ACTIVE → DEGRADED → RETIRED`。
不得因单次盈利直接 ACTIVE；晋升需证据；旧策略不删除（可由市况变化 `RESEARCH → SHADOW` 重新验证）。

## 本阶段状态计数
`{json.dumps(state['lifecycle_counts'], ensure_ascii=False)}`

## 接入 Historical Strategy Decay Lab（Section 七）
已消费（未重跑）`V2_HISTORICAL_STRATEGY_DECAY_LAB`：
- 真实含交易系统：{d.get('real_trade_systems')}
- V1_OLD: {d.get('V1_OLD')}
- V1_NEW: {d.get('V1_NEW')}
- 该 lab 结论：证据不足；fresh-start/decay/reset/48h 均 INCONCLUSIVE / NOT_ESTABLISHED。

持续记录 system_age / strategy_age / regime_age / performance_age / confidence_age，
监测 Birth/Early/Stable/Degradation/Exhaustion/Recovery/Retirement。
**不预设衰竭时间，由数据识别**（本阶段样本不足以识别，如实标注）。
"""


def failure_report(state):
    f = state["memory_failure"]
    lines = ["# FAILURE_ANALYSIS", "",
             "失败分类：DIRECTION_ERROR / TIMING_ERROR / REGIME_ERROR / RISK_ERROR / COST_ERROR / "
             "DATA_ERROR / EXECUTION_ERROR / OPPORTUNITY_ERROR / NO_IDENTIFIABLE_ERROR。", "",
             f"strategy_memory 记录数：{f['records']}", "", "`strategy × failure_type` 计数：", "```",
             json.dumps(f["failure_counts"], ensure_ascii=False, indent=2), "```"]
    return "\n".join(lines)


def multi_report(state):
    p = state["portfolio"]
    lines = ["# MULTI_STRATEGY_REPORT", "",
             "组合层：Single / EqualWeight / ConfidenceWeight / RegimeWeight / DiversityWeight（权重只用 discovery 固定，OOS 严格）。",
             "", "## 相关性检查（是否都在赌同一风险因子）", "```",
             json.dumps({k: p.get(k) for k in
                         ["n_strategies_with_trades", "corr_mean_offdiag", "corr_max_offdiag",
                          "same_factor_flag"]}, ensure_ascii=False, indent=2), "```", "",
             "## 组合结果 (OOS)", "```",
             json.dumps({k: p.get(k) for k in
                         ["single_best_discovery", "single_best_oos_total", "equal_weight_oos_total",
                          "confidence_weight_oos_total"]}, ensure_ascii=False, indent=2), "```"]
    return "\n".join(lines)


def oos_report(state):
    lines = ["# OOS_REPORT", "",
             "Untouched OOS = " + str(state["splits"]["oos"]) + "，在 discovery 选择与 validation 之前未参与任何选择。", "",
             "## 工厂候选 OOS", "| strategy_id | oos_n | oos_expectancy | oos_precision | oos_total |",
             "|---|---|---|---|---|"]
    for s in state["specs"]:
        o = state["results"][s.strategy_id]["splits"]["oos"]
        lines.append(f"| {s.strategy_id} | {o['n_eff']} | {_f(o['expectancy'])} | {_f(o['precision'])} | {_f(o['total'])} |")
    lines += ["", "## 简单基准 OOS（Section 十）", "| baseline | n | expectancy | total |", "|---|---|---|---|"]
    for name, per in state["baselines"].items():
        o = per["oos"]
        lines.append(f"| {name} | {o['n_eff']} | {_f(o['expectancy'])} | {_f(o['total'])} |")
    lines += ["", "## GPU 搜索 top 组合 OOS（前 15）", "| fast | slow | thr | sign | val_exp | oos_n | oos_exp |",
              "|---|---|---|---|---|---|---|"]
    for _, r in state["gpu_search"]["selected"].head(15).iterrows():
        lines.append(f"| {int(r.fast)} | {int(r.slow)} | {r.thr} | {int(r.sign)} | {_f(r.val_exp)} | {int(r.oos_n)} | {_f(r.oos_exp)} |")
    return "\n".join(lines)


def statistical_report(state):
    lines = ["# STATISTICAL_EVIDENCE", "",
             "bootstrap(block) 95% CI + permutation p + BH-FDR(q=0.05)，全部在 discovery 上进行，再以 OOS 复核。", "",
             "| strategy_id | n_eff | mean | CI_lo | CI_hi | perm_p | FDR_pass |",
             "|---|---|---|---|---|---|---|"]
    for s in state["specs"]:
        r = state["results"][s.strategy_id]
        b, p = r["bootstrap"], r["permutation"]
        lines.append(f"| {s.strategy_id} | {r['splits']['discovery']['n_eff']} | {_f(b['mean'])} | "
                     f"{_f(b['lo'])} | {_f(b['hi'])} | {_f(p['p'])} | {'Y' if r['fdr_pass'] else 'n'} |")
    lines += ["", f"FDR 通过数：{sum(1 for s in state['specs'] if state['results'][s.strategy_id]['fdr_pass'])} / {len(state['specs'])}",
              "", "**结论**：样本跨度小、重叠持仓使独立样本有限，绝大多数统计量不显著 → 见 FINAL_REPORT 的诚实收口。"]
    return "\n".join(lines)


def stability_report(state):
    lines = ["# STABILITY_REPORT", "",
             "| strategy_id | disc_stab | val_stab | oos_stab | 2x_cost_robust |",
             "|---|---|---|---|---|"]
    for s in state["specs"]:
        r = state["results"][s.strategy_id]["splits"]
        lines.append(f"| {s.strategy_id} | {_f(r['discovery']['stability'])} | {_f(r['validation']['stability'])} | "
                     f"{_f(r['oos']['stability'])} | {state['results'][s.strategy_id]['cost_robust_2x']} |")
    return "\n".join(lines)


def replay_report(state):
    r = state["replay"]
    f = state["exp_F"]
    lines = ["# REPLAY_REPORT", "",
             "历史回放（Section 二十一）：用 V1_OLD / V1_NEW 可验证历史重放 Factory/Brain 机制。",
             "**历史只用于 architecture/replay/mechanism 研究，绝不当未来训练标签。**", "",
             "## V1 真实成交（来自券商事实库）", "```",
             json.dumps(r, ensure_ascii=False, indent=2), "```", "",
             "## V1 Capture Replication (Experiment F)", "```",
             json.dumps(f, ensure_ascii=False, indent=2), "```"]
    return "\n".join(lines)


def v1_capture_report(state):
    return "# V1_CAPTURE_REPLICATION\n\n" + json.dumps(state["exp_F"], ensure_ascii=False, indent=2) + "\n"


def alpha_report(state):
    lines = ["# ALPHA_DISCOVERY_REPORT", "",
             f"GPU 搜索 {state['gpu_search']['searched_hypotheses']} 条假设；"
             f"样本足够 {state['gpu_search']['eligible']}；选取 top {state['gpu_search']['selected_top_k']}。",
             "Discovery → Validation → Untouched OOS，记录搜索空间与拒绝原因。", "",
             "## 通过三者（disc/val/oos 均正）的机制数",
             f"- 手工机制族：{state['exp_E']['manual_stable']} / {state['exp_E']['manual_mechanism_candidates']}",
             f"- GPU 大规模搜索：{state['exp_E']['gpu_stable_after_validation_and_oos']} / {state['exp_E']['gpu_selected']}",
             "",
             f"结论：{state['exp_E']['verdict']}。样本不足以确证稳定短周期 alpha（见 FINAL_REPORT）。"]
    return "\n".join(lines)


def _f(x, nd=4):
    try:
        if x is None or (isinstance(x, float) and not np.isfinite(x)):
            return "nan"
        return f"{float(x):.{nd}f}"
    except Exception:
        return str(x)


def dashboard_html(state):
    g = state["gpu"]
    exp = state["experiments"]
    hub = state["hub"]["concentration"]
    lc = state["lifecycle_counts"]
    def bar(counts, total):
        total = total or 1
        return "".join(
            f'<div class="row"><span>{k}</span><div class="bar"><i style="width:{v/total*100:.0f}%"></i></div><b>{v}</b></div>'
            for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))
    regime_counts = state.get("regime_counts", {})
    perf_rows = "".join(
        f"<tr><td>{s.strategy_id}</td><td>{s.mechanism}</td>"
        f"<td>{_f(state['results'][s.strategy_id]['splits']['oos']['expectancy'])}</td>"
        f"<td>{state['results'][s.strategy_id]['splits']['oos']['n_eff']}</td>"
        f"<td>{'Y' if state['results'][s.strategy_id]['fdr_pass'] else 'n'}</td></tr>"
        for s in state["specs"])
    evo_rows = "".join(
        f"<tr><td>{sid}</td><td>{v['state']}</td><td>{', '.join(v['triggers']) or '—'}</td></tr>"
        for sid, v in list(state["evolution"]["states"].items()))
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>V2 Grand Architecture · Research Dashboard</title>
<style>
body{{font-family:system-ui,'Microsoft YaHei',sans-serif;margin:0;background:#0f1218;color:#e8eef7}}
header{{padding:18px 24px;background:#161b25;border-bottom:1px solid #233}}
h1{{font-size:18px;margin:0}} .sub{{color:#8fa3bf;font-size:12px;margin-top:4px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px;padding:16px 24px}}
.card{{background:#161b25;border:1px solid #223;border-radius:10px;padding:14px 16px}}
.card h2{{font-size:13px;margin:0 0 10px;color:#9db4d6;letter-spacing:.5px;text-transform:uppercase}}
.row{{display:flex;align-items:center;gap:8px;font-size:12px;margin:4px 0}}
.row span{{width:120px;color:#b9c9e0}} .bar{{flex:1;background:#0c0f15;border-radius:4px;height:10px;overflow:hidden}}
.bar i{{display:block;height:100%;background:linear-gradient(90deg,#2f81f7,#39d353)}}
.row b{{width:36px;text-align:right;color:#e8eef7}}
table{{width:100%;border-collapse:collapse;font-size:12px}} td,th{{padding:4px 6px;border-bottom:1px solid #202836;text-align:left}}
th{{color:#8fa3bf}} .k{{color:#39d353}} .w{{color:#f0a35e}} .bad{{color:#f85149}}
.tag{{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;background:#1f2937;color:#9db4d6;margin:2px}}
</style></head><body>
<header><h1>V2 多策略智能交易系统 · Research Dashboard</h1>
<div class="sub">只读 / Shadow 研究面板 · 不接口生产 · commit {state['commit'][:10]} · dataset {state['dataset_hash'][:12]} · seed {state['seed']}</div></header>
<div class="grid">
<div class="card"><h2>策略总数与生命周期</h2><div class="row"><span>候选总数</span><b>{len(state['specs'])}</b></div>
{bar(lc, len(state['specs']))}</div>
<div class="card"><h2>Market Regime 分布</h2>{bar(regime_counts, sum(regime_counts.values()) or 1)}</div>
<div class="card"><h2>策略一致 / 冲突</h2>
<div class="row"><span>AGREEMENT</span><b>{state['brain']['conflict_counts'].get('oos', {}).get('AGREEMENT', 0)}</b></div>
<div class="row"><span>CONFLICT</span><b>{state['brain']['conflict_counts'].get('oos', {}).get('CONFLICT', 0)}</b></div>
<div class="row"><span>ABSENT</span><b>{state['brain']['conflict_counts'].get('oos', {}).get('ABSENT', 0)}</b></div>
<div class="row"><span>DATA_GAP</span><b>{state['brain']['conflict_counts'].get('oos', {}).get('DATA_GAP', 0)}</b></div></div>
<div class="card"><h2>Opportunity Concentration</h2>
<div class="row"><span>来源数</span><b>{len(hub['source_used'])}</b></div>
<div class="row"><span>最大份额</span><b>{hub['max_share']:.2f}</b></div>
<div>{''.join(f'<span class="tag">{k}:{v}</span>' for k,v in hub['counts'].items())}</div></div>
<div class="card"><h2>GPU 状态</h2>
<div class="row"><span>设备</span><b>{g.get('gpu',{}).get('device')}</b></div>
<div class="row"><span>research</span><b class="k">{g.get('GPU_RESEARCH')}</b></div>
<div class="row"><span>speedup</span><b>{g.get('speedup')}×</b></div>
<div class="row"><span>peak VRAM</span><b>{g.get('peak_vram_mb')}MB</b></div>
<div class="row"><span>util max</span><b>{g.get('gpu_utilization_pct',{}).get('max')}%</b></div>
<div class="row"><span>组合数</span><b>{g.get('n_combos')}</b></div></div>
<div class="card"><h2>Evolution 状态</h2>
<div class="row"><span>总证据</span><b class="w">{state['evolution_evidence']}</b></div>
{bar(state['evolution']['counts'], len(state['specs']))}</div>
<div class="card"><h2>大实验 A–F</h2>
{''.join(f'<div class="row"><span>Experiment {k}</span><b class="{"k" if exp[k].get("verdict")=="PASS" else "w"}">{exp[k].get("verdict")}</b></div>' for k in "ABCDEF")}</div>
<div class="card" style="grid-column:1/-1"><h2>近期性能 / 退化（Untouched OOS）</h2>
<table><tr><th>strategy_id</th><th>mechanism</th><th>oos_expectancy</th><th>oos_n</th><th>FDR</th></tr>{perf_rows}</table></div>
<div class="card" style="grid-column:1/-1"><h2>Evolution 明细</h2>
<table><tr><th>strategy_id</th><th>state</th><th>triggers</th></tr>{evo_rows}</table></div>
</div></body></html>"""


def write_dashboard(state):
    _w("RESEARCH_DASHBOARD.html", dashboard_html(state))


REPORT_MAP = {
    "ARCHITECTURE.md": architecture_md,
    "STRATEGY_FACTORY_REPORT.md": factory_report,
    "STRATEGY_COMPETITION.md": competition_report,
    "REGIME_STRATEGY_MATRIX.md": regime_matrix_report,
    "STRATEGY_BRAIN_REPORT.md": brain_report,
    "EVOLUTION_ENGINE_REPORT.md": evolution_report,
    "GPU_RESEARCH_REPORT.md": gpu_report,
    "STRATEGY_LIFECYCLE.md": lifecycle_report,
    "FAILURE_ANALYSIS.md": failure_report,
    "MULTI_STRATEGY_REPORT.md": multi_report,
    "OOS_REPORT.md": oos_report,
    "STATISTICAL_EVIDENCE.md": statistical_report,
    "STABILITY_REPORT.md": stability_report,
    "REPLAY_REPORT.md": replay_report,
    "V1_CAPTURE_REPLICATION.md": v1_capture_report,
    "ALPHA_DISCOVERY_REPORT.md": alpha_report,
}


def write_all_reports(state):
    for name, fn in REPORT_MAP.items():
        _w(name, fn(state))


def write_registries(state):
    # STRATEGY_REGISTRY.jsonl
    reg_path = os.path.join(ROOT, "STRATEGY_REGISTRY.jsonl")
    with open(reg_path, "w", encoding="utf-8") as fh:
        for sid in sorted(state["registry_records"]):
            fh.write(json.dumps(state["registry_records"][sid], ensure_ascii=False) + "\n")
    # CANDIDATE_REGISTRY.jsonl
    cpath = os.path.join(ROOT, "CANDIDATE_REGISTRY.jsonl")
    with open(cpath, "w", encoding="utf-8") as fh:
        for c in state["candidates"]:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    # EXPERIMENT_REGISTRY.jsonl
    epath = os.path.join(ROOT, "EXPERIMENT_REGISTRY.jsonl")
    with open(epath, "w", encoding="utf-8") as fh:
        for k in ("A", "B", "C", "D", "E", "F"):
            e = dict(state["experiments"][k])
            e["experiment"] = k
            e["code_commit"] = state["commit"]
            e["input_hash"] = state["dataset_hash"]
            e["seed"] = state["seed"]
            e["config_hash"] = hashing.sha256_json(e)
            fh.write(json.dumps(e, ensure_ascii=False, default=str) + "\n")
    # GPU_BENCHMARK.json
    _w("GPU_BENCHMARK.json", json.dumps(state["gpu"], ensure_ascii=False, indent=2, default=str))
    # DATA_MANIFEST.json
    _w("DATA_MANIFEST.json", json.dumps(state["data_manifest"], ensure_ascii=False, indent=2, default=str))


def final_report(state):
    exp = state["experiments"]
    auth = state["intelligence"]
    lines = ["# FINAL_REPORT", "",
             f"code_commit `{state['commit']}` · dataset_hash `{state['dataset_hash'][:16]}…` · seed `{state['seed']}`",
             f"branch `research/v2-grand-architecture`", "",
             "## 交付目录", "",
             "模块：" + ", ".join(f"`{d}/`" for d in BUILD_ORDER), "",
             "报告：ARCHITECTURE / STRATEGY_LIFECYCLE / STRATEGY_COMPETITION / REGIME_STRATEGY_MATRIX / "
             "FAILURE_ANALYSIS / MULTI_STRATEGY_REPORT / STRATEGY_FACTORY_REPORT / STRATEGY_BRAIN_REPORT / "
             "EVOLUTION_ENGINE_REPORT / GPU_RESEARCH_REPORT / ALPHA_DISCOVERY_REPORT / V1_CAPTURE_REPLICATION / "
             "OOS_REPORT / STATISTICAL_EVIDENCE / STABILITY_REPORT / REPLAY_REPORT / FINAL_REPORT", "",
             "登记表：STRATEGY_REGISTRY.jsonl / CANDIDATE_REGISTRY.jsonl / EXPERIMENT_REGISTRY.jsonl / "
             "GPU_BENCHMARK.json / DATA_MANIFEST.json / SHA256SUMS.txt", "",
             "## 12 条验收回答", ""]
    for i, a in enumerate(state["acceptance"], 1):
        lines.append(f"{i}. {a}")
    lines += ["", "## 大实验 A–F 结论", ""]
    for k in ("A", "B", "C", "D", "E", "F"):
        lines.append(f"- **{k}** `{exp[k].get('verdict')}`")
    lines += ["", "## 最终状态块", "", "```",
              "Production changes = 0",
              "order_send = 0",
              "V1 touched = 0",
              "V3 touched = 0",
              "V2 production behavior changed = 0",
              f"GPU research = {state['gpu'].get('GPU_RESEARCH', 'FAIL')}",
              f"Validated Alpha candidates = {len(state['candidates'])}",
              f"Evolution evidence = {state['evolution_evidence']}",
              "```", "",
              "## 核心问题", "",
              state["core_answer"]]
    return "\n".join(lines)
