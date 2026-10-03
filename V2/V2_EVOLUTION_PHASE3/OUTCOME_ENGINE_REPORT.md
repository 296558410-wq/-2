# OUTCOME_ENGINE_REPORT — 任务 C：Outcome 闭环（正式只读研究组件）

组件：`shadow_evolution/outcome_engine.py`（新，只读）· 输入 `TRUE_AGENT_DECISIONS.jsonl` · 输出 `OUTCOME_ENGINE.jsonl` + `_outcome_engine_stats.json`。

## 1. 记录字段（每个可评估 decision）
`shadow_side` · `cycle` · `ts_utc` · `decision` · `opportunity` · `direction` · `entry_ref` ·
`future_return{+15m,+30m,+60m,+240m}` · `mfe_bps` · `mae_bps` · `tp_sl_path{applicable,first_touch,touch_min,window_min,sl,tp}` ·
`horizon_complete{...}` · `outcome_status` · `bars_n`

## 2. 严格性
- **PIT**：只用 decision 时刻**之后**的 M1 bar（`copy_rates_range(t, t+245m)`）。
- **不补造休市数据**：某 horizon 的 bar 不足 ⇒ 该 horizon `horizon_complete=false`，整体标 `PARTIAL_DATA_GAP`。
- **不产生交易**：仅 MT5 只读（无 order_check/order_send）。
- `tp_sl_path` 仅当 plan 定义方向+SL/TP 时 `applicable=true`（WAIT/LLM_UNAVAILABLE 侧记 `applicable=false`）。

## 3. 结果（360 行 = 120 周期 × 3 侧）
| 状态 | 计数 |
|---|---|
| `OK` | **360 / 360** |
| `PARTIAL_DATA_GAP` | 0 |
| horizon 完整率 | +15m **1.0** · +30m **1.0** · +60m **1.0** · +240m **1.0** |

## 4. 中位汇总（bps）
| 侧/决策 | n | +15m | +30m | +60m | +240m | MFE | MAE | TP/SL first-touch |
|---|---|---|---|---|---|---|---|---|
| reference_rules / TRADE | 10 | 8.7 | 6.1 | −85.3 | +90.7 | 117.2 | −107.6 | TP 2 · SL 8 |
| hermes_heuristic / TRADE | 10 | 8.7 | 6.1 | −85.3 | +90.7 | 117.2 | −107.6 | TP 2 · SL 8 |
| reference_rules / WAIT | 110 | 9.5 | 12.1 | 109.4 | −73.3 | — | — | n/a |
| hermes_heuristic / WAIT | 108 | 10.7 | 13.3 | 110.6 | −72.2 | — | — | n/a |
| hermes_heuristic / REJECT | 2 | 4.1 | 6.7 | 103.9 | −78.7 | — | — | n/a |
| true_llm_agent / LLM_UNAVAILABLE | 120 | 6.0 | 8.6 | 105.8 | −76.9 | — | — | n/a |

## 5. 结论
- **Decision → Outcome 闭环成立**：每条 decision 均有 outcome 记录（360/360 OK，四档 horizon 全完整）。
- 事实级观察（**不作因果、不调参**）：10 个执行候选的 MFE 中位 117.2bps / MAE 中位 −107.6bps、first-touch **TP 2 · SL 8**。
- `+240m` 在本轮 **完整可得**（此前一版因窗口设置标 n/a；本组件统一 `WIN=245m` 并显式记录完整性）。
- 研究结论（是否可用）**不在本任务范围**；本组件只保证"可评估 decision → outcome 链"完整、PIT、可审计。
