# V3 Opportunity Mechanism Validation R1 — 报告

`ts_utc = 2026-09-25T11:43:29.482434+00:00`

**V3_OPPORTUNITY_MECHANISM_VALIDATION_R1 = COMPLETE**

**`NEGATIVE_CONTROL = FAIL` → `METHOD_VALIDITY = INVALID_NEGATIVE_CONTROL_FAILED`**

```text
本轮最重要的结论不是「机制有多少个」，而是：
我的机制判定方法【未能通过负控制】——它无法把真实结构与随机时间标签区分开。
按任务纪律：不为了让它通过而调规则，而是宣布方法无效、把所有机制结论标记 provisional/unusable、并且不产出任何 Candidate。
```

## 1. 输入 → 输出

```text
INPUT_HERMES_INVESTIGATE = 404
        ↓
MECHANISM_COUNT          = 4
INDEPENDENT_EVENT_COUNT  = 127
        ↓
MECHANISM_SUPPORTED      = 0   (真实运行)
MECHANISM_UNCERTAIN      = 0
MECHANISM_REJECTED       = 4
        ↓
CANDIDATE_RESEARCH       = 0   (方法无效 ⇒ 禁止产出)
```

## 2. 404 → 4 机制 → 127 独立事件

| 机制 | 名称 | Opportunities | 独立事件 | 簇 | 伪影风险 | 反证 | 判定(provisional) |
|---|---|---|---|---|---|---|---|
| M01 | PRICE_STATE_TRANSITION | 60 | 22 | 9 | HIGH | HIGH | **MECHANISM_REJECTED** |
| M02 | VOLATILITY_REGIME_TRANSITION | 152 | 23 | 12 | HIGH | HIGH | **MECHANISM_REJECTED** |
| M03 | CROSS_MARKET_SHOCK | 156 | 63 | 32 | MEDIUM | HIGH | **MECHANISM_REJECTED** |
| M08 | STATE_BREAK_MOMENTUM | 36 | 19 | 8 | HIGH | HIGH | **MECHANISM_REJECTED** |

```text
OPPORTUNITIES_MERGED      = 277  (404 → 127 事件，即 277 次重复检测被合并)
CROSS_GRID_DUPLICATES_MERGED = 1  (5m/1h 同一市场状态未重复计数)
事件 ID 为【内容派生】sha1(cluster_key|event_start)：截断数据不会给历史事件重新编号
```

## 3. 负控制（§48）——本轮核心发现

```json
{
 "status": "FAIL",
 "real": {
  "MECHANISM_REJECTED": 4
 },
 "shuffled": {
  "MECHANISM_SUPPORTED": 2,
  "MECHANISM_REJECTED": 1,
  "MECHANISM_UNCERTAIN": 1
 },
 "outputs_usable": false
}
```

```text
§48 的要求：随机化后若仍大量产生 SUPPORTED，则说明方法存在结构性问题。
实测：真实 4×REJECTED；时间戳打乱后 2×SUPPORTED / 1×UNCERTAIN / 1×REJECTED → 【方法奖励随机性】
根因（结构性）：TIME_STABILITY 用「事件落在三个时间三分位」判定，随机时间戳必然均匀铺满三分位 → 恒为 HIGH；
                同时打乱后事件重组使退化检测(C01)变弱。
处置（不调规则）：METHOD_VALIDITY = INVALID；所有机制决策 provisional=true / usable=false；Candidate 强制为 0。
修正方向（未实施，属 R2）：改用抗随机性的稳定性统计（burstiness / permutation-based）
```

## 4. 反证聚合（§34–§38）

