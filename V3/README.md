# V3 — 高频 Demo 交易机器与研究机器

当前交付：[demo_runtime/](demo_runtime/README.md)。tick 驱动、每秒决策，连接隔离 FXTM MT5 Demo 执行冻结实验策略，同时独立记录五周期前向研究。成交与研究报价代理分别计数，策略价值尚未验证。

运行版包括券商止损、费用对账、未知成交恢复、持久化账本、停止开关、监督进程和中文面板。登录恢复已获用户明确授权并在部署主机配置。凭据、授权文件、模型及交易日志仅留本地。正式 CAND-001 测试窗口与旧研究闸门保持原协议。

## 历史归档（2026-10-03）

# V3 — Hermes Trader V3（研究 / 机会引擎）

> 归档快照。源：`C:\AIQuant\research\hermes\trader_v3` + `C:\AIQuant\research\v3_opportunity_engine` + `research/v3_*`。

## 角色
研究阶段（RESEARCH，无实盘执行）：alpha 发现、机会引擎、机制验证、tradability、PIT/长历史/跨市场数据能力探测。

## 目录
| 目录 | 内容 |
|---|---|
| `src/` | `alpha/` `foundation/` `strategy/` `execution/` `gpu_infra/` `microstructure/` `mt5/` `tools/` |
| `config/` | 配置 + `schemas/` |
| `tests/` | 测试 |
| `research/` | `v3_alpha_discovery_r1/r2` `v3_crossmarket_sources` `v3_data_capability` `v3_event_window_pit` `v3_jin10_probe` `v3_long_history_data` `v3_strategy_revalidation_xau` `v3_xau_spot_data` `v3_r4_temporal_f5` 及外部证据蒸馏等 |
| `opportunity_engine/` | 机会引擎：`mechanism_validation*` `tradability_r1` `high_frequency_r2` `m01_*`/`m03_*` 与 `v1_r2..v1_r31_*` 只读审计（run 边界/账本计数器/重置闸门/受控迁移） |
| `audit/` | V3 审计 |
| `reports/` | V3 报告 |
| `manifests/` | 文件清单（FILE_INDEX.json） |

## 状态（归档时点）
- 研究阶段，未观察到常驻调度；`order_send=0`。
- `data/`（parquet 快照）与 `state/` `logs/` 属运行时/数据体，排除并记录。

## 注意
- V3 一切“机会/alpha 候选”均为**研究假设**，未经 forward paper 验证，**不是** Alpha 证明。
