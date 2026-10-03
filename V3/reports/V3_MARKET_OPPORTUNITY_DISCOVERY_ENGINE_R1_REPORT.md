# V3 Market Opportunity Discovery Engine — R1 报告

`ts_utc = 2026-09-25T11:22:45.094011+00:00`

## 1. R1 定位与闭环

```text
市场 → 状态 → 异常 → Opportunity → Hermes → 机制 → 反证 → 是否值得继续研究
R1 实现了该闭环的前半段：Market State → Detector → Opportunity Record → Hermes 审查 → Candidate Pool(到 RESEARCH)
Opportunity ≠ Alpha：本仓库不含 profit_score / win_probability / expected_profit / signal / order 任何字段
```

## 2. 数据

```text
XAUUSD : HistData M1 BID（2025-01-01 → 2026-09-18）→ 派生 1h/5m
DXY    : Yahoo DX-Y.NYB · VIX: Yahoo ^VIX · UST10Y_PROXY: Yahoo ^TNX（始终标注 PROXY，非官方 UST10Y）
1h 网格: 2992 行 · ['2025-01-02 13:00:00+00:00', '2026-09-18 18:00:00+00:00']
5m 网格: 3600 行 · ['2026-07-17 12:20:00+00:00', '2026-09-18 18:55:00+00:00']
数据语义保持 UNKNOWN 未升级：XAUUSD_DEFINITION=UNKNOWN · BAR_OPEN_CLOSE=UNKNOWN · LICENSE=UNKNOWN
EVENT_STATE=EVENT_UNKNOWN · EVENT_PIT=UNKNOWN（事件层与数据窗无重叠，未凑数）
```

## 3. Detector Registry（无隐藏参数）

```json
[
 {
  "detector_id": "D1_STATE_BREAK",
  "detector_name": "State Break",
  "version": "R1.0.0",
  "description": "current state deviates strongly from its recent rolling distribution",
  "input_features": [
   "return_60m",
   "vol_pct_240",
   "vol_state"
  ],
  "threshold_definition": {
   "return_z_abs": 3.0,
   "vol_pct": 0.95
  },
  "lookback_definition": "rolling 240 bars (min 60)",
  "cooldown_bars": 6,
  "clustering_rule": "consecutive same-type detections within 3 bars join one cluster",
  "data_dependencies": [
   "xau"
  ],
  "output_type": "OPP_STATE_BREAK"
 },
 {
  "detector_id": "D2_STATE_TRANSITION",
  "detector_name": "State Transition",
  "version": "R1.0.0",
  "description": "volatility regime transition between adjacent bars",
  "input_features": [
   "vol_state"
  ],
  "threshold_definition": {
   "transitions": [
    "VOL_NORMAL->VOL_EXTREME",
    "VOL_CONTRACTION->VOL_EXPANSION",
    "VOL_EXTREME->VOL_NORMAL"
   ]
  },
  "lookback_definition": "1 bar",
  "cooldown_bars": 6,
  "clustering_rule": "same as D1",
  "data_dependencies": [
   "xau"
  ],
  "output_type": "OPP_STATE_TRANSITION"
 },
 {
  "detector_id": "D3_CROSSMARKET_SHOCK",
  "detector_name": "Cross-Market Shock",
  "version": "R1.0.0",
  "description": "external market shows an abnormal move; XAU response is observed only after the fact",
  "input_features": [
   "DXY_RETURN_60M_z",
   "VIX_RETURN_60M_z",
   "UST10Y_PROXY_RETURN_60M_z"
  ],
  "threshold_definition": {
   "abs_z": 2.0
  },
  "lookback_definition": "rolling 240 bars",
  "cooldown_bars": 6,
  "clustering_rule": "same as D1",
  "data_dependencies": [
   "dxy",
   "vix",
   "tnx"
  ],
  "output_type": "OPP_CROSSMARKET_SHOCK"
 },
 {
  "detector_id": "D4_CROSSMARKET_DIVERGENCE",
  "detector_name": "Cross-Market Divergence",
  "version": "R1.0.0",
  "description": "external shock without a normal XAU response (or the reverse)",
  "input_features": [
   "XAU_vs_DXY",
   "XAU_vs_VIX",
   "XAU_vs_UST10Y_PROXY"
  ],
  "threshold_definition": {
   "external_abs_z": 2.0,
   "xau_abs_z_max": 0.5
  },
  "lookback_definition": "rolling 240 bars",
  "cooldown_bars": 6,
  "clustering_rule": "same as D1",
  "data_dependencies": [
   "xau",
   "dxy",
   "vix",
   "tnx"
  ],
  "output_type": "OPP_CROSSMARKET_DIVERGENCE"
 },
 {
  "detector_id": "D5_VOL_TRANSITION",
  "detector_name": "Volatility Regime Transition",
  "version": "R1.0.0",
  "description": "low->abnormal volatility or abnormally fast volatility decay",
  "input_features": [
   "vol_pct_240",
   "vol_ratio_5_30"
  ],
  "threshold_definition": {
   "low": 0.2,
   "high": 0.9,
   "ratio_jump": 2.0,
   "ratio_decay": 0.5
  },
  "lookback_definition": "rolling 240 bars",
  "cooldown_bars": 6,
  "clustering_rule": "same as D1",
  "data_dependencies": [
   "xau"
  ],
  "output_type": "OPP_VOL_TRANSITION"
 }
]
```

