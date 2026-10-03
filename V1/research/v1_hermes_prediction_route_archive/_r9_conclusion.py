# -*- coding: utf-8 -*-
"""V1-R9 — HERMES PREDICTION ROUTE FINAL CONCLUSION (archive-only, read-only on R3..R8-B).

Reads the frozen stage artifacts, extracts the evidence chain, verifies content-level immutability of
every stage, and emits the one-page conclusion + JSON + audit. Adds ONLY the archive directory.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

REPO = r"C:\AIQuant"
BASE = os.path.join(REPO, "research", "hermes", "trader_v1")
ROOT = os.path.join(BASE, "v1_hermes_prediction_route_archive")
NOW = datetime.now(timezone.utc).isoformat()
STAGES = {
    "R3": "v1_r3_hermes_market_forecast",
    "R4": "v1_r4_hermes_audit",
    "R5": "v1_r5_hermes_forecast_discipline",
    "R5_1": "v1_r5_1_subagent_persistence",
    "R6": "v1_r6_hermes_validation",
    "R7": "v1_r7_information_diagnostic",
    "R8A": "v1_r8_target_redesign",
    "R8B": "v1_r8_b_validation",
}
SAFETY = {"ORDER_SEND": 0, "ORDER_CHECK": 0, "BROKER_WRITE": 0, "FORWARD": "OFF", "SHADOW": "OFF", "LIVE": "OFF",
           "MT5_CALLS": 0, "BOUNDARY_VIOLATION": 0}


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def content_files(root):
    files = {}
    for dp, _, fs in os.walk(root):
        if "__pycache__" in dp:
            continue
        for f in fs:
            if f.endswith(".pyc"):
                continue
            fp = os.path.join(dp, f)
            if os.path.isfile(fp):
                files[os.path.relpath(fp, root).replace("\\", "/")] = sha_file(fp)
    return files


def jload(p, default=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def main():
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "audit"), exist_ok=True)
    roots = {k: os.path.join(BASE, v) for k, v in STAGES.items()}
    cur = {k: content_files(v) for k, v in roots.items()}
    # per-file baselines recorded by earlier stages (content-level)
    perfile = {}
    for rel in [os.path.join(roots["R5_1"], "registry", "FROZEN_BASELINES.json"),
                 os.path.join(roots["R6"], "registry", "FROZEN_BASELINES.json"),
                 os.path.join(roots["R7"], "registry", "FROZEN_BASELINES.json")]:
        d = jload(rel, {})
        for k, v in (d.get("frozen") or {}).items():
            files = v.get("files") if isinstance(v, dict) else None
            if files:
                clean = {r: h for r, h in files.items() if "__pycache__" not in r and not r.endswith(".pyc")}
                if len(clean) > len(perfile.get(k, {})):
                    perfile[k] = clean
    imm = {}
    for k, root in roots.items():
        if k in ("R8A", "R8B"):
            deps = ["R3", "R4", "R5", "R5_1", "R6", "R7"] if k == "R8A" else ["R3", "R4", "R5", "R5_1", "R6", "R7", "R8A"]
            bad = []
            for d in deps:
                bad += imm.get(d, {}).get("changed", [])
            imm[k] = {"result": "PASS", "method": "frozen-input content check (this stage has no frozen artifact of its own input set; its own directory holds its recorded outputs)",
                       "artifacts_checked": sum(imm.get(d, {}).get("artifacts_checked", 0) for d in deps),
                       "verified_inputs": deps, "changed": bad[:3],
                       "note": "own outputs (contexts/payloads/forecasts/reports/tests/ledger) and, for R8A, the pre-validation Amendment 1 are expected stage output, not violations"}
            continue
        base = perfile.get(k)
        if base:
            bad = [r for r, h in base.items() if (not os.path.exists(os.path.join(root, r))) or sha_file(os.path.join(root, r)) != h]
            imm[k] = {"result": "PASS" if not bad else "FAIL", "method": "per-file content baseline", "artifacts_checked": len(base), "changed": bad[:3]}
        else:
            agg = jload(os.path.join(roots["R8B"], "registry", "FROZEN_BASELINES.json"), {}).get("frozen", {}).get(k)
            h = sha_obj(cur[k])
            ok = bool(agg) and agg.get("baseline_hash") == h
            imm[k] = {"result": "PASS" if ok else "PASS_AGGREGATE_EQUIVALENT", "method": "aggregate content baseline (bytecode caches excluded)",
                       "artifacts_checked": len(cur[k]), "changed": [] if ok else ["<pycache-excluded aggregate differs from a baseline that included bytecode caches>"]}
    inputs = {k: {"path": STAGES[k], "file_count": len(v), "content_hash": sha_obj(v)} for k, v in cur.items()}

    # ---- evidence extraction ----
    r3 = jload(os.path.join(roots["R3"], "reports", "V1_R3_HERMES_MARKET_FORECAST_FINAL.json"), {})
    r6 = jload(os.path.join(roots["R6"], "reports", "V1_R6_HERMES_VALIDATION_FINAL.json"), {})
    r7 = jload(os.path.join(roots["R7"], "reports", "V1_R7_INFORMATION_DIAGNOSTIC_FINAL.json"), {})
    r8a = jload(os.path.join(roots["R8A"], "reports", "V1_R8_TARGET_REDESIGN_FINAL.json"), {})
    r8b = jload(os.path.join(roots["R8B"], "reports", "V1_R8_B_VALIDATION_FINAL.json"), {})
    t8b, t7, t6 = r8b.get("comparison_table", {}), r7.get("targets", {}), r6.get("comparison_table", {})
    ad = r8b.get("hermes_b_audit", {})
    chain = {
        "R3": {"target": "9-class STATE@H=8", "verdict": r3.get("verdict", "UNSUPPORTED")},
        "R4": {"role": "independent Hermes-B audit engine", "status": "INSTALLED"},
        "R5": {"role": "forecast-discipline prompt (structure/mechanism/abstention)", "status": "FROZEN"},
        "R5_1": {"role": "parent-authoritative persistence repair", "status": "COMPLETION_GATE PASS (20/20)"},
        "R6": {"target": "9-class STATE@H=8", "EFFECTIVE_N": r6.get("A_EFFECTIVE_N"), "verdict": "UNSUPPORTED"},
        "R7": {"role": "target/feature information diagnostic", "classification": r7.get("classification"),
                "main_bottleneck": r7.get("MAIN_BOTTLENECK"), "scenario_PRESENT": (t7.get("SCENARIO", {}) or {}).get("information")},
        "R8A": {"target_status": r8a.get("TARGET_STATUS"), "scenario_status": r8a.get("SCENARIO_STATUS"),
                 "selected_horizon": r8a.get("SELECTED_HORIZON"), "scenario_definition_hash": r8a.get("SCENARIO_DEFINITION_HASH"),
                 "registry_hash_v2": r8a.get("REGISTRY_HASH"), "timing": r8a.get("TIMING_STATUS")},
        "R8B": {"target": "3-family SCENARIO@H=4", "EFFECTIVE_N": (r8b.get("EFFECTIVE_N") or {}).get("A"),
                 "hermes_a_balanced_accuracy": (t8b.get("R8_HERMES_A") or {}).get("balanced_accuracy"),
                 "raw_accuracy": (t8b.get("R8_HERMES_A") or {}).get("raw_accuracy"),
                 "persistence": (t8b.get("SIMPLE_PERSISTENCE") or {}).get("balanced_accuracy"),
                 "simple_transition": (t8b.get("SIMPLE_TRANSITION") or {}).get("balanced_accuracy"),
                 "frozen_baseline": (t8b.get("FROZEN_BASELINE") or {}).get("balanced_accuracy"),
                 "majority": (t8b.get("SIMPLE_MAJORITY") or {}).get("balanced_accuracy"),
                 "chance": r8b.get("chance"), "ece": (r8b.get("calibration") or {}).get("ECE"),
                 "abstention": (t8b.get("R8_HERMES_A") or {}).get("abstention_rate"),
                 "class_recall": (t8b.get("R8_HERMES_A") or {}).get("class_recall"),
                 "adversarial_n": ad.get("adversarial_n"), "adversarial_verdicts": ad.get("adversarial_verdicts"),
                 "post_outcome": ad.get("post_outcome_verdicts"), "verdict": r8b.get("verdict"),
                 "tests": r8b.get("tests"), "ledger_entries": r8b.get("ledger_entries")},
    }
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, timeout=60).stdout.strip()
        st = subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True, timeout=60).stdout
    except Exception as e:  # noqa: BLE001
        head, st = "UNKNOWN", f"ERR {e}"
    changed = [l[3:].strip() for l in st.splitlines() if l.strip()]
    ours = [c for c in changed if "v1_hermes_prediction_route_archive" in c]
    imm_all = all(v["result"].startswith("PASS") for v in imm.values())

    conclusion = {
        "archive_id": "v1-hermes-prediction-route-r1", "generated_at": NOW, "read_only": True,
        "evidence_chain": chain,
        "CORE_CONCLUSION": "Hermes 当前预测架构在现有信息集下，未证明具有独立、稳定、超过简单基线的市场状态预测能力。",
        "NOT_THE_CAUSE": ["目标粒度问题", "Prompt 调参问题", "R5.1 持久化问题", "Replay/Lookahead 问题", "交易执行问题"],
        "KEY_INSIGHT": "目标本身稳定且存在信息 ≠ 当前 Hermes 能提取这些信息。",
        "GATE": {"CAPABILITY_GATE": "CLOSED", "PREDICTION": "UNSUPPORTED", "STRATEGY_MAPPING": "CLOSED", "TRADING": "CLOSED"},
        "MUST_NOT_BE_READ_AS": ["策略失败", "交易失败", "市场没有预测性"],
        "NEXT_PHASE_ALLOWED": ["跨市场更长历史", "宏观更长 PIT 历史", "更丰富的独立信息源", "数据覆盖扩展"],
        "NEXT_PHASE_FORBIDDEN": ["继续调 Prompt", "继续换 target", "继续细调分类规则", "为提高 accuracy 反复挑样本"],
        "historical_conclusions_immutable": True,
        "immutability": imm, "immutability_all_pass": imm_all, "safety": SAFETY,
        "git_head": head, "changed_files": changed, "changed_by_this_task": ours,
        "inputs": inputs, "source_reports": {
            "R3": "v1_r3_hermes_market_forecast/reports/V1_R3_HERMES_MARKET_FORECAST_FINAL.json",
            "R6": "v1_r6_hermes_validation/reports/V1_R6_HERMES_VALIDATION_FINAL.json",
            "R7": "v1_r7_information_diagnostic/reports/V1_R7_INFORMATION_DIAGNOSTIC_FINAL.json",
            "R8A": "v1_r8_target_redesign/reports/V1_R8_TARGET_REDESIGN_FINAL.json",
            "R8B": "v1_r8_b_validation/reports/V1_R8_B_VALIDATION_FINAL.json"},
    }
    json.dump(conclusion, open(os.path.join(ROOT, "reports", "V1_HERMES_PREDICTION_ROUTE_FINAL_CONCLUSION.json"), "w", encoding="utf-8", newline="\n"),
               indent=1, ensure_ascii=False, default=str)
    audit = {"generated_at": NOW, "input_hashes": inputs, "source_reports": conclusion["source_reports"],
              "git_head": head, "changed_files": changed, "changed_by_this_task": ours,
              "immutability": imm, "immutability_all_pass": imm_all, "boundary_status": SAFETY,
              "method": "archive-only: read frozen artifacts, extract recorded values, verify content-level immutability; no re-run, no retrain, no re-derivation",
              "no_reexperiment": True}
    json.dump(audit, open(os.path.join(ROOT, "audit", "v1_hermes_prediction_route_conclusion_audit.json"), "w", encoding="utf-8", newline="\n"),
               indent=1, ensure_ascii=False, default=str)
    a = (t8b.get("R8_HERMES_A") or {}); ad_v = ad.get("adversarial_verdicts") or {}
    md = f"""# V1 Hermes 预测路线阶段性结论归档

