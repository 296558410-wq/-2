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
