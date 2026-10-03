# V1-R2 Phase B-R12｜Confirmed Predictive Capability Harvest

## 1. Executive Summary
- Baseline = 冻结 V1-R2 state engine（未改）。Primary target = `NEXT_BAR_GEOMETRY_STATE`（非循环）；Secondary = `FROZEN_NEXT_STATE`（循环风险，仅参考）。
- 预注册 ΔH 阈值 **0.05 bits**，null 置换 **200** 次，时间块固定 3 等分。
- TOUCH/LEVEL/PENETRATION/BREAK/COUNTER_BREAK **不作为新候选**（自 B-R8/B-R11 已判定同源）。
- **CONFIRMED_CAPABILITIES = NONE**
- **WEAK_CAPABILITIES = ['FAILED_EVENT', 'MOMENTUM', 'MOMENTUM_TRANSITION', 'REGIME', 'LIQUIDITY_PROXY']**
- **REJECTED_CAPABILITIES = ['COUNTER_EVIDENCE', 'ABSORPTION']**
- **INCONCLUSIVE_CAPABILITIES = NONE**
- **NEXT_FORMAL_CANDIDATE = FAILED_EVENT**

## 2. Baseline
- BASELINE = 当前冻结 V1-R2 state engine（`ns_v3` + `rule_mu`），未做任何修改。
- 所有候选均以 BASELINE vs BASELINE+FEATURE_GROUP 的**条件增量**衡量。

## 3. Information Axes (B-R8 dependency)
- PRICE_STRUCTURE(LEVEL/TOUCH/BREAK/COUNTER_BREAK/FAILED_EVENT) · MOMENTUM · REGIME · ABSORPTION。
- 4 个信息轴 ≠ 4 个独立数据源；原始信息仍为单条 BID OHLC（+ask/spread）。

## 4. Method
- ΔH = H(Y|C) − H(Y|C,X)；C 含 baseline state 与**其它信息轴**（条件增量，§15）。
- null = X 标签置换 200 次，要求 ΔH > null p95。
- 时间稳定性按预注册等三分块；level 类型与方向分别检查。

## 5-11. Candidate Results
### FAILED_EVENT  →  **WEAK**
- ΔH(primary)=0.05062 bits | null p95=0.10915 | NULL=FAIL | CONDITIONAL=PASS
- NON_CIRCULAR=FAIL | TEMPORAL=PASS | DEPENDENCY=ACCEPTABLE
- LEVEL=PASS | DIRECTION=PASS | ΔH(secondary)=0.07361
- reason: increment present but a pre-registered criterion failed: NULL,NONCIRC

### MOMENTUM  →  **WEAK**
- ΔH(primary)=0.19534 bits | null p95=0.28415 | NULL=FAIL | CONDITIONAL=PASS
- NON_CIRCULAR=FAIL | TEMPORAL=PASS | DEPENDENCY=ACCEPTABLE
- LEVEL=PASS | DIRECTION=PASS | ΔH(secondary)=0.2226
- reason: increment present but a pre-registered criterion failed: NULL,NONCIRC

### MOMENTUM_TRANSITION  →  **WEAK**
- ΔH(primary)=0.44553 bits | null p95=0.73833 | NULL=FAIL | CONDITIONAL=PASS
- NON_CIRCULAR=FAIL | TEMPORAL=PASS | DEPENDENCY=ACCEPTABLE
- LEVEL=PASS | DIRECTION=PASS | ΔH(secondary)=0.51534
- reason: increment present but a pre-registered criterion failed: NULL,NONCIRC

### COUNTER_EVIDENCE  →  **NOT_SUPPORTED**
- ΔH(primary)=0.03362 bits | null p95=0.17438 | NULL=FAIL | CONDITIONAL=FAIL
- NON_CIRCULAR=FAIL | TEMPORAL=PASS | DEPENDENCY=ACCEPTABLE
- LEVEL=PASS | DIRECTION=PASS | ΔH(secondary)=0.04684
- reason: no conditional increment (delta_H below threshold / within null)

### REGIME  →  **WEAK**
- ΔH(primary)=0.17576 bits | null p95=0.33679 | NULL=FAIL | CONDITIONAL=PASS
- NON_CIRCULAR=FAIL | TEMPORAL=PASS | DEPENDENCY=ACCEPTABLE
- LEVEL=PASS | DIRECTION=PASS | ΔH(secondary)=0.29775
- reason: increment present but a pre-registered criterion failed: NULL,NONCIRC

### ABSORPTION  →  **NOT_SUPPORTED**
- ΔH(primary)=0.04482 bits | null p95=0.05694 | NULL=FAIL | CONDITIONAL=FAIL
- NON_CIRCULAR=FAIL | TEMPORAL=PASS | DEPENDENCY=ACCEPTABLE
- LEVEL=PASS | DIRECTION=PASS | ΔH(secondary)=0.04844
- reason: no conditional increment (delta_H below threshold / within null)

### LIQUIDITY_PROXY  →  **WEAK**
- ΔH(primary)=0.25528 bits | null p95=0.29362 | NULL=FAIL | CONDITIONAL=PASS
- NON_CIRCULAR=FAIL | TEMPORAL=PASS | DEPENDENCY=ACCEPTABLE
- LEVEL=PASS | DIRECTION=PASS | ΔH(secondary)=0.29081
- reason: increment present but a pre-registered criterion failed: NULL,NONCIRC

## 12. Null / Replay / Determinism
- REPLAY=PASS（8 截断点）; DETERMINISTIC=PASS; NULL=PASS

## 13. Liquidity
- {"DOM": "UNAVAILABLE", "TRADE_DIRECTION": "UNAVAILABLE", "TICK_VOLUME": "all-zero", "LIQUIDITY_WITHDRAWAL": "PROXY", "proxy_used": "bar mean spread from tick bid/ask (DIRECT) + tick count", "spread_available": true, "q33": 0.14000859494720308, "q67": 0.1799999999999872}

## 14. Limitations
- 样本仅 3 个日历日（09-23…09-25）；时间块稳定性功效有限。
- Primary target 为**下一根 bar 的几何状态**（非收益）；未使用任何收益/盈亏/胜率。
- 所有结论为 research-only；正式规则修改**未获授权**。

## 15. Confirmed Capability
- 本轮**未**出现 SUPPORTED 能力；无 PROMOTION_CANDIDATE。下一步按 §23 优先级继续调查 WEAK 项，或研究替代定义。

## 16. Next
- **NEXT_FORMAL_CANDIDATE = FAILED_EVENT**

## 17. Safety
- ORDER_SEND=0 / ORDER_CHECK=0 / BROKER_WRITE=0；FORWARD=OFF / SHADOW=OFF / LIVE=OFF。
- ENGINE_PY_MODIFIED=0 / REGISTRY_MODIFIED=0 / PARAMETER_MODIFIED=0 / DIRECTION_MAPPING_MODIFIED=0。
- FUTURE_RETURN_USED=NO / PNL_USED=NO / WIN_RATE_USED=NO / TRADE_OUTCOME_USED=NO；GIT_COMMIT=NONE。
