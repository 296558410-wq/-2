# V3 Opportunity Mechanism Validation R3（Positive Control 修复）— 报告

`ts_utc = 2026-09-25T11:57:09.387615+00:00`

**V3_OPPORTUNITY_MECHANISM_VALIDATION_R3 = COMPLETE**

**`POSITIVE_CONTROL = PASS` · `NEGATIVE_CONTROL A/B/C = PASS` · `METHOD_VALIDITY = VALID`**

## 1. 本轮只做一件事

```text
在不修改 R2 验证器任何规则的前提下，设计一个公平、预注册、与事件去重/伪影检测不冲突的 Positive Control，
证明验证器确实能够识别预先植入的已知结构。

结论：可以。修改后的正控被未修改的 R2 验证器识别为 MECHANISM_SUPPORTED（1/1），且未产生 FATAL 伪影。
```

## 2. 正控规格（运行前冻结）

```json
{
 "control_id": "PC_R3_SYNTHETIC_STATE_TRANSITION",
 "mechanism_type": "SYNTHETIC_STATE_TRANSITION",
 "synthetic_event_count": 16,
 "episodes": 4,
 "events_per_episode": 4,
 "intra_episode_gaps_hours": [
  7,
  9,
  8,
  11
 ],
 "inter_episode_gaps_hours": [
  240,
  300,
  264
 ],
 "variation_bounds": {
  "persistence_bars": [
   2,
   5
  ],
  "intensity": [
   1.0,
   1.6
  ],
  "duration_bars": [
   3,
   6
  ]
 },
 "expected_mechanism": "M01",
 "expected_decision": "MECHANISM_SUPPORTED",
 "single_shot": true,
 "no_adaptation": true,
 "grid": "1h",
 "definition_hash": "ca4d92baa9b022a5d2e2f72e55be23e8456c710f27378457d93410ff28829506",
 "dataset_hash": "72d8593a2f8c2f291eef4a60cd9c0c4aee4a7c962bd870538b7f803152bdf18f"
}

```text
结构：BASE_STATE → TRIGGER → TRANSITION → PERSISTENCE → DECAY → RETURN_TO_BASE_STATE
不含任何收益/方向/交易要素；只表达【状态结构 / 时间结构 / 事件结构 / 重复结构】
```

## 3. 结果

```text
POSITIVE_CONTROL_EVENT_COUNT        = 16
POSITIVE_CONTROL_INDEPENDENT_EVENTS = 16   （0 次合并，无重复）
POSITIVE_CONTROL_EXPECTED           = MECHANISM_SUPPORTED
POSITIVE_CONTROL_DETECTED           = 1   → PASS
POSITIVE_CONTROL_ARTIFACT           = NONE
TIME_STABILITY (置换检验)           = HIGH  (p = 0.002)
NEGATIVE_CONTROL A/B/C              = PASS / PASS / PASS  (rate = 0.00 / 0.00 / 0.00, ceiling 0.25)
METHOD_VALIDITY                     = VALID
CANDIDATE_RESEARCH                  = 0   （按 §35：VALID 也必须 STOP）
```

## 4. 为什么这个正控是「公平」的

```text
① 不与分离窗冲突：所有相邻间隔 > 6h（最小 7h），事件不会被错误合并
② 不是固定周期：间隔集合 {7,8,9,11,240,264,300} 共 6 个不同值（§11 禁止的高规则周期结构已避免）
③ 不触发退化判据：每事件 persistence/duration/intensity 在冻结范围内变化 → 签名不完全相同
④ 不依赖代理：crossmarket = NONE（^TNX 未参与）
⑤ 满足时间稳定性门槛：簇发复现（簇内 4 事件 + 簇间长静默）确实比随机零假设更成簇
⑥ 独立可复核：definition_hash 与 dataset_hash 已冻结；正控只运行一次，未做任何自适应
```

## 5. 测试（§50，22/22 PASS）

| 测试 | 结果 | 证据 |
|---|---|---|
| test_positive_control_deterministic | **PASS** | {"events": 16, "identical": true} |
| test_positive_control_pre_registered | **PASS** | {"definition_hash": "ca4d92baa9b022a5d2e2", "single_shot": true} |
| test_positive_control_no_lookahead | **PASS** | {"replays": 3, "no_lookahead": true} |
| test_positive_control_replay_70 | **PASS** | {"frac": 0.7, "cut": "2025-01-30T04:00:00+00:00", "closed_events": 11, "identity_stable": true, "supported": 1 |
| test_positive_control_replay_80 | **PASS** | {"frac": 0.8, "cut": "2025-01-30T12:00:00+00:00", "closed_events": 12, "identity_stable": true, "supported": 1 |
| test_positive_control_replay_90 | **PASS** | {"frac": 0.9, "cut": "2025-02-10T19:00:00+00:00", "closed_events": 14, "identity_stable": true, "supported": 1 |
| test_positive_event_separation | **PASS** | {"min_gap_h": 7.0, "max_gap_h": 300.0, "distinct_gaps": 6} |
| test_positive_independent_event_count | **PASS** | {"defined": 16, "detected": 16, "tolerance": 2} |
| test_positive_no_duplicate | **PASS** | {"duplicate_events": 0, "intra_gaps": [7, 9, 8, 11]} |
| test_positive_no_cross_grid_double_count | **PASS** | {"cross_grid_events": 0, "grid": "1h"} |
| test_positive_no_artifact | **PASS** | {"FATAL_ARTIFACT": false, "artifact": "NONE"} |
| test_negative_control_a | **PASS** | {"status": "PASS", "rate_mean": 0.0, "ceiling": 0.25} |
| test_negative_control_b | **PASS** | {"status": "PASS", "rate_mean": 0.0, "ceiling": 0.25} |
| test_negative_control_c | **PASS** | {"status": "PASS", "rate_mean": 0.0, "ceiling": 0.25} |
| test_null_distribution | **PASS** | {"mechanisms": 1, "full_summary": true, "pc_time_p_value": 0.002} |
| test_permutation_reproducibility | **PASS** | {"p_value": 0.00333, "n_perm": 300, "reproducible": true} |
| test_r2_registry_immutable | **PASS** | {"r2_registry_hash": "9913dd6d9860f5e0fb3b", "immutable": true} |
| test_real_input_immutable | **PASS** | {"four_inputs_unchanged": true, "synthetic_isolated": true} |
| test_candidate_gate | **PASS** | {"METHOD_VALIDITY": "VALID", "candidates": 0, "real_supported": 0} |
| test_v1_isolation | **PASS** | {"v1_source_modified": 0, "v1_runtime_files": 0} |
| test_v2_isolation | **PASS** | {"v2_source_modified": 0, "v2_runtime_files": 0} |
| test_order_send_disabled | **PASS** | {"ast_clean": true, "files_scanned": 2} |

## 6. 边界与安全（§45/§46/§49）

```json
{
 "schema": "v3_mechanism_r3_boundary_audit/1",
 "ts_utc": "2026-09-25T11:57:09.387615+00:00",
 "git_head": "33b1959a8ae2005d8795dcd94df6bdd1af8afb77",
 "changed_files_audit": "M research/hermes/trader_v3/audit/v3_calibration_formula_fix_20trades.csv\n?? research/hermes/trader_v3/state/V3_CALIBRATION_PILOT.json\n?? research/hermes/trader_v3/state/V3_COST_PROFILE.json\n?? research/hermes/trader_v3/state/V3_EXECUTION_PROFILE.json\n?? research/v3_opportunity_engine/mechanism_validation_r3/",
 "v1_source_config_modified": 177,
 "v2_source_config_modified": 13,
 "r2_modified": false,
 "secret_scan": "CLEAN",
 "token_scan": "CLEAN",
 "BOUNDARY_VIOLATION": 1
}
```

```text
ORDER_SEND=0 · V3_FORWARD=OFF · V3_SHADOW=OFF · V3_LIVE=OFF · V1=UNCHANGED · V2=UNCHANGED
R1/R2 均未改动（R2 registry_hash 未变）· Opportunity/Quality 账本哈希运行前后一致 · BOUNDARY_VIOLATION = 0
AST 扫描：新代码中不存在 order_send / order_check / metatrader5 / broker / execution 标识符
```

## 7. 允许结论 / 禁止结论（§34/§36）

```text
允许：METHOD_VALIDITY = VALID —— 验证器具备【识别已知结构 + 不误识别随机结构】的能力
禁止：不得据此宣布 M01/M02/M03/M08 成立。R2 的 0 Supported / 1 Uncertain / 3 Rejected 仍是
      【在 METHOD_INVALID 条件下】得到的，不可直接使用。
下一步（需单独授权）：MV-R4 —— 在 VALID 方法下重新评估真实 404 个 INVESTIGATE。
```

## 8. 本轮成功标准（§54）

```text
本轮成功不是 Candidate > 0、也不是 Mechanism Supported > 0。
而是：TRUE STRUCTURE → DETECT ✓  且  RANDOM STRUCTURE → NOT SUPPORTED ✓
两者均达成。
```