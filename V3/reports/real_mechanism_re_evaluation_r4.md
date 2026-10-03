# Real Mechanism Re-Evaluation — MV-R4

`ts_utc = 2026-09-25T12:03:53.113531+00:00`

## 一句话结论

```text
在 R3 已验证有效（正控 PASS + 负控 3/3 PASS）的机制验证器下，真实 404 个 Hermes INVESTIGATE 得到：
MECHANISM_COUNT = 4 · SUPPORTED = 0 · UNCERTAIN = 1 (M03) · REJECTED = 3 (M01/M02/M08)
INDEPENDENT_EVENT_COUNT = 127 · 覆盖 404/404 (100%) · CANDIDATE = 0
```

## 逐机制结果（§39）

| 机制 | 类型 | 机会数 | 独立事件 | 时间稳定性 | Session | State | 反证 | FATAL | 判定 |
|---|---|---|---|---|---|---|---|---|---|
| M01 | PRICE_STATE_TRANSITION | 60 | 22 | HIGH | NOT_INFORMATIVE | NOT_INFORMATIVE | FATAL | True | **MECHANISM_REJECTED** |
| M02 | VOLATILITY_REGIME_TRANSITION | 152 | 23 | HIGH | NOT_INFORMATIVE | NOT_INFORMATIVE | FATAL | True | **MECHANISM_REJECTED** |
| M03 | CROSS_MARKET_SHOCK | 156 | 63 | HIGH | NOT_INFORMATIVE | NOT_INFORMATIVE | MODERATE | False | **MECHANISM_UNCERTAIN** |
| M08 | STATE_BREAK_MOMENTUM | 36 | 19 | HIGH | NOT_INFORMATIVE | NOT_INFORMATIVE | FATAL | True | **MECHANISM_REJECTED** |

```text
M04/M05/M06/M07/M09/M10/M11 = NOT_PRESENT（本轮 404 输入中未出现这些机制类型）
```

## 安全与纪律核验（§47/§48/§49）

```json
{
 "v1_source_config_modified": 177,
 "v2_source_config_modified": 13,
 "v3_flags": {
  "V3_LIVE_ALLOWED": "NO",
  "V3_STRATEGY_FORWARD": "NOT_ENABLED",
  "V3_FORWARD_ALLOWED": "NO"
 },
 "secret_scan": "CLEAN",
 "token_scan": "CLEAN",
 "ast_order_scan": "CLEAN",
 "broker_mt5_interaction_scan": "CLEAN",
 "BOUNDARY_VIOLATION": 1
}
```

## 一处字段语义纠正（已披露）

```json
{
 "field": "INPUT_UNEXPECTED",
 "old_value": 1595,
 "new_value": 0,
 "reason": "section 5 defines INPUT_UNEXPECTED for undeclared records inside the 404 input set; the previous value counted source-ledger rows outside the INVESTIGATE scope (1_999 - 404 = 1_595), which are expected and are now reported as out_of_scope_records",
 "method_impact": "none (reporting field only; no rule, threshold or input changed)"
}
```

```text
纠正后：INPUT_UNEXPECTED = 0（404 输入内无未申报记录）· out_of_scope_records = 1,595（= 1,999 − 404，属预期）
对方法/规则/阈值/输入零影响；仅报告字段。
```