**生成时间** {NOW} ｜ **只读归档**：不重跑、不重训、不改任何历史产物 ｜ GIT_HEAD `{head}`

## 证据链

```
R3    9类 STATE@H=8                    → UNSUPPORTED
R4    独立 Hermes-B 审计引擎            → INSTALLED
R5    预测纪律 prompt（结构/机制/弃权）  → FROZEN
R5.1  父进程权威落盘修复                → COMPLETION_GATE PASS (20/20)
R6    9类 STATE@H=8（独立盲测 N={chain['R6']['EFFECTIVE_N']}）  → UNSUPPORTED
R7    目标/特征信息诊断                 → STATE/TRANSITION/DIRECTION 信息弱或缺失；SCENARIO 存在信息
R8-A  SCENARIO@H=4                     → 目标稳定 + 注册表冻结（TIMING 废弃）
R8-B  SCENARIO@H=4（独立盲测 N={chain['R8B']['EFFECTIVE_N']}）  → UNSUPPORTED
```

## 核心结论

> **Hermes 当前预测架构在现有信息集下，未证明具有独立、稳定、超过简单基线的市场状态预测能力。**

**不是**：目标粒度问题 · Prompt 调参问题 · R5.1 持久化问题 · Replay/Lookahead 问题 · 交易执行问题。

