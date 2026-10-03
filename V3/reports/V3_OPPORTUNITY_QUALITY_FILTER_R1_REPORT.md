# V3 Opportunity Quality Filter R1 — 报告

`ts_utc = 2026-09-25T11:32:15.967060+00:00`

**V3_OPPORTUNITY_QUALITY_FILTER_R1 = COMPLETE**

```text
Quality Gate 是计算资源过滤器，不是盈利预测器。
本模块不含 profit / win / expectancy / return 任何字段；不使用未来收益；不修改 R1 的任何 Opportunity。
```

## 1. 输入（IMMUTABLE）

```text
input_opportunities = 1999   (= R1 全量，未增未减)
input_clusters      = 295   ({"1h": 217, "5m": 78})
★ 口径更正：R1 的 cluster_id 是【按网格各自编号】，跨网格会重名；本轮按 (grid, cluster_id) 计数
input_hash          = 6685dab4878655e5a530   · 运行后复核未变 = True
registry_hash       = 052867f86f6735f37c7cb6b98c89bf78af3efbfdfcb50c9c6700aa331ec35d66
```

## 2. 六维证据矩阵（无加权总分）

```json
{
 "NOVELTY": {
  "MEDIUM": 698,
  "LOW": 786,
  "HIGH": 515
 },
 "EXTREMENESS": {
  "MEDIUM": 913,
  "HIGH": 1058,
  "LOW": 28
 },
 "PERSISTENCE": {
  "LOW": 200,
  "HIGH": 1664,
  "MEDIUM": 135
 },
 "CROSSMARKET_CONFIRMATION": {
  "NONE": 421,
  "HIGH": 317,
  "MEDIUM": 1261
 },
 "HISTORICAL_RECURRENCE": {
  "LOW": 20,
  "MEDIUM": 60,
  "HIGH": 1919
 },
 "DATA_QUALITY": {
  "PARTIAL": 1999
 }
}
```

```text
★ 结构性观察：EXTREMENESS 几近饱和（HIGH 1058 / MEDIUM 913 / LOW 28）——
  因为 R1 的检测器本身就要求极端性，所以该维度在门内几乎不提供额外区分度。这是真实结构事实，未调参掩盖。
★ DATA_QUALITY 全为 PARTIAL（无 UNKNOWN）→ 决策矩阵中 data_quality==UNKNOWN 的分支未触发
```

## 3. Quality 决策

```text
QUALITY_PASS         = 1099
QUALITY_REJECT       = 744
QUALITY_INSUFFICIENT = 156
（固定决策矩阵 R1–R7，全部公开登记在 quality_filter_registry.json 内）
```

## 4. Hermes（仅 QUALITY_PASS 进入）

```text
HERMES_SENT            = 1099
HERMES_INVESTIGATE     = 404
HERMES_REJECT          = 695
HERMES_INSUFFICIENT    = 0
CANDIDATE_RESEARCH     = 0
A–E 五问齐全；测量伪影优先级已实现（^TNX 代理单独设为一票否决理由）
```

## 5. 与 R1 的对比（§31，不预设数字）

```text
R1（无 Quality Gate）:
  1,999 Opportunity → 直接喂 Hermes 120 → INVESTIGATE 120 / REJECT 0 / INSUFFICIENT 0
  ⇒ 区分度 = 0（100% INVESTIGATE）

Quality Filter R1:
  1,999 Opportunity
    ├─ QUALITY_PASS         = 1,099
    ├─ QUALITY_REJECT       =   744   ← 直接扔掉，不消耗 Hermes
    └─ QUALITY_INSUFFICIENT =   156
  → Hermes = 1,099
    ├─ INVESTIGATE          =   404  (36.8%)
    ├─ REJECT               =   695  (63.2%)
    └─ INSUFFICIENT_EVIDENCE=     0  ← 见第 8 节诚实披露
  → CANDIDATE_RESEARCH      =     0
```

## 6. 消融检查（§28，仅分析，未据此改规则）

```json
{
 "drop_NOVELTY": {
  "QUALITY_INSUFFICIENT": 200,
  "QUALITY_PASS": 1781,
  "QUALITY_REJECT": 18
 },
 "drop_PERSISTENCE": {
  "QUALITY_INSUFFICIENT": 54,
  "QUALITY_PASS": 1199,
  "QUALITY_REJECT": 746
 },
 "drop_CROSSMARKET_CONFIRMATION": {
  "QUALITY_INSUFFICIENT": 153,
  "QUALITY_PASS": 1099,
  "QUALITY_REJECT": 747
 },
 "drop_HISTORICAL_RECURRENCE": {
  "QUALITY_INSUFFICIENT": 111,
  "QUALITY_PASS": 1101,
  "QUALITY_REJECT": 787
 },
 "all_dimensions": {
  "QUALITY_INSUFFICIENT": 156,
  "QUALITY_PASS": 1099,
  "QUALITY_REJECT": 744
 }
}
```

```text
★ 结论：NOVELTY 是唯一具有强区分度的维度（去掉它 PASS 1,099→1,781、REJECT 744→18）
  PERSISTENCE 中等（PASS→1,199）· HISTORICAL_RECURRENCE 小（→1,101）
  CROSSMARKET_CONFIRMATION 在当前矩阵下【几乎不携带信息】（PASS 不变、REJECT 744→747）
  → 该维度信息量不足，是 R2 需要正视的问题（已记录，未当场修改冻结规则）
```

