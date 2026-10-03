# V1 — Hermes Trader V1（主交易引擎）

> 归档快照。源：`C:\AIQuant\research\hermes\trader_v1`。

## 角色
XAUUSD M15 agentic 交易引擎，每轮：
`OBSERVE → THINK → DECIDE → PLAN → TRIGGER → EXECUTE → MANAGE → REVIEW → MEMORY`。
0.01 手固定，**1R 硬止损**纪律。后端：**FXTM MT5 demo**（BROKER_DEMO）。

## 目录
| 目录 | 内容 |
|---|---|
| `src/` | 引擎核心：`engine.py` `trader_core.py` `position*.py` `trigger.py` `stop_authority.py` `broker_mt5_demo.py` `ledger.py` `invariants.py` `metrics.py` `review.py` `state_package.py` `replay_study.py` `opportunity.py` `candlestick.py` |
| `config/contracts/` | 契约/接口定义 |
| `tests/` | 测试 |
| `audit/` | 审计：`v1_loss_forensics` `v1_full_reaudit` `v1_risk_hardening` `v1_truth_system` `v1_architecture_behavior_timeline` `v1_restart_behavior_forensics` `v1_zombie_code_forensics` `v1_7loss_forensics` `v1_demo_resume_20261002` |
| `v1_upgrade/` | 升级线：`truth/`（证据层）、`ledger/`、`registry/`、`dashboard/`、`audit/`、`tests/` |
| `research/` | `v1_r2_full_optimization` `v1_r2_prediction_upgrade` `v1_r2_market_reading` `v1_r3_hermes_market_forecast` `v1_r4_hermes_audit` `v1_r5_hermes_forecast_discipline` `v1_r6_hermes_validation` `v1_r7_information_diagnostic` `v1_r8_target_redesign` `v1_r8_b_validation` `v1_hermes_prediction_route_archive` |
| `memory/reviews/` | 逐笔复盘（RV-TP-*） |
| `panel/` | `trader_v1_panel` 面板源码 |
| `money_hunter/` | dashboard / 微结构漂移监控 |
| `microstructure_memory/` | 每日 tick/点差统计归档 |
| `pre_reset_snapshot/` | 2026-09-23 reset 前快照（code + originals_moved + v1_root） |
| `manifests/` | 文件清单（FILE_INDEX.json） |

## 状态（归档时点）
- 生产/demo 运行中；调度 `\OpenClaw\hermes-tick-collect`（tick 采集）。
- 未停止、未干预；`order_send=0`。

## 注意
- `run_state/`、`tmp/`、`decisions/` 属**运行时数据**，按策略排除（见根 `archive/RUNTIME_EXCLUSION_POLICY.md`）。
- reviews/pre_reset 内的历史账本为**历史事实**，只读保存，不修改。
