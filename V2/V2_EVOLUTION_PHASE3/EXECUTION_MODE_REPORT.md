# EXECUTION_MODE_REPORT — 任务 B：执行模式统一为 `PAPER_LOCAL`

## 1. 修改前（声名与实际不一致）
| 字段 | 值 |
|---|---|
| `execution.execution_mode`（声明） | **BROKER_DEMO** |
| `execution.backend` | fxtm_demo |
| `broker.enabled` / `broker_demo_enabled` | true / true |
| 实际执行后端（`PaperExecutor.backend`） | **paper_local** |
| 实际 run 前缀 | `V2-PAPER-…` |

⇒ **declared(BROKER_DEMO) ≠ actual(paper_local)**（审计确认的歧义）。

## 2. 修改内容（最小、向后兼容）
| # | 文件 | 改动 |
|---|---|---|
| 1 | `execution/paper_executor.py` | 新增 `PAPER_MODES=("PAPER","PAPER_LOCAL")`；`_guard()` 由 `!= "PAPER"` 改为 `not in PAPER_MODES` |
| 2 | `execution/hermes_paper_adapter.py` | `assert_paper_only`/`assert_execution_allowed` 接受 `PAPER_LOCAL`；错误文案更新 |
| 3 | `config/v2_config.json` | `execution_mode: BROKER_DEMO→PAPER_LOCAL`；新增 `declared_mode:"PAPER_LOCAL"`；`backend: fxtm_demo→paper_local`；`broker_demo_enabled: true→false`；`broker.enabled: true→false` |

**未改动**：执行逻辑、成本模型、账户、风险参数、数据路径、`shadow_run` 执行器选择（非 BROKER_DEMO ⇒ PaperExecutor，已在原逻辑内）。

## 3. 修改后验证（PASS）
```
declared: PAPER_LOCAL | declared_mode: PAPER_LOCAL | backend: paper_local
broker.enabled: False | broker_demo_enabled: False | live_trading: False
assert_paper_only: True
assert_execution_allowed: PASS
PaperExecutor._guard: PASS | mode: PAPER_LOCAL | backend: paper_local
execution_mode_of: PAPER_LOCAL
```
⇒ **`declared_execution_mode == actual_execution_backend == PAPER_LOCAL`**。

## 4. 未接 Broker Demo / 未下单 / 未改账户
- `fxtm_demo_adapter._gate()` 仅在 `BROKER_DEMO 且 broker_demo_enabled=true` 时才允许连接 ⇒ 现恒拒绝（`broker_demo_enabled=false`）；**未连接 broker**。
- 行情读取走 `connect_readonly()`（P0-06 已与执行武装解耦）⇒ **数据路径不受影响**。
- 账户/持仓/执行逻辑未改；`live_trading=false`。

## 5. 运行验证（V2 不停机）
- 触发一次 V2 调度周期：**returncode 0**，`{"skipped":"MARKET_CLOSED","observe_only":true,"agent1":true,"agent2":true,"errors":[]}`。
- `v2_run_health`：`run_status=RUNNING`、`blocked=null`、`scheduler=DIRECT_WINDOWS_TASK`。
- ledger **未变**（sha `9b8b51c5…`，12 行）——见 `REPLAY_REPORT.md`。

## 6. 遗留（诚实）
- dashboard 文案（`dashboard/datasource.py` 的 `BROKER_DEMO` 分支）保留兼容分支但当前不会命中（mode=`PAPER_LOCAL`）；显示将走"模拟执行正常（不下真实单）"。不改其逻辑，避免影响运行中的面板。
- `execution/execution_guard.py`（未跟踪）见 `VERSION_INTEGRITY.md`。
