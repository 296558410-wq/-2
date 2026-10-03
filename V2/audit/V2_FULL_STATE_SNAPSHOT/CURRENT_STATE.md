# CURRENT_STATE — V2 当前运行态快照
生成：2026-10-02T14:1xZ（UTC）· 全程 READ-ONLY · `order_send=0`

## 1. 版本与工作区
| 项 | 值 |
|---|---|
| 仓库 / 分支 | `C:\AIQuant` · `fix/v2-full-system-repair-20260917` |
| HEAD | `666e11b7e32aeaebab16a18c194ffc46c0ef6585` |
| V2 树 dirty | **75 个已跟踪文件被修改** + 1 个未跟踪（`execution/execution_guard.py`） |
| V2 历史提交（all refs） | **87**；首个 V2 提交 `f3bf407`（2026-09-11，V2 Phase-1 baseline） |

> Dirty 的多数是**运行态文件**（`state/*.json(l)`、`dashboard/*`），亦有**代码漂移**（`config/v2_config.json`、`data_sources/mt5_market.py`、`execution/fxtm_demo_adapter.py`、`hermes/context.py`、`runtime/shadow_run.py`、`runtime/v2_scheduled_cycle.py`）。⇒ **当前运行代码 ≠ 仓库已提交版本**（见 FORENSICS）。

## 2. 进程 / 调度
| 项 | 值 |
|---|---|
| V2 面板进程 | `trader_v2/dashboard/server.py` ×2（本地 python 312） |
| 调度器 | **Windows 任务计划**（`scheduler=DIRECT_WINDOWS_TASK`，`gateway_dependency=false`，`llm_dependency=false`） |
| 任务 | `hermes-v2-cycle`（15m，下一次 22:22 本地）、`hermes-v2-observer`（22:55）、`hermes-tick-collect`（22:24） |
| 备注 | V2 **不经 OpenClaw cron** 驱动；与 V1（OpenClaw cron）相互独立 |

## 3. 当前 run
| 项 | 值 |
|---|---|
| run_id | **`V2-PAPER-20261001-205202-8b9e`** |
| 窗口 | 2026-10-01T20:52:02Z → 2026-10-02T20:52:02Z |
| stopped | false（**RUNNING**） |
| last_scheduled / last_success | 2026-10-02T14:07:01Z / 14:09:17Z |
| current_window | 2026-10-02T14:00Z |
| cycle_result | `decision=WAIT`，`decision_id=DEC-ctx_864b749c68cc`，`paper_orders=0`，`replay_match=true`，`blocked=null` |
| 计数 | cycles 1306 · wait 1059 · trade 125 · reject 25 · missed 17 · recovery 5 · duplicate_prevented 6 |
| 健康 | agent1 OK · agent2 OK · hermes OK · ledger OK · execution OK · blocked null |

## 4. 账户 / 持仓 / 挂单
| 项 | 值 |
|---|---|
| MT5（仅行情用） | login 160759434 · ForexTimeFXTM-Demo01 · **DEMO** · balance=equity=1923.39 |
| MT5 持仓 / 挂单 | **空 / 空** |
| V2 paper 账户 | `initial_balance=200`、balance=150、equity=149.79、**realized_pnl=0.0**、backend=`paper_local` |
| paper 持仓 | 1 个**合成**位 `PPOS-P`（plan `P`，2026-09-12 开，从未平） |

## 5. 当前决策 / 信号 / 机会
- decision=`WAIT`，reason=`该机会需市场确认(follow-through 未验) → 先观察`
- chosen=`opp_geo_shock`；`regime_tags=[GEOPOLITICAL_EVENT, RANGE]`
- **`decision_source="reference_rules"`**，**`signal_from_agents=false`**，`live_trading=false`
- 最近机会序列：几乎全为 `opp_geo_shock`（偶发 `opp_bo_short`/`opp_fbo_long`/`opp_narrative_flow_divergence`）

## 6. 当前是否允许继续交易
- `run_status=RUNNING`、`blocked=null`、`replay_status=MATCH`、`armed=true`、`market_open=true` ⇒ **调度层允许继续跑周期**。
- 但**实际不产生成交**：`decision_source=reference_rules`（占位参照器）+ 供给单一化 ⇒ 近全部决策为 WAIT；且 `execution_mode` 存在**配置漂移**（见 RISK_STATUS / FORENSICS）。
- `paper_orders=0`（本周期）；**V2 从未产生真实成交**（见 TRADE_RECONCILIATION）。

## 7. 未完成 / 告警项
- `last_failure`：2026-10-01T14:37Z `PAPER_REPLAY_MISMATCH`（run `…484f`）。
- agent2 数据缺口 5 项（中央行政策利率 / BLS 宏观 / COT / 全球黄金 ETF 流量 / 央行购金）。
- `v2_run_health.json` 存在 `.pre-monfix.bak`（2026-09-29）——历史修复残留。
