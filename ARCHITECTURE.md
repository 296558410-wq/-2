# ARCHITECTURE.md — AIQuant 三系统架构（归档视图）

> 只读归档，不改变任何运行行为。真实来源：`C:\AIQuant`。

## 0. 总览

```
                     ┌──────────────────────── C:\AIQuant (single git root) ───────────────────────┐
                     │  shared/  research_engine · alpha_engine · alpha_registry · data_registry     │
                     │           architecture/docs · scripts · configs · environment · tools         │
                     └───────────────┬──────────────────────┬───────────────────────┬──────────────┘
                                     │                      │                       │
                            ┌────────▼────────┐    ┌────────▼────────┐     ┌────────▼────────┐
                            │      V1         │    │      V2         │     │      V3         │
                            │ Hermes 主引擎   │    │ 研究+前向引擎   │     │ 研究/机会引擎   │
                            │ BROKER_DEMO     │    │ PAPER/BROKER    │     │ RESEARCH only   │
                            └─────────────────┘    └─────────────────┘     └─────────────────┘
                                 隔离：不同 magic / 账户上下文 / run 状态；无运行耦合
```

## 1. V1 — Hermes 主交易引擎

- **决策链**：OBSERVE → THINK → DECIDE → PLAN → TRIGGER → EXECUTE → MANAGE → REVIEW → MEMORY（每 M15 一轮）。
- **核心模块**（`V1/src/`）：`engine.py` `trader_core.py` `position.py` `position_decision.py`
  `trigger.py` `stop_authority.py` `broker_mt5_demo.py` `ledger.py` `invariants.py` `metrics.py`
  `review.py` `state_package.py` `replay_study.py` `opportunity.py` `candlestick.py`。
- **风控**：1R 硬止损、fail-closed 执行路径、重复单去重、kill-switch（见 `V1/audit/v1_risk_hardening/`）。
- **证据层**：Truth System（`V1/v1_upgrade/truth/`、`V1/audit/v1_truth_system/`）——决策快照、incidents。
- **面板**：`V1/panel/`（`trader_v1_panel`）；`V1/money_hunter/`（dashboard/漂移监控）。
- **历史**：`V1/pre_reset_snapshot/`（2026-09-23 reset 前快照）；`V1/research/v1_r2..v1_r8` 研究线。

## 2. V2 — 研究 + 前向 paper/demo 引擎

- **数据层**：`V2/src/data_sources/`（net/cache/validate/audit/health/local_bars/registry/router/adapters），
  路由 Primary→Secondary→Cache→Missing，确定性。
- **决策层**：`V2/src/agents/`（macro_global / technical）→ `V2/src/hermes/`。
- **执行/账本**：`V2/src/execution/` `V2/src/ledger/`（broker 对账、重复单、重启恢复）。
- **进化与记忆**：`V2/research/shadow_evolution/`、`V2/V2_EVOLUTION_PHASE3/`。
- **Grand Architecture**：`V2/V2_GRAND_ARCHITECTURE/`
  - Phase1：strategy_factory(11 机制族/17 候选) · strategy_registry(7 态) · strategy_brain · strategy_memory ·
    evolution · gpu_research(torch/CUDA) · opportunity_hub(8 源) · intelligence · pipeline。
  - **Phase2 Live Evidence**：`PHASE2_LIVE_EVIDENCE/`（runner 代码 + 冻结报告；实时 jsonl 流按策略排除）。
- **历史策略衰减实验室**：`V2/V2_HISTORICAL_STRATEGY_DECAY_LAB/`。
- **run 记录**：`V2/research/runs/<RUN_ID>/`（manifest / metrics / RUN_SUMMARY；逐周期 decisions 抽样保留）。

## 3. V3 — 研究 / 机会引擎

- `V3/opportunity_engine/`：机制发现、机制验证（mechanism_validation r2–r4）、tradability、high_frequency_r2、
  以及 v1_r2..v1_r31 系列（run 边界、账本计数器、重置闸门、受控迁移）等只读审计。
- `V3/src/`（`alpha` `foundation` `strategy` `execution` `gpu_infra` `microstructure` `mt5` `tools`）。
- `V3/research/`：alpha discovery r1/r2、跨市场源、PIT 事件窗口、长历史数据、XAU spot、策略再验证、
  GitHub 外部证据蒸馏等。

## 4. 共享层（`shared/`）

- `research_engine/`：通用研究内核（data/feature/signal/backtest/statistics/validation/compute-GPU）。
- `alpha_engine/` + `alpha_registry/`：alpha 假设生成/评分/注册表（候选定义）。
- `data_registry/`：数据集索引（仅 JSON 元数据；parquet 数据体不在库内）。
- `architecture/` `docs/`：全局架构文档。
- `scripts/` `configs/` `environment/` `tools/` `benchmarks/` `tests/`：平台级工具与测试。
- `hermes/`：V1/V2/V3 共用的 hermes 元目录（audit/evidence/registry/reports/reviews/skills…）。

## 5. 数据流（V2 为例，简化）

```
PIT/行情源 ──► data_sources(router/cache/validate) ──► agents ──► hermes(brain)
      └► strategy_factory ─► strategy_registry ─► strategy_brain(一致/冲突/缺席)
                                              └► evolution(证据触发) ─► strategy_memory
      ──► execution(guards) ──► ledger/账本 & broker 对账 ──► reviews/观察
      ──► opportunity_hub(8 源) ──► intelligence(LLM 只读) ──► pipeline
```

## 6. 边界与安全

- 归档不含执行能力；无 remote、无 push。
- V1/V2/V3 的运行行为不被本仓库影响。
- 运行所需秘密（broker 凭据等）**从不**进入本仓库。