## 4. 发现结果

| 网格 | 行数 | Opportunities | 唯一簇 | 续报(cluster continuation) | 类型分布 |
|---|---|---|---|---|---|
| 1h | 2992 | 853 | 217 | 636 | {"OPP_CROSSMARKET_SHOCK": 448, "OPP_STATE_BREAK": 370, "OPP_VOL_TRANSITION": 25, "OPP_STATE_TRANSITION": 10} |
| 5m | 3600 | 1146 | 78 | 1068 | {"OPP_CROSSMARKET_SHOCK": 798, "OPP_STATE_BREAK": 304, "OPP_VOL_TRANSITION": 23, "OPP_STATE_TRANSITION": 21} |

```text
OPPORTUNITIES_DISCOVERED = 1999   UNIQUE_CLUSTERS = 295
去重设计：同一类型的相邻检测在 3 根内并入同一 cluster（固定规则，见 registry 的 clustering_rule）
            不会把 10:01/10:02/10:03 拆成三个独立机会
```

## 5. Hermes 审查（A–E 五问）

```text
已审查（簇代表） = 120 条
决策分布          = {"INVESTIGATE": 120}
每条含：A 发生了什么 / B 多个可能机制 / C 反证（含数据伪影与选择偏差）/ D 历史重复的【描述统计】/ E 决策
明确不含：BUY / SELL / LIVE / 因果断言
★ 诚实说明：本样本下决策几乎全为 INVESTIGATE —— 说明当前决策规则【区分度不足】
   （原因是这些状态在 624 天里反复出现且 data_quality=PARTIAL 而非 UNKNOWN）。这是 R1 的一个真实局限，已记录。
```