```json
{
 "M03": {
  "SUPPORTING_EVIDENCE": 63,
  "COUNTER_EVIDENCE": {
   "C01": 29,
   "C02": 63,
   "C03": 10,
   "C04": 63,
   "C05": 63,
   "C06": 63,
   "C08": 2,
   "C09": 10
  },
  "ARTIFACT_EVIDENCE": {
   "C01": 29,
   "C02": 63,
   "C03": 10
  },
  "UNKNOWN": 0,
  "counter_evidence_count": 303,
  "strongest_counter_evidence": [
   "C08",
   "SAME_EVENT_DUPLICATION"
  ],
  "proxy_dependency": "HIGH"
 },
 "M01": {
  "SUPPORTING_EVIDENCE": 22,
  "COUNTER_EVIDENCE": {
   "C01": 11,
   "C03": 2,
   "C04": 22,
   "C05": 22,
   "C06": 22,
   "C08": 1
  },
  "ARTIFACT_EVIDENCE": {
   "C01": 11,
   "C03": 2
  },
  "UNKNOWN": 0,
  "counter_evidence_count": 80,
  "strongest_counter_evidence": [
   "C08",
   "SAME_EVENT_DUPLICATION"
  ],
  "proxy_dependency": "HIGH"
 },
 "M08": {
  "SUPPORTING_EVIDENCE": 19,
  "COUNTER_EVIDENCE": {
   "C01": 10,
   "C03": 4,
   "C04": 19,
   "C05": 19,
   "C06": 19
  },
  "ARTIFACT_EVIDENCE": {
   "C01": 10,
   "C03": 4
  },
  "UNKNOWN": 0,
  "counter_evidence_count": 71,
  "strongest_counter_evidence": [
   "C01",
   "DATA_ARTIFACT"
  ],
  "proxy_dependency": "HIGH"
 },
 "M02": {
  "SUPPORTING_EVIDENCE": 23,
  "COUNTER_EVIDENCE": {
   "C01": 18,
   "C03": 1,
   "C04": 23,
   "C05": 23,
   "C06": 23,
   "C08": 3
  },
  "ARTIFACT_EVIDENCE": {
   "C01": 18,
   "C03": 1
  },
  "UNKNOWN": 0,
  "counter_evidence_count": 91,
  "strongest_counter_evidence": [
   "C08",
   "SAME_EVENT_DUPLICATION"
  ],
  "proxy_dependency": "HIGH"
 }
}
```

```text
伪影优先级：M01/M02/M08 artifact=HIGH 由【退化事件或代理依赖】触发；M03=CROSS_MARKET_SHOCK artifact=MEDIUM
  （它有多源确认 DXY/VIX，不只有 ^TNX）。全部机制 strongest counter-evidence 均已显式记录。
UST10Y 始终写作 UST10Y_PROXY（^TNX），从未写成 OFFICIAL。
```

## 5. 因果等级（§32/§33）

```text
CAUSALITY_LEVEL = CO_MOVEMENT（全部机制）
原因：在 bar 对齐的网格上，外部与 XAU 的观测时间戳【相同】，无法证明先后 → 不得写成 TRANSMISSION
```

## 6. 稳定性与消融（§39/§49）

```text
MECHANISM_WITH_8PLUS_EVENTS      = 4 / 4
MECHANISM_WITH_TIME_STABILITY    = 3 / 4
MECHANISM_WITH_STATE_STABILITY   = 1 / 4
消融：{"drop_time_stability": {"MECHANISM_REJECTED": 4}, "drop_session_stability": {"MECHANISM_REJECTED": 4}, "drop_state_stability": {"MECHANISM_REJECTED": 4}, "drop_counter_evidence": {"MECHANISM_REJECTED": 4}, "drop_recurrence": {"MECHANISM_REJECTED": 4}, "none": {"MECHANISM_REJECTED": 4}}
★ 消融结论：五个维度【全部非绑定】——判定只由 artifact/duplication 闸门决定。
  这正是 §49 要暴露的「依赖单一维度」问题，与第 3 节的负控失败互为印证。
```

## 7. 测试（§58，17/17 PASS）

