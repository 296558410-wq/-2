# V2 — Hermes Trader V2（研究 + 前向 paper/demo 引擎）

> 归档快照。源：`C:\AIQuant\research\hermes\trader_v2`。

## 角色
数据层 + 决策层 + 执行/账本 + Grand Architecture 研究程序 + Phase2 live evidence。
存在 PAPER 与 BROKER_DEMO 两种 mode；magic `90003`。

## 目录
| 目录 | 内容 |
|---|---|
| `src/` | `agents/`(macro_global, technical) `data_sources/`(router/cache/validate/local_bars…) `execution/` `hermes/` `ledger/` `runtime/`(调度入口) `research_compute/` `tools/` |
| `config/` | 配置 + contracts |
| `tests/` | 测试 |
| `audit/` | 审计线（含 `V2_FULL_STATE_SNAPSHOT` 等） |
| `research/` | 研究文档 + `runs/<RUN_ID>/`（manifest/metrics/SUMMARY；逐周期 decisions 抽样） + `shadow_evolution/` |
| `V2_GRAND_ARCHITECTURE/` | Phase1（strategy_factory/registry/brain/memory/evolution/gpu_research/opportunity_hub/intelligence/pipeline） + `PHASE2_LIVE_EVIDENCE/`（runner 代码 + 冻结报告；实时流排除） |
| `V2_EVOLUTION_PHASE3/` | 进化 Phase3 |
| `V2_HISTORICAL_STRATEGY_DECAY_LAB/` | 历史策略衰减实验室 |
| `manifests/` | 文件清单（FILE_INDEX.json） |

## 关键事实
- Grand Architecture Phase1 结论：**FDR 通过 0/17 → 0 候选**，状态 `RESEARCH_COMPLETE`
  （“架构成立、证据不足”）；GPU 计算真跑（GPU 2.18s vs CPU 14.55s ≈ 6.7×，peak 1223MB）。
- Phase2：live shadow evidence stream（**增长流按策略排除**，保留 runner 代码与冻结报告）。
- 活跃 run：`V2-PAPER-20261001-205202-8b9e`（RUNNING）。
- 冻结基线 tag：`v2-pricespace-validated-cf31862` / `V2_FULL_AUDIT_BASELINE` / `V2_REPAIRED_RUN_START`。

## 状态（归档时点）
- 调度：`\OpenClaw\hermes-v2-cycle`(PT15M)、`hermes-v2-observer`、`hermes-v2-shadow-evidence`。
- 未停止、未干预；`order_send=0`。

## 注意
- `state/` `observations/` `data_cache/` `logs/` 属**运行时数据**，排除并记录。
- run 记录中 `*.jsonl`（ledger/timeline）按策略排除；`run_manifest.json`/`metrics.json`/`RUN_SUMMARY.md` 保留。
- 本归档中 V2 的“表现”数字均为**研究证据**，非 Alpha 证明。