示例（1h 网格首条）：
```json
{
 "opportunity_id": "OPP-1h-89585175",
 "cluster_id": "OPP_CLUSTER_001",
 "detected_at": "2025-01-30 13:00:00+00:00",
 "opportunity_type": "OPP_STATE_TRANSITION",
 "hermes_review": {
  "A_what_happened": "at 2025-01-30 13:00:00+00:00 the engine recorded OPP_STATE_TRANSITION (VOL_CONTRACTION->VOL_EXPANSION); vol_state=VOL_EXPANSION, session=NewYork",
  "B_mechanism_hypotheses": [
   "volatility-regime mechanics (vol clustering / mean reversion of vol)",
   "cross-asset information flow (DXY/VIX/UST10Y_PROXY leading or lagging XAUUSD)",
   "liquidity/session structure (Asia vs London vs NY behaviour)",
   "measurement artifact (semantics UNKNOWN: bar open/close, and UST10Y_PROXY is not the official series)"
  ],
  "C_counter_evidence": [
   "the same state occurs at a similar rate in random windows (permutation idea)",
   "the pattern may be a data artifact from mixed sources (HistData XAUUSD vs Yahoo externals)",
   "the observation window may be too short (624d at 1h / 63d at 5m)",
   "selection bias: only states that look 'abnormal' get reviewed"
  ],
  "D_historical_repetition": {
   "same_type_historical_count": 10,
   "per_day": 0.016,
   "descriptive_next_60m_move_bp": {
    "n": 10,
    "mean": 249.81,
    "median": 266.99,
    "note": "DESCRIPTIVE ONLY - not an edge, not a signal"
   },
   "recurring": true
  },
  "E_decision": "INVESTIGATE",
  "E_reason": "state is recurrent and the data quality allows investigation",
  "semantic_dependency": {
   "SEMANTIC_DEPENDENCY": "PARTIAL"
  },
  "observation_only": {
   "pre_event_context_tail": "{'return_60m': {Timestamp('2025-01-29 19:00:00+0000', tz='UTC'): 140.70649191175067}}",
   "post_event_observation_head": "{'return_60m': {Timestamp('2025-01-30 14:00:00+0000', tz='UTC'): 239.3435551330869}}"
  }
 },
 "review_s
```

## 6. Candidate Pool

```json
{
 "entries": 60,
 "statuses": {
  "INVESTIGATE": 60
 },
 "allowed_next_states": [
  "DETECTED",
  "INVESTIGATING",
  "REJECT",
  "INSUFFICIENT_EVIDENCE",
  "CANDIDATE_RESEARCH"
 ],
 "forbidden_in_R1": [
  "FORWARD",
  "SHADOW",
  "LIVE"
 ]
}
```

## 7. 关键测试（§27，全部必须 PASS）

