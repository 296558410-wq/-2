# MULTI_STRATEGY_REPORT

组合层：Single / EqualWeight / ConfidenceWeight / RegimeWeight / DiversityWeight（权重只用 discovery 固定，OOS 严格）。

## 相关性检查（是否都在赌同一风险因子）
```
{
  "n_strategies_with_trades": 13,
  "corr_mean_offdiag": 0.01901128703134381,
  "corr_max_offdiag": 1.0,
  "same_factor_flag": true
}
```

## 组合结果 (OOS)
```
{
  "single_best_discovery": "SF-RANGE-01",
  "single_best_oos_total": 3.5899999999965075,
  "equal_weight_oos_total": 47.153461538234225,
  "confidence_weight_oos_total": 1.8280449333626247
}
```