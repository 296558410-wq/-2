# REPLAY_REPORT — 修改前后 Replay 与运行验证

## 1. Ledger（未改动）
| 时刻 | sha256(前16) | 行数 |
|---|---|---|
| 修改后 / 周期前 | `9b8b51c5dc774454` | **12** |
| 周期后 | `9b8b51c5dc774454` | **12** |

⇒ 本次代码/配置修改**未触碰账本**；历史 ledger 未被删除/重写（append-only 保持）。

## 2. 运行验证（V2 不停机）
- 触发 V2 调度入口 `runtime/v2_scheduled_cycle.py` 一次：
  - `returncode = 0`
  - stdout: `{"skipped":"MARKET_CLOSED","observe_only":true,"dry_run":false,"agent1":true,"agent2":true,"errors":[],"window":"2026-10-02T23:00:00+00:00"}`
  - stderr: 空
- `state/v2_run_health.json`：`run_status=RUNNING`、`blocked=null`、`scheduler=DIRECT_WINDOWS_TASK`、`llm_dependency=false`、`cycle_result=MARKET_CLOSED_SKIP`。

## 3. Shadow / Discovery / Outcome Replay 一致性
| 组件 | 结论 |
|---|---|
| Discovery（reference vs 新） | 120/120 周期逐周期可比；**选择改变 0**（`picks_changed=0`）；输入为 PIT as-of 快照 |
| Outcome engine | 360/360 `OK`；四档 horizon 完整率 1.0；PIT（仅用 decision 之后数据） |
| Shadow 决策（三侧） | reference 复现生产 **120/120 = 100%**；`true_llm_agent = LLM_UNAVAILABLE`（未静默退化） |

## 4. `order_send = 0` 证据
- 本任务所有脚本**无 `order_send` / `order_check` 调用**；MT5 仅 `copy_rates_range`（读取）与 `initialize/shutdown`。
- V2 周期因**休市**走 `OBSERVE_ONLY`，未进入执行分支；账户/持仓未变。

## 5. 结论
**修改前后 replay 一致、账本未变、V2 继续运行、无真实订单。**