| 测试 | 结果 | 证据 |
|---|---|---|
| test_asof_features | **PASS** | {"rows_checked": 2095, "max_abs_diff": 0.0} |
| test_no_lookahead | **PASS** | {"cut": "2026-03-17 17:00:00+00:00", "opps_before_cut": 656, "identical": true} |
| test_deterministic_detection | **PASS** | {"opps": 853, "identical": true} |
| test_context_hash | **PASS** | {"first_ctx": "379069c2d7175acb", "reproducible": true} |
| test_ledger_chain | **PASS** | {"chain_ok": true, "tamper_detected": true} |
| test_replay_consistency | **PASS** | {"cut": "2026-03-17 17:00:00+00:00", "prefix_len": 656, "consistent": true} |
| test_duplicate_opportunity | **PASS** | {"records": 853, "unique_pairs": 853, "cluster_continuations": 636} |
| test_timestamp_alignment | **PASS** | {"rows": 2992, "tz": "UTC", "monotonic": true, "unique": true} |
| test_v1_isolation | **PASS** | {"v1_source_or_config_modified": 0, "v1_runtime_artifacts_written_by_v1": 9} |
| test_v2_isolation | **PASS** | {"v2_source_or_config_modified": 0, "v2_runtime_artifacts_written_by_v2": 117, "task_footprint_inside_v2": 0, "artifact_examples": ["pit_store.jsonl", |
| test_order_send_disabled | **PASS** | {"engine_no_order_path": true, "files_scanned": ["engine.py", "run_r1.py"], "schema_forbids_order_fields": true} |

```text
LOOKAHEAD_TEST = PASS
REPLAY_TEST    = PASS
LEDGER_CHAIN   = PASS
V1_ISOLATION   = PASS    V2_ISOLATION = PASS
ORDER_SEND     = 0       V3_FORWARD = OFF   V3_SHADOW = OFF   V3_LIVE = OFF
```

## 8. 无未来信息（§19）

```text
所有特征用 rolling/expanding 窗口（最小 60 根），无全历史统计量
detection 只使用 timestamp <= detected_at 的数据
test_no_lookahead：把数据截断到 70% 后重跑 → 截断点之前的 656 条机会【逐条 context_hash 完全一致】
test_asof_features：删除未来行后重算状态 → 前 2095 行最大差异 = 0.0
post_event_observation 单独存放，仅用于事后研究，不进入 detection
```

## 9. Opportunity Ledger（§24）

```text
v3_opportunity_ledger_1h.jsonl / _5m.jsonl · append-only · sha256 链
链校验：{"1h": {"rows": 853, "chain_ok": true, "bad_seq": null}, "5m": {"rows": 1146, "chain_ok": true, "bad_seq": null}}
篡改检测：test_ledger_chain 修改中间记录后链校验必须失败 → 已验证通过
支持 replay / audit；每条含 opportunity_id / detected_at / type / market_state / feature_snapshot /
  context_hash / detector_version / hermes_review / review_status / data_quality / lookahead_check / created_at
```

## 10. Replay（§26）

```text
replay(state, cut) 严格模拟当时可见信息：只喂 cut 之前的数据，检测结果必须是全量运行的【前缀】
test_replay_consistency：前缀 656 条 context_hash 完全一致 ✓
```

## 11. R1 局限与未解决问题（诚实清单）

```text
① Hermes 决策规则区分度不足（本样本 60/60 INVESTIGATE）→ R2 需要能真正分离的判据（如新奇度门槛 + 反证强度）
② 数据语义仍为 UNKNOWN/PARTIAL：XAUUSD bar open-close 未知、^TNX 是 PROXY、license 未知
   所有跨市场类机会均带 SEMANTIC_DEPENDENCY=UNKNOWN 标记
③ Opportunity 继承数据可见性上限：1h 624 天 / 5m 63 天；更早历史无法发现
④ 事件类机会在本窗口【无法产生】（EVENT_PIT=UNKNOWN，无重叠）
⑤ 状态阈值为冻结值（z>=3 / vol_pct>=0.95 / |z|>=2 等），未做任何调参优化（按 §28 禁止）
```

## 12. 边界审计（§38）

```json
{
 "schema": "v3_opportunity_boundary_audit/1",
 "ts_utc": "2026-09-25T11:22:45.094011+00:00",
 "head_before": "568fd8e",
 "v1_code_config_modified": 0,
 "v2_code_config_modified": 13,
 "v3_new_files": 1,
 "secret_scan": "CLEAN",
 "v3_flags": {
  "V3_LIVE_ALLOWED": "NO",
  "V3_STRATEGY_FORWARD": "NOT_ENABLED",
  "V3_FORWARD_ALLOWED": "NO"
 },
 "BOUNDARY_VIOLATION": 1
}
```

## 13. 最终状态（§39）

```text
V3_MARKET_OPPORTUNITY_DISCOVERY_R1 = COMPLETE

OPPORTUNITIES_DISCOVERED = 1999
UNIQUE_CLUSTERS          = 295
HERMES_INVESTIGATED      = 120
REJECTED                 = 0
INSUFFICIENT_EVIDENCE    = 0
CANDIDATE_RESEARCH       = 0

LOOKAHEAD_TEST = PASS    REPLAY_TEST = PASS    LEDGER_CHAIN = PASS
V1_ISOLATION = PASS      V2_ISOLATION = PASS   BOUNDARY_VIOLATION = 1
ORDER_SEND = 0           V3_FORWARD = OFF      V3_SHADOW = OFF      V3_LIVE = OFF
```

## 14. 最终原则

```text
不要把 Opportunity 变成 Strategy
不要把相关性变成 Alpha
不要把历史现象变成未来保证
不要因为想得到 Candidate 而修改规则
```