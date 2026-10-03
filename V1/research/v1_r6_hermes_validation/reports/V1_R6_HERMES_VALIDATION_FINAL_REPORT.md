# V1-R6 HERMES VALIDATION — FINAL REPORT

## 目标
用 **R5 冻结 prompt + R5.1 修复后的落盘链路**，在**预注册 ≥30 点盲集**上独立复验 Hermes 预测能力。允许 INCONCLUSIVE，不追求好看数字。

## 覆盖（诚实）
声明样本 **31** 点（固定规则：2026-07-18..09-16 每 2 天 12:00Z，未挑样本）。
Hermes-A 落盘 **30** 点（EFFECTIVE_N=30）；Hermes-B 对抗 15 点；Hermes-B 盲审 15 点。
R5 prompt 与冻结版本逐字节一致：**True**。

## 对照表（同一批点）
{"R6_HERMES_A": {"STATE_acc": 0.1667, "n_state": 24, "MAJORITY_ref": "REJECTION", "TRANSITION_acc": 0.4583, "DIRECTION_acc": 0.2381, "ABSTENTION_rate": 0.2, "SCENARIO_COVERAGE": 0.7333}, "SIMPLE_MAJORITY_ref": {"state": "REJECTION"}, "SIMPLE_PERSISTENCE": {"STATE_acc": 0.375, "n_state": 24, "MAJORITY_ref": "REJECTION", "TRANSITION_acc": null, "DIRECTION_acc": null, "ABSTENTION_rate": 0.0, "SCENARIO_COVERAGE": null}, "SIMPLE_PREVIOUS_STATE": {"STATE_acc": 0.4583, "n_state": 24, "MAJORITY_ref": "REJECTION", "TRANSITION_acc": null, "DIRECTION_acc": null, "ABSTENTION_rate": 0.0, "SCENARIO_COVERAGE": null}, "SIMPLE_TRANSITION": {"STATE_acc": 0.25, "n_state": 24, "MAJORITY_ref": "REJECTION", "TRANSITION_acc": null, "DIRECTION_acc": null, "ABSTENTION_rate": 0.0, "SCENARIO_COVERAGE": null}, "FROZEN_NEXT_STATE_MODEL": {"STATE_acc": 0.2667, "n": 30}}

## 校准
{"n": 21, "ECE": 0.181, "mean_confidence": 0.3476, "direction_accuracy": 0.2381}

## R5 vs R6（配对点 n=6）
{"n_overlap": 6, "points": ["20260720", "20260726", "20260801", "20260807", "20260813", "20260912"], "R5_STATE_acc": 0.0, "R6_STATE_acc": 0.2, "R5_TRANSITION_acc": 0.25, "R6_TRANSITION_acc": 0.4, "R5_SCENARIO_COVERAGE": 0.8333, "R6_SCENARIO_COVERAGE": 0.8333, "R5_ABSTENTION": 0.3333, "R6_ABSTENTION": 0.1667}

## Hermes-B 审计
{"n": 15, "verdicts": {"PARTIAL_AGREE": 11, "DISAGREE": 4}, "agreement_rate": 0.0, "partial_rate": 0.7333, "disagreement_rate": 0.2667, "insufficient_rate": 0.0, "focus": {"OBSERVATION_DISCIPLINE": {"PARTIAL_AGREE": 14, "DISAGREE": 1}, "MECHANISM_DISCIPLINE": {"PARTIAL_AGREE": 9, "DISAGREE": 3, "AGREE": 3}, "COUNTER_EVIDENCE": {"PARTIAL_AGREE": 13, "DISAGREE": 1, "AGREE": 1}, "CONFIDENCE": {"AGREE": 1, "PARTIAL_AGREE": 10, "DISAGREE": 4}, "ABSTENTION": {"AGREE": 4, "PARTIAL_AGREE": 6, "DISAGREE": 5}, "INVALIDATION": {"PARTIAL_AGREE": 10, "DISAGREE": 3, "AGREE": 2}}, "error_counts": {"over_inference": 46, "mechanism_jump": 35, "missing_counter_evidence": 57, "unjustified_confidence": 39, "observation_as_fact": 36}, "blind_vs_A_direction_pairs": 9, "blind_vs_A_direction_agreement": 0.8889, "blind_n": 15}

## 能力裁决（允许 INCONCLUSIVE）
{"STATE": "UNSUPPORTED", "TRANSITION": "UNSUPPORTED", "SCENARIO": "SUPPORTED", "DIRECTION": "UNSUPPORTED", "TIMING": "INCONCLUSIVE"}
基线最强 STATE_acc = 0.4583

## 结论
CAPABILITY_GATE = **CLOSED** · PREDICTION = **UNSUPPORTED**
R3 裁决不变 = **UNSUPPORTED**
R6 完成 ≠ 可交易：**交易保持关闭**。
tests = 16/0 · ledger = 76 · chain_ok = True
R3/R4/R5/R5.1 immutability = {"R3": true, "R4": true, "R5": true, "R5_1": true}
GIT_HEAD = 9e8c4f94089c5700ade3b08ec528e14d83821b2e
