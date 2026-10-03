# V1-R2 Phase C1 — Market Reading & Forecast Blind Validation R1

## 1. Label Unification (the C1 gate)
- LABEL_ONTOLOGY / LABEL_MAPPING / LABEL_INTEGRITY = **PASS**；10 项标签完整性测试全过 → 才允许跑预测（§43）。
- label_ontology_hash `8d38209daa7df892` / label_mapping_hash `21e0f842edc14f6f` / selection_hash `e288dc4c74008bea`（运行前冻结）。
- Legacy→Canonical 映射 13 条；`BREAKOUT_FAILURE` 统一 FAILED_BREAK/BREAK_FAIL/FAILED_BREAKOUT。

## 2. Blind Test
- 样本 200（预注册 seed 20260927，分层 REGIME×PRICE_STRUCTURE，purge 10，horizon 8 bars）。
- forecast_hash（Reveal 前冻结）`cd21008d11c0f512`；Reveal 使用**同一** ontology。

## 3. Evaluation
- relation 分布 {"RELATED": 106, "EXACT": 18, "UNKNOWN": 76}
- STATE_EXACT 0.09 / HIERARCHICAL 0.09 / DIRECTION 0.69 / INVALIDATION 0.07

## 4. Baselines & Ablation
- B0 0.17 / B1 0.14 / B2 0.09
- ablation {"A0 PRICE_STRUCTURE": 0.09, "A1 + MOMENTUM": 0.09, "A2 + CANDLE": 0.13, "A3 + MARKET_BEHAVIOR": 0.17, "A4 + MECHANISM": 0.09, "A5 + MULTI_TIMEFRAME": 0.085}

## 5. Capability Matrix
- {"MARKET_PERCEPTION": "SUPPORTED", "MARKET_READING": "SUPPORTED", "CANDLE_READING": "SUPPORTED", "PRICE_STRUCTURE": "SUPPORTED", "MARKET_BEHAVIOR": "UNSUPPORTED", "MARKET_MECHANISM": "SUPPORTED", "MULTI_TIMEFRAME": "WEAK", "STATE_RECOGNITION": "UNSUPPORTED", "STATE_TRANSITION": "UNSUPPORTED", "NEXT_STATE_FORECAST": "UNSUPPORTED", "DIRECTION_FORECAST": "SUPPORTED", "TIMING_FORECAST": "INCONCLUSIVE", "COUNTER_EVIDENCE": "WEAK", "INVALIDATION": "UNSUPPORTED"}

## 6. Audits
- LOOKAHEAD/ANTI_HINDSIGHT/REPLAY/DETERMINISTIC/SHUFFLE = PASS（详见 audit/）。

## 7. Casebook
- BEST 10 / WORST 10 / AMBIGUOUS 10（自动选取，无人工挑选）。

## 8. Limitations
- 样本仅 3 个日历日；OOS 能力有限。
- 预测器为**确定性规则**（非学习模型）；机制/多周期为规则确认，非统计验证。
- `MULTI_TIMEFRAME` / `COUNTER_EVIDENCE` / `TIMING_FORECAST` 仍为 WEAK/INCONCLUSIVE。

## 9. Safety
- ORDER_SEND=0 / ORDER_CHECK=0 / BROKER_WRITE=0；FORWARD/SHADOW/LIVE=OFF；engine/execution/risk/order logic 未改；GIT_COMMIT=NONE。
