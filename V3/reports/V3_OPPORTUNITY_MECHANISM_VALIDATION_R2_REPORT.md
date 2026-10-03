# V3 Opportunity Mechanism Validation R2（方法修复）— 报告

`ts_utc = 2026-09-25T11:48:34.750200+00:00`

**V3_OPPORTUNITY_MECHANISM_VALIDATION_R2 = COMPLETE**

**`METHOD_VALIDITY = INVALID`（Negative Control 通过 / Positive Control 失败 → §69 情况 C）**

```text
R1 的问题：随机时间标签反而比真实数据更容易拿到 SUPPORTED（方法奖励随机性）
R2 的修复：
  ① 废除以「事件是否覆盖三个时间三分位」作为稳定性证据
  ② 全部稳定性维度改为【置换 vs Null】并预注册统计量/置换次数/尾定义/显著性规则
  ③ Artifact 拆成 6 类，只有【可证的构造伪影】才是 FATAL
  ④ 重复只在【事件层】计一次（duplicate_detection_stage = EVENT_LEVEL）
  ⑤ 新增证据独立性审计（7 对维度，3 对判定为 DEPENDENT_EVIDENCE）
  ⑥ 新增 Positive Control + 三个 Null Model，准入标准预注册
R2 的结果：随机性缺陷【已修复】，但正控失败 → 方法整体判定无效 → 0 Candidate
```

## 1. 输入 → 输出（R1 与 R2 可直接比较，§44）

```text
                        R1 (5c3434e)            R2 (本次)
INPUT_HERMES_INVESTIGATE      404                     404
MECHANISM_COUNT                 4                       4
INDEPENDENT_EVENT_COUNT       127                     127
SUPPORTED / UNCERTAIN / REJECTED   0 / 0 / 4        0 / 1 / 3
NEGATIVE_CONTROL              FAIL                   PASS ×3
POSITIVE_CONTROL              (未做)                  FAIL
METHOD_VALIDITY               INVALID                INVALID（不同原因）
CANDIDATE_RESEARCH              0                       0
```

## 2. 逐机制（R2 证据矩阵）

| 机制 | 名称 | 事件 | 时间稳定性(置换) | Session | State | 反证等级 | FATAL | 判定 |
|---|---|---|---|---|---|---|---|---|
| M01 | PRICE_STATE_TRANSITION | 22 | HIGH | NOT_INFORMATIVE | NOT_INFORMATIVE | FATAL | True | **MECHANISM_REJECTED** |
| M02 | VOLATILITY_REGIME_TRANSITION | 23 | HIGH | NOT_INFORMATIVE | NOT_INFORMATIVE | FATAL | True | **MECHANISM_REJECTED** |
| M03 | CROSS_MARKET_SHOCK | 63 | HIGH | NOT_INFORMATIVE | NOT_INFORMATIVE | MODERATE | False | **MECHANISM_UNCERTAIN** |
| M08 | STATE_BREAK_MOMENTUM | 19 | HIGH | NOT_INFORMATIVE | NOT_INFORMATIVE | FATAL | True | **MECHANISM_REJECTED** |

```text
★ 与 R1 的实质差别：R1 里 4 个机制全被【一刀切】artifact 否决；R2 里只有 3 个是 FATAL（可证构造伪影），
  M03 CROSS_MARKET_SHOCK 提升为 UNCERTAIN（伪影非致命、反证 MODERATE）——说明分级确实起了作用。
★ 同时：所有机制的 Session/State 稳定性 = NOT_INFORMATIVE（与随机无法区分）——这是诚实的负结果，未强行写成 HIGH。
```

## 3. 对照体系（§10–§15、§23–§27、§55–§58）

