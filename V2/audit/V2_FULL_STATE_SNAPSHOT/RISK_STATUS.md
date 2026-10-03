# RISK_STATUS — V2 风控与执行门现状
只读取 `config/v2_config.json`、`state/v2_run_health.json`、`execution/*`、既有审计（`research/V2_*`）。

## 1. 声明限额（config `execution.risk`）
| 项 | 值 |
|---|---|
| per_trade_pct | 1.0 |
| max_daily_loss_pct | 3.0 |
| max_consecutive_losses | 4 |
| single_position | true |
| max_notional_usd | 25000 |
| contract | min 0.01 / max 0.05 手 · 100 oz/手 · 杠杆 500 |

## 2. 执行门 / 守卫（代码）
| 机制 | 位置 | 说明 |
|---|---|---|
| 执行守卫 | `execution/execution_guard.py` | **未跟踪新文件**（`??`），已存在于工作区 |
| 券商止损预校验 | `d364f5d` | fail-closed，无效单不下发（含 live symbol spec probe） |
| forward gate 全入口加固 | `7284f10`、`b002054` | start_run/ensure_run/CLI/scheduler 全加固；未认证 forward run 锁死 |
| PIT as-of 缓存 | `a6229b1` | 不可变 `get_asof` + router 接线 |
| 失败注入 | `0e33811` | 13/13 fail-closed |
| LLM 独立性 | `0e33811` | 7/7 |
| shadow guardian | `6d1e9fd` + `tools/shadow_guardian.py` | 每周期 validate + 4h/24h/48h 门 |

## 3. 当前运行态风控
| 项 | 值 |
|---|---|
| `blocked` | **null**（无阻塞） |
| `execution_status` | OK |
| `exec_rejected_total` | 3（历史累计） |
| `duplicate_prevented` | 6 |
| `recovery_count` | 5 · `missed_cycles` 17 |
| `last_failure` | 2026-10-01T14:37Z `PAPER_REPLAY_MISMATCH`（run …484f） |
| `forward_validation_allowed` | true（flag 文件存在，2026-09-18） |

## 4. 关键问题：执行模式漂移（当前 vs 配置）
- config 声明：`execution.backend="fxtm_demo"`、`execution_mode="BROKER_DEMO"`、`broker_demo_enabled=true`、`broker.enabled=true`、`live_trading=false`。
- 实际运行：活跃 run = **`V2-PAPER-20261001-205202-8b9e`**（PAPER）；`paper_account.backend="paper_local"`；`hermes_decision_latest.live_trading=false`；**broker 无 V2 magic ⇒ 无券商下单**。
- ⇒ **声明 BROKER_DEMO，实际 PAPER**（与 `V2_LONG_RUN_AUDIT_20260918` 记录的 MT5-读取/执行耦合→回退问题同源）。

## 5. 风险系统是否“被真正使用”
- 因 **0 成交**，config 中的 `max_daily_loss_pct / max_consecutive_losses / single_position / max_notional` **从未在真实成交路径上被触发检验**（仅由失败注入/单元测试覆盖）。
- 无“风控拦截”状态（`blocked=null`）；不产生 `WAIT_RISK` 类拦截记录。

## 6. 判定
- 结构上：门/守卫齐备且多为 fail-closed（已由测试与失败注入验证）。
- 运行上：**风控未被实际成交检验**；且存在**执行模式声明与实际不一致**的漂移（BROKER_DEMO 声明 vs PAPER 实跑）——需在下一阶段澄清（本审计不改动）。
