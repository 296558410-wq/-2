# V1-R2 Phase B-R8｜Feature Dependency Collapse — 独立信息轴审计

## 1. Executive Summary

- 数据集：TICK_ONLY（`m15_tick_bid.parquet`, sha256 `aafbb448…`），PRICE_SOURCE=BID 不变。
- PIT：142 决策 → VALID_PIT_ALIGNED=140 / DUPLICATE=2 / OUT_OF_DATASET=0 / ALIGNMENT_ERROR=0。
- Registry：`v1r2-r3` hash `014de166…` 校验 PASS，未生成新 registry。
- **71 UNKNOWN 的压缩结果**：Feature 均值 9.04 → 独立信息轴均值 3.85。
- **PRICE_STRUCTURE 轴确认**：LEVEL/TOUCH/BREAK/COUNTER_BREAK_RISK/FAILED_EVENT = **1 个信息轴**。
- **UNKNOWN 数量不变**：71 → 71。Collapse 消除的是重复投票，不是门条件。
- 下一阶段方向：**PRICE_STRUCTURE_STATE_MODEL**。

## 2. Input Integrity

- DATASET_VARIANT=TICK_ONLY；bars=1328；决策 142；PIT 通过。
- B-R4 SOURCE_DATA_CONFLICT 保持：SOURCE_DATA_CONFLICT。

## 3. Feature Lineage

- **REGIME** ← ATR_PCTL, ER10, SLOPE5, VEL4, MA20  `research/hermes/trader_v1/v1_r2_prediction_upgrade/_v1r2_phaseB_R1.py L151-166` axis=REGIME
- **LEVEL** ← PIVOT_HIGH/LOW (h/l fractal L2R2), RANGE_HIGH/LOW (96-bar)  `research/hermes/trader_v1/v1_r2_prediction_upgrade/_v1r2_phaseB_R1.py L84-96,L188` axis=PRICE_STRUCTURE
- **TOUCH** ← LEVEL.touch_events_240, LEVEL.fail_rate, LEVEL.pen_last, LEVEL.rec_ok/fail, LEVEL.last_touch_i  `research/hermes/trader_v1/v1_r2_prediction_upgrade/_v1r2_phaseB_R1.py L180-194` axis=PRICE_STRUCTURE
- **BREAK** ← LEVEL(touch_events_240,rec_ok,rec_fail,fail_rate,pen_last,last_touch_i,dist_atr), ABSORPTION, VEL4+LEVEL.side  `research/hermes/trader_v1/v1_r2_prediction_upgrade/_v1r2_phaseB_R1.py L204-221 (all groups inside `if nl:` L205)` axis=PRICE_STRUCTURE
- **MOMENTUM** ← VEL4, ACC, RNG_EXP  `research/hermes/trader_v1/v1_r2_prediction_upgrade/_v1r2_phaseB_R1.py L225-236` axis=MOMENTUM
- **ABSORPTION** ← EFF3/EFF3_prev, ACT3/ACT3_prev, LEVEL.pen_last, LEVEL.dist_atr  `research/hermes/trader_v1/v1_r2_prediction_upgrade/_v1r2_phaseB_R1.py L198-201` axis=ABSORPTION
- **LIQUIDITY** ← -  `NOT EMITTED by engines_v2` axis=LIQUIDITY_UNAVAILABLE
- **FAILED_EVENT** ← close[i-1], close[i], LEVEL.price, ATR20  `research/hermes/trader_v1/v1_r2_prediction_upgrade/_v1r2_phaseB_R1.py failed_event block (`if nl and i>=3`)` axis=PRICE_STRUCTURE
- **TRANSITION** ← REGIME, LEVEL relation, TOUCH, ABSORPTION, MOMENTUM, BREAK  `research/hermes/trader_v1/v1_r2_prediction_upgrade/_v1r2_phaseB_R1.py transition block` axis=DERIVED_OUTPUT
- **DATA_QUALITY** ← -  `not implemented` axis=UNAVAILABLE

## 4. Raw Input Lineage

- RAW_SOURCE_COUNT_FOR_STATE_MACHINE = **1**（同一条 bid OHLC 路径；ask/spread 存在但状态机不使用）。
- 所有中间量（ATR20/VEL4/ACC/EFF3/ACT3/ER10/RNG_EXP/ATR_PCTL）均为该路径的窗口变换。

## 5. PRICE_STRUCTURE Collapse

- 成员 ['LEVEL', 'TOUCH', 'BREAK', 'COUNTER_BREAK_RISK', 'FAILED_EVENT']，逐项验证 level-conditioned：全部 True；无 level 的行中 `break!=LOW` = 0。
- **PRICE_STRUCTURE_INFORMATION_AXES = 1**。
- price_structure_state 分布（140 决策）：{"PENETRATION": 79, "FAILED_BREAK": 16, "BREAK_CONFIRMED": 7, "APPROACH": 37, "BREAK_ATTEMPT": 1}

## 6. MOMENTUM Dependency

- {"total": 1, "members": ["MOMENTUM"], "raw_dependencies": ["VEL4", "ACC", "RNG_EXP", "ATR20", "OHLC_15M"], "restatements": ["COUNTER_DECELERATION"], "shared_with_REGIME": ["VEL4", "ATR20", "OHLC_15M"], "classification": "single axis (MOMENTUM) with intra-family restatement"}