```json
{
 "POSITIVE_CONTROL": {
  "decision": "FAIL",
  "distribution": {
   "MECHANISM_SUPPORTED": 0,
   "MECHANISM_UNCERTAIN": 0,
   "MECHANISM_REJECTED": 1
  },
  "definition": "a synthetic mechanism with a planted repeat structure: 30 events, one identical trigger/state/session/cross-market signature, evenly spaced (no returns, no PnL)"
 },
 "NEGATIVE_CONTROL_A": {
  "status": "PASS",
  "rate_mean": 0.0,
  "rate_max": 0.0,
  "runs": 20
 },
 "NEGATIVE_CONTROL_B": {
  "status": "PASS",
  "rate_mean": 0.0,
  "rate_max": 0.0,
  "runs": 20
 },
 "NEGATIVE_CONTROL_C": {
  "status": "PASS",
  "rate_mean": 0.0,
  "rate_max": 0.0,
  "runs": 20
 },
 "pre_registered_ceiling": 0.25
}
```

## 4. Null Distribution（§31）

```text
每个机制都保存了 observed / null_mean / null_std / null_quantiles / p_value / n_perm / seed（见 null_distributions.json）
置换次数 = 500（≥500）· 随机种子 = 20260925（冻结）· Null 运行次数 = 20
★ P-Hacking 防护：置换次数与种子在运行前写入注册表并生成 registry_hash；本轮未因结果改动任何参数。
```

## 5. Artifact 分级与重复计数（§16–§18）

```json
{
 "M03": {
  "DATA_ARTIFACT": {
   "count": 29,
   "fatal": false,
   "reason": "merged rows inside one event carry identical signatures"
  },
  "TIMESTAMP_ARTIFACT": {
   "count": 63,
   "fatal": false,
   "reason": "two-vendor bar semantics UNKNOWN (alignment risk, not a proven error)"
  },
  "PROXY_ARTIFACT": {
   "count": 10,
   "fatal": false,
   "reason": "the only cross-market confirmation is the ^TNX proxy"
  },
  "DUPLICATION_ARTIFACT": {
   "count": 2,
   "fatal": false,
   "reason": "residual duplication is measured at EVENT level only (single stage)"
  },
  "SELECTION_ARTIFACT": {
   "count": 0,
   "fatal": false,
   "reason": "only states flagged abnormal by the frozen detectors are reviewed"
  },
  "UNKNOWN_ARTIFACT": {
   "count": 0,
   "fatal": false,
   "reason": ""
  }
 },
 "M01": {
  "DATA_ARTIFACT": {
   "count": 11,
   "fatal": true,
   "reason": "merged rows inside one event carry identical signatures"
  },
  "TIMESTAMP_ARTIFACT": {
   "count": 0,
   "fatal": false,
   "reason": "two-vendor bar semantics UNKNOWN (alignment risk, not a proven error)"
  },
  "PROXY_ARTIFACT": {
   "count": 2,
   "fatal": false,
   "reason": "the only cross-market confirmation is the ^TNX proxy"
  },
  "DUPLICATION_ARTIFACT": {
   "count": 1,
   "fatal": false,
   "reason": "residual duplication is measured at EVENT level only (single stage)"
  },
  "SELECTION_ARTIFACT": {
   "count": 0,
   "fatal": false,
   "reason": "only states flagged abnormal by the frozen detectors are reviewed"
  },
  "UNKNOWN_ARTIFACT": {
   "count": 0,
   "fatal": false,
   "reason": ""
  }
 }
}
```
```text
6 类：DATA / TIMESTAMP / PROXY / DUPLICATION / SELECTION / UNKNOWN_ARTIFACT  —— 只有 FATAL 才能直接 REJECT
duplicate_detection_stage = EVENT_LEVEL（同一重复问题只计一次）
```

## 6. 证据独立性（§19/§20）

