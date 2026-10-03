# AIQuant-XAUUSD-Systems

> XAUUSD 研究/交易系统归档仓库（V1 / V2 / V3）
> **性质：资产归档（asset archival），不是系统升级。**
> 归档时点：2026-10-03（Asia/Shanghai）。来源仓库 `C:\AIQuant`（只读快照）。

本仓库把 AIQuant 的 V1/V2/V3 三个 XAUUSD 系统的**源码、研究脚本、审计产物、架构文档与注册表**
固化成一个**本地** Git 仓库，供长期保存与后续（由人手动）推送到私有 GitHub。

---

## 1. 这是什么 / 不是什么

- **是**：三套系统当前源码与静态研究/审计产物的完整快照 + 版本注册表 + 证据清单。
- **不是**：不是可交易部署包；不是回测结论；**不是 Alpha 证明**。
- 研究结论一律以源仓库中的原始报告为准；本归档不重跑、不改写任何结论。

## 2. 三套系统与角色

| 系统 | 角色 | 目录 | 当前状态 |
|---|---|---|---|
| **V1** | Hermes 主交易引擎（M15 agentic：OBSERVE→THINK→DECIDE→PLAN→TRIGGER→EXECUTE→MANAGE→REVIEW→MEMORY），0.01 手，1R 硬止损 | `V1/` | 生产 / demo |
| **V2** | 研究+前向 paper/demo 引擎：数据层、strategy_factory/brain/registry/memory、evolution、gpu_research、opportunity_hub、Grand Architecture Phase1/Phase2 live evidence | `V2/` | paper/demo 前向运行 |
| **V3** | 研究阶段：alpha discovery、opportunity engine、mechanism validation、tradability、PIT/长历史数据能力探测 | `V3/` | 研究（无实盘执行） |

**隔离关系**：V1/V2/V3 相互隔离（不同 magic / 账户上下文 / 独立 run 状态）。本归档只读快照，
**不改变任何运行行为**。

> ⚠️ 诚实说明：V1/V2/V3 **共享同一个 git root（`C:\AIQuant`）**，没有各自独立的历史。
> 见 `archive/SOURCE_COMMITS.md` 与 `SOURCE_REPOSITORY_REGISTRY.json`。

## 3. 当前运行状态（归档时点）

- V1：由 Windows 计划任务 `\OpenClaw\hermes-tick-collect` 采集 tick；主引擎由 OpenClaw cron 驱动。
- V2：Windows 计划任务 `\OpenClaw\hermes-v2-cycle`（PT15M）、`hermes-v2-observer`、
  `hermes-v2-shadow-evidence`；活跃 run `V2-PAPER-20261001-205202-8b9e`（RUNNING）。
- V3：研究阶段，未观察到常驻调度。
- 本归档**未停止、未干预**任何任务；`order_send=0`；生产改动=0。

## 4. PAPER / DEMO 边界

- V1 走 **FXTM MT5 demo**；V2 有 PAPER 与 BROKER_DEMO 两种 mode。
- 归档中的 run 记录（`V2/research/runs/*`）**多为 PAPER / SHADOW**，是研究观察，**不代表真实成交或盈利**。
- **验证哲学**：回测/历史拟合 ≠ 战胜未来；只有 forward paper 观察才是真验证。
  因此本归档中的一切“表现”数字都是**研究证据**，不是可交易结论。

## 5. 目录结构

```
README.md ARCHITECTURE.md SYSTEM_REGISTRY.json VERSION_REGISTRY.json
SECURITY_POLICY.md REPRODUCTION.md SOURCE_BASELINE.json SOURCE_REPOSITORY_REGISTRY.json
SECURITY_SCAN_REPORT.md GITHUB_ARCHIVE_VERIFICATION.md .gitignore
V1/{README.md,src,config,tests,research,audit,docs,memory,panel,money_hunter,
    microstructure_memory,v1_upgrade,pre_reset_snapshot,manifests}
V2/{README.md,src,config,tests,research,audit,docs,V2_GRAND_ARCHITECTURE,
    V2_EVOLUTION_PHASE3,V2_HISTORICAL_STRATEGY_DECAY_LAB,manifests}
V3/{README.md,src,config,tests,research,audit,reports,docs,opportunity_engine,manifests}
shared/{architecture,docs,alpha_engine,research_engine,alpha_registry,data_registry,
        scripts,configs,environment,tools,benchmarks,tests,hermes}
archive/{SOURCE_COMMITS.md,SOURCE_BRANCHES.md,ARCHIVE_MANIFEST.json,
         EXCLUDED_RUNTIME_ASSETS.jsonl,RUNTIME_EXCLUSION_POLICY.md}
docs/{AIQUANT_ROOT_README.md,PROJECT_COLLABORATION.md}
```

## 6. 哪些文件是“运行时数据”（不在本归档内）

以下**必须被视为运行时/易变数据**，本归档**按策略排除**，并逐条记录在
`archive/ARCHIVE_MANIFEST.json` 的 `excluded_runtime_assets` 与
`archive/EXCLUDED_RUNTIME_ASSETS.jsonl`：

- 高频运行时 `*.jsonl`（ledger / timeline / live shadow stream / evidence_registry / router_audit …）
- 心跳与易变状态（`heartbeat.jsonl`, `*_latest.json`, `*_health.json`, `*scheduler_state*.json`）
- `data_cache/`、`cache/`、`logs/`、`tmp/`、`run_state/`、`state/`、`observations/`
- 大数据（`*.parquet`、`*.csv`>1MB、单文件 >10MB 的产物）
- 二进制（`*.dll`, `*.exe`, MT5 `*.ex5`）
- **密钥类**：`.env.mt5_demo` / `.env.mt5_v3_calib` / `.env.v3_jin10` 等（**绝不入库**）
- 体量过大的“每周期证据”目录（`decisions/`, `decision_contexts/` 等）做**抽样**保留，
  完整集合仍在源仓库。

## 7. 哪些结果**不是** Alpha 证明

- 任何回测/参数搜索/GPU 组合扫描的“最优结果”**不是** Alpha 证明。
- V2 Grand Architecture Phase1 的结论是 **FDR 通过 0/17 → 0 候选（RESEARCH_COMPLETE）**，
  属“架构成立、证据不足”。
- PAPER / SHADOW run 的胜率、收益率**不是**实盘证据。
- 只有 forward paper/demo 的**真实开→平闭环**才有验证意义。

## 8. 如何复现研究

见 `REPRODUCTION.md`（Python 3.12、依赖、入口脚本、replay/审计运行方式、如何在不执行交易的前提下做 import smoke）。

## 9. 如何查看版本

见 `VERSION_REGISTRY.json`（V1/V2/V3 子系统版本、研究线、冻结基线 tag）与 `archive/SOURCE_COMMITS.md`。

## 10. 安全说明

见 `SECURITY_POLICY.md` 与 `SECURITY_SCAN_REPORT.md`。提交前已执行密钥扫描闸门，**未发现真实密钥**。

---

*本仓库由只读归档流程生成。若需推送 GitHub：由人手动创建私有仓库并 `git remote add` / `git push`；
本流程**不创建 remote、不 push**。*