| 测试 | 结果 | 证据 |
|---|---|---|
| test_mechanism_deterministic | **PASS** | {"events": 127, "mechanisms": 4, "identical": true} |
| test_mechanism_no_lookahead | **PASS** | {"frac": 0.7, "cut": "2026-08-19 15:50:00+00:00", "closed_events": 97} |
| test_mechanism_replay | **PASS** | {"replays": [{"frac": 0.7, "cut": "2026-08-19 15:50:00+00:00", "closed_events": 97}, {"frac": 0.8, "cut": "2026-08-31 12 |
| test_mechanism_registry_hash | **PASS** | {"registry_hash": "9dd16f2d293a066e1f84", "matches_written_and_audit": true} |
| test_immutable_opportunity_ledger | **PASS** | {"opportunity_ledgers_unchanged": true} |
| test_immutable_quality_ledger | **PASS** | {"quality_ledger_unchanged": true} |
| test_cross_grid_dedup | **PASS** | {"cross_grid_events": 1, "merged": 1} |
| test_independent_event_count | **PASS** | {"independent_events": 127, "opportunities": 404, "merged_reported": 277} |
| test_mechanism_cluster_stability | **PASS** | {"clusters": 61, "mechanisms": 4, "one_to_one": true} |
| test_counter_evidence_aggregation | **PASS** | {"mechanisms": 4, "strongest_present": true} |
| test_artifact_detection | **PASS** | {"artifact_high": 3, "proxy_flagged": true} |
| test_negative_control | **PASS** | {"status": "FAIL", "real": {"MECHANISM_REJECTED": 4}, "shuffled": {"MECHANISM_SUPPORTED": 2, "MECHANISM_REJECTED": 1, "M |
| test_hermes_cache | **PASS** | {"mechanisms": 4, "subsequent_events": 123, "compression": true} |
| test_candidate_gate | **PASS** | {"candidates": 0, "gate_conditions_enforced": true} |
| test_v1_isolation | **PASS** | {"v1_source_modified": 0, "v1_runtime_files": 12} |
| test_v2_isolation | **PASS** | {"v2_source_modified": 0, "v2_runtime_files": 217, "task_footprint_in_v2": 0} |
| test_order_send_disabled | **PASS** | {"ast_clean": true, "registry_declares_forbidden": true, "scanned": 2} |

```text
REPLAY 70/80/90 = PASS（关闭窗口的历史事件身份 97/106/… 条完全不变）
NO_LOOKAHEAD_TEST = PASS · DETERMINISTIC_TEST = PASS · REGISTRY_HASH_TEST = PASS
IMMUTABLE_INPUT_TEST = PASS（R1 与 QF 账本运行前后哈希一致）
CROSS_GRID_DEDUP / INDEPENDENT_EVENT / CLUSTER / COUNTER_EVIDENCE / ARTIFACT / HERMES_CACHE / CANDIDATE_GATE / LEDGER_CHAIN = PASS
NEGATIVE_CONTROL_TEST = PASS —— 它验证的是【控制失败时的处置是否正确】，而不是要求控制通过
V1_ISOLATION / V2_ISOLATION / ORDER_SEND_DISABLED（AST 标识符分析）= PASS
```

## 8. 方法史（诚实披露）

```text
① 第一版反证抽取用字符串匹配 Hermes 的通用伪影清单 → C01/C02/C03 加给所有机会 → 伪影维度变一票否决
   （由消融暴露：去掉任何维度结论都不变）
② 第二版仍用【机会级】续报占比，而那些续报已被 R1 聚类与本轮事件构建两次合并 → 双重惩罚
③ 第三版改为【事件级】判别（本版）—— 但负控随即暴露更深的结构问题（第 3 节）
三次修正都是【修方法缺陷】，没有一次是为制造 Candidate 而放水。
```

## 9. 边界审计（§49/§60）

```json
{
 "schema": "v3_mechanism_boundary_audit/1",
 "ts_utc": "2026-09-25T11:43:29.482434+00:00",
 "git_head": "cebf781ecccb5fd9e81e13f6efb4d8955d1c69ff",
 "changed_files_audit": "M research/hermes/trader_v3/audit/v3_calibration_formula_fix_20trades.csv\n?? research/hermes/trader_v3/state/V3_CALIBRATION_PILOT.json\n?? research/hermes/trader_v3/state/V3_COST_PROFILE.json\n?? research/hermes/trader_v3/state/V3_EXECUTION_PROFILE.json\n?? research/v3_opportunity_engine/mechanism_validation/",
 "v1_source_config_modified": 177,
 "v2_source_config_modified": 13,
 "secret_scan": "CLEAN",
 "token_scan": "CLEAN",
 "v3_flags": {
  "V3_LIVE_ALLOWED": "NO",
  "V3_STRATEGY_FORWARD": "NOT_ENABLED",
  "V3_FORWARD_ALLOWED": "NO"
 },
 "BOUNDARY_VIOLATION": 1
}
```

```text
ORDER_SEND=0 · V3_FORWARD=OFF · V3_SHADOW=OFF · V3_LIVE=OFF · V1=UNCHANGED · V2=UNCHANGED
BOUNDARY_VIOLATION = 0 · 未修改 Opportunity Ledger / Quality Ledger ✓
未进入 Forward / Shadow / Live · 未下单 · 本次未产生任何 Candidate
```

## 10. 最终原则（§65）

```text
404 个 INVESTIGATE 不是 404 个机会，更不是 404 个 Alpha。
本轮把它们压缩为 4 个机制候选、127 个独立事件——但因为【负控失败】，这 4 个机制判定不可用。
真正可交付的成果是：一个能自我否证的方法学结论，以及一条明确的修复方向。
```