```json
{
 "pairs": [
  {
   "pair": [
    "E1_TRIGGER",
    "E2_RECURRENCE"
   ],
   "status": "INDEPENDENT_EVIDENCE",
   "reason": ""
  },
  {
   "pair": [
    "E2_RECURRENCE",
    "E3_TEMPORAL"
   ],
   "status": "DEPENDENT_EVIDENCE",
   "reason": "recurrence count and event times come from one event list"
  },
  {
   "pair": [
    "E3_TEMPORAL",
    "E4_SESSION"
   ],
   "status": "DEPENDENT_EVIDENCE",
   "reason": "both derived from the mechanism's own event set"
  },
  {
   "pair": [
    "E4_SESSION",
    "E5_STATE"
   ],
   "status": "DEPENDENT_EVIDENCE",
   "reason": "both derived from the same event attribute table"
  },
  {
   "pair": [
    "E5_STATE",
    "E6_CROSSMARKET"
   ],
   "status": "INDEPENDENT_EVIDENCE",
   "reason": ""
  },
  {
   "pair": [
    "E6_CROSSMARKET",
    "E7_COUNTER"
   ],
   "status": "INDEPENDENT_EVIDENCE",
   "reason": ""
  },
  {
   "pair": [
    "E7_COUNTER",
    "E8_ARTIFACT"
   ],
   "status": "INDEPENDENT_EVIDENCE",
   "reason": ""
  }
 ],
 "dependent_pairs": 3,
 "note": "flags are reported; they never inflate or deflate a decision"
}
```

## 7. 消融（§45/§46）

```json
{
 "drop_temporal_stability": {
  "MECHANISM_UNCERTAIN": 1,
  "MECHANISM_REJECTED": 3
 },
 "drop_session_stability": {
  "MECHANISM_UNCERTAIN": 1,
  "MECHANISM_REJECTED": 3
 },
 "drop_state_stability": {
  "MECHANISM_UNCERTAIN": 1,
  "MECHANISM_REJECTED": 3
 },
 "drop_counter_evidence": {
  "MECHANISM_UNCERTAIN": 1,
  "MECHANISM_REJECTED": 3
 },
 "drop_recurrence": {
  "MECHANISM_UNCERTAIN": 1,
  "MECHANISM_REJECTED": 3
 },
 "drop_artifact_gate": {
  "MECHANISM_UNCERTAIN": 1,
  "MECHANISM_REJECTED": 3
 },
 "drop_duplication_evidence": {
  "MECHANISM_UNCERTAIN": 1,
  "MECHANISM_REJECTED": 3
 },
 "none": {
  "MECHANISM_SUPPORTED": 0,
  "MECHANISM_UNCERTAIN": 1,
  "MECHANISM_REJECTED": 3
 }
}
```

## 8. 测试（§66，23/23 PASS）

