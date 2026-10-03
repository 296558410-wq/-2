# V1-R3 HERMES MARKET FORECAST ENGINE — FINAL REPORT

## 任务目标
验证 Hermes 在仅见 PIT 市场上下文时，能否形成优于冻结基线的市场演化预测（State / Transition / Scenario / Direction / Timing / Invalidation / Abstention）。

## 数据输入
XAUUSD M1→M5/M15/H1/H4（2025-01→2026-09-18）；跨市场 DXY/VIX/UST10Y_PROXY_TNX（5m，PROXY，仅 2026-07-17 起；GLD/GC/COT/ETF/新闻 = UNKNOWN，不购买、不扩历史）。

## Context Architecture
7 层 HERMES_MARKET_CONTEXT：L1 PRICE/KLINE(5 TF, 原始几何+序列)、L2 PRICE_STRUCTURE、L3 MARKET_BEHAVIOUR(OBSERVED/DERIVED/INFERRED)、L4 MECHANISM(candidates+反证+invalidation)、L5 STATE_HISTORY、L6 MULTI_TIMEFRAME(不合并)、L7 CROSS_MARKET(PROXY/UNKNOWN 标注) + HISTORICAL_ANALOG(仅状态演化)。context_schema_hash = eeb1621d61c391d1f27c84b9bd40c0cbeeebc15681108d667bc4150114572c08

## Hermes Model
{"registry_id": "v1r3-hermes-model-r1", "model": "deepseek/deepseek-v4-flash", "provider": "custom-yuanyuaicloud-cn", "prompt_hash": "3813c2e323e7e2bb6c265c880701ee635bbcda6da0efa1c647fccc3c1d815ad9", "context_schema_hash": "eeb1621d61c391d1f27c84b9bd40c0cbeeebc15681108d667bc4150114572c08", "temperature": "runtime_default", "seed": "runtime_default", "runtime": "OpenClaw subagent (isolated context), tools disabled for forecast calls", "invocation": "one isolated Hermes call per (timestamp, context_variant); no shared state", "ts_utc": "2026-09-27T13:29:30.907755+00:00"}

## Prompt
冻结于预测之前。prompt_hash = 3813c2e323e7e2bb6c265c880701ee635bbcda6da0efa1c647fccc3c1d815ad9（prompt/hermes_market_forecast_prompt.txt）

## Forecast Schema
§22 全字段；含 primary/alternative/(third) scenario、direction_bias(允许 NO_DIRECTIONAL_EDGE)、time_horizon(允许 TIMING_UNCERTAIN)、supporting/counter evidence、invalidation、change_my_mind、abstain、reasoning_trace、questions A–J。

## Blind Design
Development < 2026-06-01；Blind = 2026-06-01→09-18；确定性抽样（每 3 天 12:00Z）。Hermes 只见 prompt+context；评测器独立。

## Baseline
MAJORITY / PERSISTENCE / PREVIOUS_STATE / SIMPLE_TRANSITION(PIT 学习) / FROZEN_NEXT_STATE_MODEL。

## Results（同一 18 个盲测点）
| model | STATE_acc | TRANSITION_acc | DIRECTION_acc | ABSTENTION | SCENARIO_COVERAGE |
|---|---|---|---|---|---|
| HERMES_FULL | 0.3333 | 0.6111 | 0.3333 | 0.0 | 0.8333 |
| HERMES_PRICE_ONLY | 0.2143 | 0.5294 | 0.4167 | 0.0556 | 0.6667 |
| PERSISTENCE | 0.2778 | None | None | 0.0 | None |
| PREVIOUS_STATE | 0.3889 | None | None | 0.0 | None |
| SIMPLE_TRANSITION | 0.2778 | None | None | 0.0 | None |
| FROZEN_NEXT_STATE_MODEL | 0.3333 | None | None | None | None |

Calibration: {"n": 12, "ECE": 0.1425, "accuracy_covered": 0.3333, "accuracy_full": 0.3333}

## Ablation
信息含量矩阵与 FULL vs PRICE_ONLY 对照见 ablation/ 与 evaluation/（§61）。

## Failure Analysis
未达 SUPPORTED 时：样本（有效 N 小）、上下文层级（跨市场覆盖短）、Prompt、模型、目标定义、或市场本身不可预测，逐一记录于 limitations。

## Replay / Lookahead / Isolation / Safety
REPLAY=PASS · LOOKAHEAD=PASS · V1/V2/V3 ISOLATION=PASS · ORDER_SEND=0 / BROKER_WRITE=0 / FORWARD=OFF / LIVE=OFF；未使用 future_return / PnL / win_rate。

## Final Verdict
ENGINE_STATUS = ENGINE_COMPLETE
HERMES_PREDICTIVE_CAPABILITY = UNSUPPORTED
HERMES_FORECAST_LEVEL = LEVEL_3
STRATEGY_MAPPING_GATE = OPEN
tests pass/fail = 23/0
ledger entries = 38