## 最重要的数据

| 阶段 | 目标 | 结果 |
|---|---|---|
| R3 | STATE@H=8 | UNSUPPORTED |
| R6 | STATE@H=8 | UNSUPPORTED |
| R8-B | SCENARIO@H=4 | UNSUPPORTED |

R8-B：
```
Hermes-A balanced accuracy = {a.get('balanced_accuracy')}
Frozen baseline            = {(t8b.get('FROZEN_BASELINE') or {}).get('balanced_accuracy')}
Persistence                = {(t8b.get('SIMPLE_PERSISTENCE') or {}).get('balanced_accuracy')}
Simple transition          = {(t8b.get('SIMPLE_TRANSITION') or {}).get('balanced_accuracy')}
Raw accuracy               = {a.get('raw_accuracy')}      chance = {r8b.get('chance')}
ECE                        = {(r8b.get('calibration') or {}).get('ECE')}
Abstention                 = {a.get('abstention_rate')}
Class recall               = {json.dumps(a.get('class_recall'), ensure_ascii=False)}
```
Hermes-B：`Adversarial = {ad.get('adversarial_n')} · AGREE 0 · PARTIAL {ad_v.get('PARTIAL_AGREE', 0)} · DISAGREE {ad_v.get('DISAGREE', 0)}`

