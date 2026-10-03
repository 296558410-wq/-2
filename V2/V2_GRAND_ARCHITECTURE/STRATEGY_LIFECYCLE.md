# STRATEGY_LIFECYCLE

## 状态机
`RESEARCH → SHADOW → CANDIDATE → VALIDATED → ACTIVE → DEGRADED → RETIRED`。
不得因单次盈利直接 ACTIVE；晋升需证据；旧策略不删除（可由市况变化 `RESEARCH → SHADOW` 重新验证）。

## 本阶段状态计数
`{"RESEARCH": 17}`

## 接入 Historical Strategy Decay Lab（Section 七）
已消费（未重跑）`V2_HISTORICAL_STRATEGY_DECAY_LAB`：
- 真实含交易系统：['V1_OLD', 'V1_NEW', 'trader_v1:v1_upgrade']
- V1_OLD: {'label': 'V1 old (Hermes LLM plan engine)', 'magic': 90002, 'real_closed_trades': 109, 'is_hermes_alpha': True}
- V1_NEW: {'label': 'V1 upgrade / BASELINE_CONTROL', 'magic': 90011, 'real_closed_trades': 32, 'is_hermes_alpha': False}
- 该 lab 结论：证据不足；fresh-start/decay/reset/48h 均 INCONCLUSIVE / NOT_ESTABLISHED。

持续记录 system_age / strategy_age / regime_age / performance_age / confidence_age，
监测 Birth/Early/Stable/Degradation/Exhaustion/Recovery/Retirement。
**不预设衰竭时间，由数据识别**（本阶段样本不足以识别，如实标注）。
