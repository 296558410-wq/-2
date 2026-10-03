# V1-R2 Phase B-R13｜Incremental Prediction Measurement Calibration

## 1. Executive Summary
- 主指标改为**样本外 log-loss 差（bits）**；模型固定 multinomial logistic（C=1.0），expanding walk-forward，PURGE=480 / EMBARGO=1。
- 置换 null **200** 次，**每次重新 fit 两个模型**（不是只重算有偏熵）。
- **MEASUREMENT_POWER = MEASUREMENT_POWER = SUFFICIENT**（5 个候选中 NULL_SEPARATION 通过数 = 3/5）
- CONFIRMED_CAPABILITIES = NONE
- WEAK_CAPABILITIES = ['FAILED_EVENT', 'MOMENTUM', 'MOMENTUM_TRANSITION']
- REJECTED_CAPABILITIES = ['REGIME', 'LIQUIDITY_PROXY']
- BEST_SUPPORTED_CAPABILITY = NONE
- PROMOTION_CANDIDATE = NONE；FORMAL_RULE_CHANGE = NOT_ALLOWED

## 2. Target
- `NEXT_BAR_GEOMETRY_STATE` ∈ {UP_BREAK, INSIDE, DOWN_BREAK}；FEATURE(t) → TARGET(t+1)，严格无未来信息。

## 3. Model
- 固定 multinomial logistic regression（C=1.0），复杂度不随结果变化；未更换模型。
- LOW_COMPLEXITY_REFERENCE = naive conditional frequency（仅 sanity check）。

## 4. Results
### FAILED_EVENT → **WEAK**
- baseline_logloss=1.26348 | feature_logloss=1.26332 | **ΔLL=0.00016 bits**
- blocks=[0.0001, 0.00025, 0.00014] | worst=0.0001 | train=0.00021 | test=0.00016 | overfit=LOW
- null p95=0.00015 | empirical_p=0.045 | NULL_SEPARATION=PASS
- direction: UP=0.00077 DN=0.00028 → SYMMETRIC

### MOMENTUM → **WEAK**
- baseline_logloss=1.2642 | feature_logloss=1.26348 | **ΔLL=0.00073 bits**
- blocks=[2e-05, 0.00088, 0.00128] | worst=2e-05 | train=0.00189 | test=0.00073 | overfit=LOW
- null p95=0.00042 | empirical_p=0.005 | NULL_SEPARATION=PASS
- direction: UP=0.00367 DN=0.0018 → SYMMETRIC

### MOMENTUM_TRANSITION → **WEAK**
- baseline_logloss=1.2642 | feature_logloss=1.25887 | **ΔLL=0.00534 bits**
- blocks=[0.00539, 0.00535, 0.00527] | worst=0.00527 | train=0.00648 | test=0.00534 | overfit=LOW
- null p95=0.00032 | empirical_p=0.0 | NULL_SEPARATION=PASS
- direction: UP=0.01475 DN=0.01211 → SYMMETRIC

### REGIME → **NOT_SUPPORTED**
- baseline_logloss=1.26369 | feature_logloss=1.26348 | **ΔLL=0.0002 bits**
- blocks=[0.00086, 0.0017, -0.00195] | worst=-0.00195 | train=0.00143 | test=0.0002 | overfit=LOW
- null p95=0.00041 | empirical_p=0.19 | NULL_SEPARATION=FAIL
- direction: UP=0.00127 DN=0.00097 → SYMMETRIC

### LIQUIDITY_PROXY → **NOT_SUPPORTED**
- baseline_logloss=1.26348 | feature_logloss=1.26382 | **ΔLL=-0.00034 bits**
- blocks=[-0.00066, -0.00041, 4e-05] | worst=-0.00066 | train=0.0006 | test=-0.00034 | overfit=LOW
- null p95=0.00049 | empirical_p=0.86 | NULL_SEPARATION=FAIL
- direction: UP=-0.00062 DN=0.00127 → ASYMMETRIC

## 5. Nested Comparisons
- {"M0": 1.2642, "M0+MOMENTUM": 1.26348, "M0+MOMENTUM+MOMENTUM_TRANSITION": 1.25818, "M0+MOMENTUM+MOMENTUM_TRANSITION+REGIME": 1.25806, "M0+FAILED_EVENT": 1.26332, "M0+LIQUIDITY_PROXY": 1.26382}

## 6. Permutation Null
- seed=20260927, permutations=200, method=refit-and-retest

## 7. Replay / Determinism
- 8 截断点；特征与目标逐 bar 因果；模型仅用先验 bar 重训。DETERMINISTIC=PASS。

## 8. Limitations
- 样本 1327 bars / 3 个日历日；PURGE=480 使有效训练量进一步压缩。
- 结论为 **research-only**；未修改任何正式规则。

## 9. Verdict
- **没有 SAupportED 能力**；且测量功效结论见上。按 §33：不应继续增加 Feature，应评估**样本扩充 / 更长历史 / 数据质量**。

## 10. Safety
- ORDER_SEND=0 / ORDER_CHECK=0 / BROKER_WRITE=0；FORWARD=OFF / SHADOW=OFF / LIVE=OFF。
- ENGINE_PY_MODIFIED=0 / REGISTRY_MODIFIED=0 / PARAMETER_MODIFIED=0 / DIRECTION_MAPPING_MODIFIED=0。
- FUTURE_RETURN_USED=NO / PNL_USED=NO / WIN_RATE_USED=NO / TRADE_OUTCOME_USED=NO；GIT_COMMIT=NONE。
