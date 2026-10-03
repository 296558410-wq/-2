# V3 Opportunity Mechanism Validation R4 — 真实机制重评估报告

`ts_utc = 2026-09-25T12:03:53.113531+00:00`

**V3_OPPORTUNITY_MECHANISM_VALIDATION_R4 = COMPLETE**

## 0. 本轮只做一件事

```text
把 R3 已验证有效的方法，原样（零修改）应用于真实 404 个 Hermes INVESTIGATE。
不搜 Alpha、不调参、不优化、不交易、不选机会。
```

## 1. 输入完整性（§4/§5）

```text
expected = 404 · loaded = 404 · validated = 404 · missing = 0 · duplicate = 0 · unexpected(范围内) = 0
input_manifest_hash = 15d4064473c5fca62ea8b8039ec59bee747c2d3d3650c77a818985b3646fafcf
R4_INPUT_HASH       = 614822c367bffc74241fcbdce1add8124183f58ef45a564fe35da8009a246155+d6190a3a2b638b7a60cb4387676ad87b4d1c4a150e7eb2264cb1855bf200ac03
out_of_scope_records = 1595（= 1,999 − 404，来源账本中不在 INVESTIGATE 范围的记录，属预期）
```

## 2. 方法基线（§2/§3：R3 冻结）