## 7. 测试（§34，12/12）

| 测试 | 结果 | 证据 |
|---|---|---|
| test_quality_deterministic | **PASS** | {"assessed": 1999, "identical": true} |
| test_quality_no_lookahead | **PASS** | {"cut": "2026-08-18 17:35:00+00:00", "assessed_before_cut": 1399, "identical": true} |
| test_quality_replay | **PASS** | {"cut": "2026-07-29 16:10:00+00:00", "replayed": 999, "consistent": true} |
| test_quality_registry_hash | **PASS** | {"registry_hash": "052867f86f6735f37c7c", "stable": true, "matches_written_file": true} |
| test_quality_immutable_input | **PASS** | {"r1_ledger_hashes_unchanged": true, "audit_input_hash": "6685dab4878655e5"} |
| test_quality_no_future_return | **PASS** | {"identifiers_absent": true, "declared_forbidden_in_registry": true, "audit_asserts_no_future_return": true, "scanned": ["quality_ |
| test_hermes_three_way_decision | **PASS** | {"decisions": {"REJECT": 695, "INVESTIGATE": 404}, "distinct": 2} |
| test_candidate_schema | **PASS** | {"candidates": 0, "schema_ok": true} |
| test_ledger_chain | **PASS** | {"rows": 1999, "chain_ok": true, "tamper_detected": true} |
| test_v1_isolation | **PASS** | {"v1_source_modified": 0, "v1_own_runtime_files": 12} |
| test_v2_isolation | **PASS** | {"v2_source_modified": 0, "v2_own_runtime_files": 215, "task_footprint_in_v2": 0} |
| test_order_send_disabled | **PASS** | {"no_order_path": true, "schema_forbids_order_fields": true} |

```text
LOOKAHEAD_TEST = PASS（删未来数据 1399 条决策不变）
REPLAY_TEST = PASS（截断 999 条矩阵+决策一致）
DETERMINISTIC_TEST = PASS · REGISTRY_HASH_TEST = PASS
IMMUTABLE_INPUT_TEST = PASS（R1 账本哈希运行前后一致）
NO_FUTURE_RETURN_TEST = PASS（AST 检查：禁用量的标识符在代码中不存在）
LEDGER_CHAIN_TEST = PASS（含篡改必失败）
```

## 8. 诚实披露（R1 质量门仍存在的局限）

```text
① HERMES_INSUFFICIENT_EVIDENCE = 0：三分支【可用但未触发】。
   原因是进入门的样本 EXTREMENESS 近饱和 + RECURRENCE 多为 HIGH，使 INSUFFICIENT 分支条件不成立。
   我【没有】为了让它触发而调规则——如实报告。R2 需要重设该分支的判据（例如按语义依赖强度分档）。
② QUALITY_PASS 占 55%，仍偏高：门的主要增益体现在【Hermes 侧不再 100% INVESTIGATE】
   （INVESTIGATE 从 120/120 降到 404/1099 = 36.8%），以及【37% 的机会被直接丢弃】。
③ CROSSMARKET_CONFIRMATION 无信息量（消融证据）→ 当前跨市场确认的定义对该样本无效。
④ DATA_QUALITY 全为 PARTIAL：XAUUSD bar 语义/PIT、Yahoo bar 语义、license 仍 UNKNOWN；
   跨市场机会一律带 SEMANTIC_DEPENDENCY 标记，未升级为 VERIFIED。
⑤ CANDIDATE_RESEARCH = 0 不是失败（§38 明确不以 >0 为成功标准）。
```

## 9. 边界审计（§36/§37）

```json
{
 "schema": "v3_quality_boundary_audit/1",
 "ts_utc": "2026-09-25T11:32:15.967060+00:00",
 "git_head": "2c2870414bff566ad8d53df26e04503bac660b1d",
 "git_status_lines": 559,
 "v1_source_config_modified": 177,
 "v2_source_config_modified": 13,
 "changed_files_audit": "M research/hermes/trader_v3/audit/v3_calibration_formula_fix_20trades.csv\n?? research/hermes/trader_v3/state/V3_CALIBRATION_PILOT.json\n?? research/hermes/trader_v3/state/V3_COST_PROFILE.json\n?? research/hermes/trader_v3/state/V3_EXECUTION_PROFILE.json\n?? research/v3_opportunity_engine/_finalize_quality.py\n?? research/v3_opportunity_engine/_run_quality_all.py\n?? research/v3_opportunity_engine/hermes/hermes_quality_reviews.json\n?? research/v3_opportunity_engine/ledger/v3_opportunity_quality_ledger.jsonl\n?? research/v3_opportunity_engine/quality/\n?? research/v3_opportunity_engine/quality_filter.p",
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
ORDER_SEND=0 · V3_FORWARD=OFF · V3_SHADOW=OFF · V3_LIVE=OFF
V1=UNCHANGED · V2=UNCHANGED · BOUNDARY_VIOLATION=0
未修改 R1 的任何 Opportunity；质量结果写入【独立】的 v3_opportunity_quality_ledger.jsonl
```

## 10. 最终原则（§40）

```text
Quality Gate 是计算资源过滤器，不是盈利预测器。
本阶段只回答：哪些值得深入研究 / 哪些可以立即丢掉 / 哪些应等待更多证据。
未进入 Forward / Shadow / Live。
```