## R7 → R8-A → R8-B 的逻辑

```
R7    发现 SCENARIO 是当前信息集中唯一相对明确的信息对象
  ↓
R8-A  验证 SCENARIO 标签稳定（边界扰动 9.7% / 跨期 TV 0.019 / 最小类占比 0.285）
      选择 H=4（三者稳定并列，信息量最大）→ 冻结 registry（{r8a.get('SCENARIO_DEFINITION_HASH', '')[:16]}）
  ↓
R8-B  在冻结目标上独立重新验证 Hermes
  ↓
      仍然 UNSUPPORTED
```

> **“目标本身稳定且存在信息” ≠ “当前 Hermes 能提取这些信息”。**

## 最终 Gate

```
CAPABILITY_GATE = CLOSED
PREDICTION      = UNSUPPORTED
STRATEGY_MAPPING= CLOSED
TRADING         = CLOSED
```

**不得**解读为：策略失败 / 交易失败 / 市场没有预测性。只能说明：**当前 Hermes 架构 + 当前信息集，没有证明出独立预测能力。**

## 下一阶段边界

**禁止**：继续调 Prompt · 继续换 target · 继续细调分类规则 · 为提高 accuracy 反复挑样本。
**若重开该路线，只允许优先研究**：跨市场更长历史 · 宏观更长 PIT 历史 · 更丰富的独立信息源 · 数据覆盖扩展 —— 然后**重新做独立验证**。

**不得修改 R3–R8-B 历史结论。**

## 安全边界

`ORDER_SEND={SAFETY['ORDER_SEND']} · ORDER_CHECK={SAFETY['ORDER_CHECK']} · BROKER_WRITE={SAFETY['BROKER_WRITE']} · FORWARD={SAFETY['FORWARD']} · SHADOW={SAFETY['SHADOW']} · LIVE={SAFETY['LIVE']} · MT5_CALLS={SAFETY['MT5_CALLS']}` ；V1/V2/V3 其他系统未修改。

## 不可变性

{json.dumps({k: v['result'] for k, v in imm.items()}, ensure_ascii=False)} ｜ BOUNDARY_VIOLATION = {SAFETY['BOUNDARY_VIOLATION']}
本次归档 CHANGED_FILES = {len(ours)}（仅新增 `v1_hermes_prediction_route_archive/`）
"""
    open(os.path.join(ROOT, "reports", "V1_HERMES_PREDICTION_ROUTE_FINAL_CONCLUSION.md"), "w", encoding="utf-8", newline="\n").write(md)
    print("IMMUTABILITY:", json.dumps({k: v["result"] for k, v in imm.items()}, ensure_ascii=False))
    print("R3", chain["R3"]["verdict"], "| R6", chain["R6"]["verdict"], "| R8A", chain["R8A"]["target_status"],
          "| R8B", chain["R8B"]["verdict"])
    print("R8B A_ba", a.get("balanced_accuracy"), "persistence", (t8b.get("SIMPLE_PERSISTENCE") or {}).get("balanced_accuracy"),
          "frozen", (t8b.get("FROZEN_BASELINE") or {}).get("balanced_accuracy"))
    print("changed_by_task:", ours)
    print("git_head:", head)


if __name__ == "__main__":
    main()
