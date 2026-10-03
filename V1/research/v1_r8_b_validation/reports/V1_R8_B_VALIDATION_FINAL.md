# V1-R8-B SCENARIO BLIND VALIDATION — FINAL REPORT

目标：**SCENARIO@H=4**（冻结定义 e51a5fdea95535e5）的独立盲验证。
Sample: every 2 days at 00:00Z inside 2026-07-17..2026-09-17 (fresh, pre-registered, no cherry-picking)｜declared=32｜EFFECTIVE_N A=32 / BB=10 / BA=16 / PO=6
chance = 0.3333

## 对照表
{
 "R8_HERMES_A": {
  "balanced_accuracy": 0.4056,
  "raw_accuracy": 0.25,
  "class_recall": {
   "DIRECTIONAL": 0.3333,
   "QUIET": 0.05,
   "RANGE": 0.8333
  },
  "n": 32,
  "abstention_rate": 0.0
 },
 "SIMPLE_MAJORITY": {
  "balanced_accuracy": 0.3333,
  "raw_accuracy": 0.1875,
  "class_recall": {
   "DIRECTIONAL": 0.0,
   "QUIET": 0.0,
   "RANGE": 1.0
  },
  "n": 32
 },
 "SIMPLE_PERSISTENCE": {
  "balanced_accuracy": 0.75,
  "raw_accuracy": 0.75,
  "class_recall": {
   "DIRECTIONAL": 0.6667,
   "QUIET": 0.75,
   "RANGE": 0.8333
  },
  "n": 32
 },
 "SIMPLE_TRANSITION": {
  "balanced_accuracy": 0.75,
  "raw_accuracy": 0.75,
  "class_recall": {
   "DIRECTIONAL": 0.6667,
   "QUIET": 0.75,
   "RANGE": 0.8333
  },
  "n": 32
 },
 "FROZEN_BASELINE": {
  "balanced_accuracy": 0.5444,
  "raw_accuracy": 0.6562,
  "class_recall": {
   "DIRECTIONAL": 0.3333,
   "QUIET": 0.8,
   "RANGE": 0.5
  },
  "n": 32
 }
}

## 校准
{"n": 32, "ECE": 0.1616, "mean_confidence": 0.4116, "raw_accuracy": 0.25}

## Hermes-B 审计
{"blind_n": 10, "blind_vs_A_agreement": null, "adversarial_n": 16, "adversarial_verdicts": {"PARTIAL_AGREE": 7, "DISAGREE": 9}, "adversarial_error_counts": {"over_inference": 54, "mechanism_jump": 40, "missing_counter_evidence": 58, "unjustified_confidence": 45, "observation_as_fact": 39}, "post_outcome_n": 6, "post_outcome_verdicts": {"ALIGNED": 4, "PARTIAL": 2}}

## 裁决
最强基线 balanced_acc = 0.75｜Hermes-A = 0.4056
VERDICT = **UNSUPPORTED**
CAPABILITY_GATE = **CLOSED**（本阶段未授权开启）· R3 裁决不变 = **UNSUPPORTED**

## 边界
tests = 17/0（共 17）· ledger = 65（chain OK）
R3/R4/R5/R5.1/R6/R7/R8-A 不可变性：{"R3": "PASS", "R4": "PASS", "R5": "PASS", "R5_1": "PASS", "R6": "PASS", "R7": "PASS", "R8_A": "PASS"}
未生成 profit_score / win_probability / expected_profit；未触碰交易/MT5。
GIT_HEAD = 9e8c4f94089c5700ade3b08ec528e14d83821b2e