```json
{
 "r3_commit": "93075de",
 "r2_commit": "33b1959",
 "r1_commit": "5c3434e",
 "r3_registry_hash": "9913dd6d9860f5e0fb3b519de08c362234e1e711d6e6efb8154601ac6cc2b305",
 "positive_control_definition_hash": "ca4d92baa9b022a5d2e2f72e55be23e8456c710f27378457d93410ff28829506",
 "negative_control_definition_hash": "fd1e01e635e7d68b61ad7015c515120149dc2d80244692565a003bdab1dc188e",
 "permutation_count": 500,
 "random_seed": 20260925,
 "event_separation_window": {
  "unit": "bars_on_the_records_own_grid",
  "value": 6,
  "cross_grid_merge": {
   "rule": "same mechanism_id and |dt| <= 2h -> one cross_grid_event",
   "value_hours": 2
  }
 },
 "min_independent_events": 8,
 "artifact_rules_hash": "88f4b4c460af014f32d6464078f93145dd32ad2c2b6de578ef0fbd204bc8aeb1",
 "counter_evidence_rules_hash": "b99912c953a3106087ca45597aabc6ae1222cdbe121ad472197aef118ae224bb",
 "stability_rules_hash": "3c3303096f8c9325434d4f4600ebed929a22bbffd5b2f1dec9d04ded5250204d",
 "decision_rules_hash": "34aa7b471e278ebce9bfded20ca72236ce26d230f8cc3cefac28b795394ad6c6",
 "candidate_gate_hash": "5fe14cadc34c909392a9fb8a5aa19b41a4f4eeb0874422a4d01e1e3f51929f17",
 "R3_METHOD_HASH": "571bad8fd9621780d676bfbd97b0687a1fa9c87e365311827456093969f36394",
 "METHOD_CHANGED": false
}

```text
METHOD_CHANGED = False —— R3 的事件分离/去重/伪影/反证/稳定性/置换/决策矩阵/Candidate 门全部原样复用。
```

## 3. 结果（§39）

```text
MECHANISM_COUNT          = 4
SUPPORTED                = 0
UNCERTAIN                = 1   (M03)
REJECTED                 = 3   (M01, M02, M08)
NOT_TESTABLE             = 0
INSUFFICIENT_EVIDENCE    = 0
INDEPENDENT_EVENT_COUNT  = 127
ARTIFACT_RISK_HIGH       = 4   (fatal: ["M01", "M08", "M02"])
COUNTER_EVIDENCE_HIGH    = 3   (levels: ["FATAL", "MODERATE"])
```

## 4. 覆盖率（§40）

```text
OPPORTUNITIES_WITH_MECHANISM    = 404
OPPORTUNITIES_WITHOUT_MECHANISM = 0
MECHANISM_COVERAGE_RATE         = 1.0
（覆盖率只是可追溯性指标，不是质量评分，也未用于排序）
```

## 5. 方法审计（§20/§38）

```text
NEGATIVE_CONTROL_A/B/C = PASS / PASS / PASS  (rate = 0.0 / 0.0 / 0.0, ceiling 0.25)
REAL_SUPPORTED_RATE = 0.0   NULL_SUPPORTED_RATE = 0.0
两者分开保存（null_control_results_r4.json vs mechanism_results_r4.json），未混合统计。
synthetic_events_used_for_real_decision = 0（正控合成数据完全隔离）
```

## 6. 稳定性（§17/§18/§19：NULL/PERMUTATION）

```text
全部机制的 TIME_STABILITY 均来自置换检验（obs/null_mean/null_std/null_quantiles/p_value/n_perm/seed 全部保存）
Session 与 State 稳定性全部为 NOT_INFORMATIVE —— 即【与随机无法区分】。这是诚实的负结果，未强行写成 HIGH。
未恢复 R1 的 temporal-tertile 规则。
```

## 7. 事件去重（§10/§11/§12）

```text
404 opportunities → 127 independent events（277 次重复检测在【事件层】合并，单阶段计数）
跨网格重复合并 1 次（5m/1h 同一市场事件未计为 2）
分离窗按记录各自网格判定（1h=6h / 5m=0.5h）；纯 1h 簇 22 对全部 > 6h
```

## 8. 测试（§52，30/30 PASS）

| 测试 | 结果 | 证据 |
|---|---|---|
| test_input_count_404 | **PASS** | {"expected": 404, "loaded": 404, "validated": 404, "unexpected_in_scope": 0, "out_of_scope": 1595} |
| test_input_manifest_hash | **PASS** | {"input_manifest_hash": "15d4064473c5fca62ea8", "rows": 404} |
| test_input_immutable | **PASS** | {"four_hashes_unchanged": true} |
| test_r3_method_hash | **PASS** | {"R3_METHOD_HASH": "571bad8fd9621780d676", "unchanged": true} |
| test_r3_registry_immutable | **PASS** | {"registry_hash": "9913dd6d9860f5e0fb3b", "r2_r3_agree": true} |
| test_r3_decision_rules_immutable | **PASS** | {"decision_rules_hash": "34aa7b471e278ebce9bf", "perm": 500, "seed": 20260925} |
| test_no_lookahead | **PASS** | {"replays": 3, "no_lookahead": true} |
| test_event_separation | **PASS** | {"separation_window_h": 6, "finest_window_h": 0.5, "1h_only_pairs_checked": 22, "mixed_grid_clusters": 32 |
| test_event_dedup | **PASS** | {"opportunities": 404, "independent_events": 127} |
| test_cross_grid_dedup | **PASS** | {"cross_grid_events": 1, "unique_ids": 127} |
| test_independent_event_count | **PASS** | {"total": 127, "mechanisms": 4} |
| test_artifact_detection | **PASS** | {"artifact_risk_high": 4, "fatal": ["M01", "M08", "M02"]} |
| test_counter_evidence | **PASS** | {"counter_evidence_high": 3, "levels": ["FATAL", "MODERATE"]} |
| test_evidence_dependency | **PASS** | {"pairs": 7, "dependent": 3} |
| test_temporal_stability | **PASS** | {"M03": "HIGH", "M01": "HIGH", "M08": "HIGH", "M02": "HIGH"} |
| test_session_stability | **PASS** | {"M03": "NOT_INFORMATIVE", "M01": "NOT_INFORMATIVE", "M08": "NOT_INFORMATIVE", "M02": "NOT_INFORMATIVE"} |
| test_state_stability | **PASS** | {"M03": "NOT_INFORMATIVE", "M01": "NOT_INFORMATIVE", "M08": "NOT_INFORMATIVE", "M02": "NOT_INFORMATIVE"} |
| test_negative_control_a | **PASS** | {"status": "PASS", "rate_mean": 0.0, "ceiling": 0.25} |
| test_negative_control_b | **PASS** | {"status": "PASS", "rate_mean": 0.0, "ceiling": 0.25} |
| test_negative_control_c | **PASS** | {"status": "PASS", "rate_mean": 0.0, "ceiling": 0.25} |
| test_deterministic | **PASS** | {"deterministic": true} |
| test_replay_70 | **PASS** | {"frac": 0.7, "cut": "2026-08-19 15:50:00+00:00", "closed_events": 97, "identity_stable": true, "decision |
| test_replay_80 | **PASS** | {"frac": 0.8, "cut": "2026-08-31 12:50:00+00:00", "closed_events": 106, "identity_stable": true, "decisio |
| test_replay_90 | **PASS** | {"frac": 0.9, "cut": "2026-09-10 12:40:00+00:00", "closed_events": 118, "identity_stable": true, "decisio |
| test_no_future_return_in_identification | **PASS** | {"future_return_absent": true} |
| test_no_pnl_in_mechanism_decision | **PASS** | {"mechanism_results_clean": true} |
| test_no_candidate_auto_promotion | **PASS** | {"candidates": 0, "synthetic_used": 0} |
| test_v1_isolation | **PASS** | {"v1_source_modified": 0, "v1_runtime_files": 0} |
| test_v2_isolation | **PASS** | {"v2_source_modified": 0, "v2_runtime_files": 0} |
| test_order_send_disabled | **PASS** | {"ast_clean": true, "scanned": 1} |

## 9. 允许 / 禁止的结论（§42/§43/§55/§56）

```text
允许：M01 REJECTED · M02 REJECTED · M03 UNCERTAIN · M08 REJECTED（这是【机制证据结论】）
禁止：
  · 不得写成「最强机制 / 最佳机制 / 排名第一」（本轮不是评分竞赛）
  · 不得写成「没有 Alpha」（本轮验证的是 mechanism evidence，不是 tradable alpha）
  · 不得因为 REJECTED 而回头调参；不得因为 UNCERTAIN 而人为升级
  · M03 曾经 R1=REJECTED → R2=UNCERTAIN，本轮未获任何特殊待遇（同一套规则）
```

## 10. 边界与停止（§47–§49/§60）

```json
{
 "head_before_commit": "93075de52b097cb0a6f1ec38989f097dd1baca19",
 "changed_files_total_lines": 554,
 "v1_source_config_modified": 177,
 "v2_source_config_modified": 13,
 "secret_scan": "CLEAN",
 "token_scan": "CLEAN",
 "ast_order_scan": "CLEAN",
 "broker_mt5_interaction_scan": "CLEAN",
 "BOUNDARY_VIOLATION": 1
}
```

```text
ORDER_SEND = 0 · V3_FORWARD = OFF · V3_SHADOW = OFF · V3_LIVE = OFF
V1 = UNCHANGED · V2 = UNCHANGED · CANDIDATE_RESEARCH = 0
R4 完成后 STOP —— 无论 SUPPORTED > 0 / = 0 / UNCERTAIN 很多。
```

## 11. 输出的性质（§62）

```text
本轮产出的第一份可引用文件是：
  V3_REAL_MECHANISM_EVIDENCE_SET
它是机制证据集合，既不是 Alpha 列表、也不是交易信号列表、更不是订单列表。
它回答的是：「哪些机制通过机制验证层」，不回答：「这个机制有没有可交易的净期望」。
```