## 7. REGIME Dependency

- REGIME↔MOMENTUM = **PARTIALLY_DEPENDENT**；共享 OHLC_15M close, ATR20, VEL4；REGIME 独有 ATR_PCTL, ER10, SLOPE5；MOMENTUM 独有 ACC, RNG_EXP。

## 8. COUNTER Dependency

- 5 个 counter 组的 lineage 分类：
  - COUNTER_BREAK_RISK → PRICE_STRUCTURE_DERIVED（复述 PRICE_STRUCTURE）
  - COUNTER_DECELERATION → MOMENTUM_DERIVED（复述 MOMENTUM）
  - COUNTER_EXHAUSTION → PRICE_STRUCTURE_DERIVED（复述 PRICE_STRUCTURE）
  - COUNTER_ABSORPTION → ABSORPTION_DERIVED（复述 ABSORPTION）
  - COUNTER_FAILED_EVENT → FAILED_EVENT_DERIVED（复述 PRICE_STRUCTURE）
- 观测频次（71 UNKNOWN）：{"COUNTER_BREAK_RISK": 49, "COUNTER_DECELERATION": 27, "COUNTER_FAILED_EVENT": 6, "COUNTER_ABSORPTION": 2, "COUNTER_EXHAUSTION": 1}

## 9. ABSORPTION Dependency

- {"members": ["ABSORPTION"], "raw_dependencies": ["EFF3", "EFF3_prev", "ACT3", "ACT3_prev", "ATR20", "TR", "LEVEL.pen_last", "LEVEL.dist_atr"], "absorption_vs_price_structure": "PARTIALLY_DEPENDENT (STRONG uses level penetration)", "absorption_vs_momentum": "PARTIALLY_DEPENDENT (EFF3 is an efficiency transform of the same close path as VEL4)", "absorption_vs_regime": "PARTIALLY_DEPENDENT (ACT3 = TR ratio, same family as ATR_PCTL/RNG_EXP)", "proxy": "PROXY_BAR", "direct_order_flow": false, "verdict": "primarily a re-expression of momentum-efficiency + volatility + level penetration -> NOT a clean independent axis"}

## 10. FAILED_EVENT Dependency

- FAILED_EVENT = **DERIVED_FROM_PRICE_STRUCTURE**（`if nl` 守卫；突破尝试+收复同一 level）。
- LIQUIDITY = DATA_LIMITED（engine 无该字段，未虚构依赖）。

## 11. 71 UNKNOWN Reclassification

- 轴数分布：{"1": 0, "2": 0, "3+": 71}（分母 71）
- 重分类：{"TRUE_MULTI_AXIS_CONFLICT": 0, "SINGLE_AXIS_BOUNDARY": 47, "DERIVED_CONFLICT": 13, "INFORMATION_INSUFFICIENT": 0, "UNKNOWN": 11}（分母 71）

## 12. Counterfactual Audit

- `COUNTERFACTUAL_ONLY = TRUE`，仅诊断；未写 registry，未改 engine.py。
- 单轴即可解释的 UNKNOWN：**64/71**；阻断轴 ≥2 的：**0/71**。

## 13. HOLD_QUIET

- 总数 32；仅缺 break LOW/NORMAL 15；VERDICT = **PRICE_STRUCTURE_BOUNDARY**。

## 14. REVERSION

- REVERSION_REVERSAL 20；涉及独立轴数 4；分类 {"SINGLE_AXIS_BOUNDARY": 20}。

## 15. BREAK_PASSTHROUGH

- 总数 7；CLASS = **PRICE_STRUCTURE_INTERNAL_STATE**。

## 16. Information Axis Distribution

- {"1": 0, "2": 0, "3+": 71}（n/71）

## 17. Before/After Complexity

- 证据标签均值 9.04 → 独立轴均值 3.85；UNKNOWN 71 → 71（不变）。

## 18. Limitations

- RAW 输入重叠近乎 100%（同一 bid 路径），因此「独立轴」是**变换维度**而非来源维度。
- ABSORPTION 为 PROXY_BAR，无 DOM/成交方向；LIQUIDITY 无字段。
- 轴数口径为 lineage-based；统计量（Cramér's V / MI）仅辅助，未用于判定。
- 样本仅 3 个日历日（09-23…09-25）。

## 19. Next Research Candidate

- **PRICE_STRUCTURE_STATE_MODEL**：先把 PRICE_STRUCTURE 内部状态（{'PENETRATION': 79, 'FAILED_BREAK': 16, 'BREAK_CONFIRMED': 7, 'APPROACH': 37, 'BREAK_ATTEMPT': 1}）显式分层，再谈 counter/priority。

## 20. Safety

- ORDER_SEND=0 / ORDER_CHECK=0 / BROKER_WRITE=0；FORWARD=OFF / SHADOW=OFF / LIVE=OFF。
- ENGINE_PY_MODIFIED=0 / REGISTRY_MODIFIED=0 / PARAMETER_MODIFIED=0 / DIRECTION_MAPPING_MODIFIED=0。
- FUTURE_RETURN_USED=NO / PNL_USED=NO / WIN_RATE_USED=NO；GIT_COMMIT=NONE。