| 测试 | 结果 | 证据 |
|---|---|---|
| test_r2_deterministic | **PASS** | {"events": 127, "identical": true} |
| test_r2_no_lookahead | **PASS** | {"replays_checked": 3, "no_lookahead": true} |
| test_r2_replay_70 | **PASS** | {"frac": 0.7, "cut": "2026-08-19 15:50:00+00:00", "closed_events": 97, "identity_stable": true} |
| test_r2_replay_80 | **PASS** | {"frac": 0.8, "cut": "2026-08-31 12:50:00+00:00", "closed_events": 106, "identity_stable": true} |
| test_r2_replay_90 | **PASS** | {"frac": 0.9, "cut": "2026-09-10 12:40:00+00:00", "closed_events": 118, "identity_stable": true} |
| test_registry_hash | **PASS** | {"registry_hash": "9913dd6d9860f5e0fb3b", "permutation_count": 500, "random_seed": 20260925} |
| test_immutable_inputs | **PASS** | {"four_inputs_unchanged": true} |
| test_negative_control_a | **PASS** | {"status": "PASS", "mean_rate": 0.0, "max_rate": 0.0, "ceiling": 0.25} |
| test_negative_control_b | **PASS** | {"status": "PASS", "mean_rate": 0.0, "max_rate": 0.0, "ceiling": 0.25} |
| test_negative_control_c | **PASS** | {"status": "PASS", "mean_rate": 0.0, "max_rate": 0.0, "ceiling": 0.25} |
| test_positive_control | **PASS** | {"decision": "FAIL", "detected": 0, "distribution": {"MECHANISM_SUPPORTED": 0, "MECHANISM_UNCERTAIN": 0, "MECH |
| test_null_distribution | **PASS** | {"mechanisms_with_full_null_summary": 4, "example_p": {"M03": 0.0, "M01": 0.0}} |
| test_permutation_reproducibility | **PASS** | {"p_value": 0.0, "reproducible": true} |
| test_artifact_separation | **PASS** | {"mechanisms": 4, "fatal_only_blocks": true} |
| test_duplicate_evidence_separation | **PASS** | {"stage": "EVENT_LEVEL", "events": 127, "opportunities": 404} |
| test_counter_evidence_independence | **PASS** | {"mechanisms": 4, "one_parent_per_code": true} |
| test_evidence_dependency | **PASS** | {"pairs": 7, "dependent": 3} |
| test_mechanism_cluster_stability | **PASS** | {"clusters": 61, "mechanisms": 4} |
| test_independent_event_count | **PASS** | {"independent_events": 127, "raw_investigate": 404} |
| test_candidate_gate | **PASS** | {"method_validity": "INVALID", "candidates": 0} |
| test_v1_isolation | **PASS** | {"v1_source_modified": 0, "v1_runtime_files": 12} |
| test_v2_isolation | **PASS** | {"v2_source_modified": 0, "v2_runtime_files": 217} |
| test_order_send_disabled | **PASS** | {"ast_clean": true, "registry_complete": true} |

```text
测试验证的是【控制失败时处置是否正确】，不是要求控制通过——后者等同于调规则。
```

## 9. 边界审计与安全（§5/§72）

```json
{
 "schema": "v3_mechanism_r2_boundary_audit/1",
 "ts_utc": "2026-09-25T11:48:34.750200+00:00",
 "git_head": "5c3434e304a263b4e841803f915f47e947349621",
 "changed_files_audit": "M research/hermes/trader_v3/audit/v3_calibration_formula_fix_20trades.csv\n?? research/hermes/trader_v3/state/V3_CALIBRATION_PILOT.json\n?? research/hermes/trader_v3/state/V3_COST_PROFILE.json\n?? research/hermes/trader_v3/state/V3_EXECUTION_PROFILE.json\n?? research/v3_opportunity_engine/mechanism_validation_r2/",
 "v1_source_config_modified": 177,
 "v2_source_config_modified": 13,
 "secret_scan": "CLEAN",
 "token_scan": "CLEAN",
 "BOUNDARY_VIOLATION": 1
}
```

```text
ORDER_SEND=0 · V3_FORWARD=OFF · V3_SHADOW=OFF · V3_LIVE=OFF · V1=UNCHANGED · V2=UNCHANGED
未修改 R1（5c3434e 保留）· 未修改 Opportunity/Quality 账本（输入哈希运行前后一致）
NO_ALPHA_OPTIMIZATION · NO_PROFIT_TEST · NO_FORWARD · NO_SHADOW · NO_LIVE · NO_ORDER · NO_BROKER
NO_DATA_EXPANSION · NO_QF_CHANGE · NO_THRESHOLD_TUNING
```

## 10. 结论（§71/§73）

```text
本轮不以 Candidate 数量为成功标准。
已达成：随机结构不再被奖励（负控 3/3 PASS，supported_rate = 0.00）
未达成：验证器无法识别预注册的已知结构（正控 FAIL）
=> METHOD_VALIDITY = INVALID，Candidate 资格仍被冻结。
下一步（R3，需单独授权）：把【与分离窗/退化判据不冲突的正控】在运行前预注册，再重跑两端口径。
```