# GIT_TIMELINE — V2 代码版本时间线
来源：`git log --all -- research/hermes/trader_v2`（共 **87** 提交）。

## 概览
| 项 | 值 |
|---|---|
| 分支 | `fix/v2-full-system-repair-20260917` |
| HEAD | `666e11b7e32aeaebab16a18c194ffc46c0ef6585` |
| V2 首个提交 | `f3bf407` · 2026-09-11 · *V2 Phase-1 baseline: isolated skeleton, architecture, config, CN data-source survey* |
| V2 树未提交改动 | **75 个已跟踪文件被修改（M）** + 1 未跟踪（`?? execution/execution_guard.py`） |
| 作者 | 主要为 `296558410-wq`（即本 agent 的运行身份） |

## 阶段
| 阶段 | 日期 | 代表提交 | 主题 |
|---|---|---|---|
| 建立 | 09-11 | `f3bf407` | Phase-1 骨架/架构/config/数据源调研 |
| 整备 | 09-13~09-16 | (见 MEMORY) | 崩修/对账/DXY/价格空间审计 |
| **P0/P1 大修** | **09-17** | `6f67f1f`→`0fc0f30`（密集 ~30 提交） | instrument 统一、router 唯一入口、freshness/PIT、宏观 fail-closed、forward gate、券商预校验、决策快照+离线回放、LLM 独立性、失败注入、国内+MT5 数据层、面板重建、G3 冻结+guardian |
| 执行启用/长跑 | 09-18 | (research 文档为主) | BROKER_DEMO 启用记录、48h 长跑审计 |
| G3 收尾 | 09-19 | (research 文档) | G3 最终 shadow / 运行态网络审计 |
| 运行期 | 09-20~10-02 | —（无 V2 代码提交） | 仅运行态文件变动（state/*、dashboard 等） |

## 关键点
- V2 的代码演进**集中在 09-11→09-19**；**09-20 之后无 V2 代码提交** ⇒ 当前运行代码 = 09-19 状态 + **未提交的工作区改动**。
- 工作区 dirty（75 文件）包含**代码**（`config/v2_config.json`、`data_sources/mt5_market.py`、`execution/fxtm_demo_adapter.py`、`hermes/context.py`、`runtime/shadow_run.py`、`runtime/v2_scheduled_cycle.py`）与**运行态**（`state/*`）。
- 因此：**“仓库已提交的 V2” ≠ “正在运行的 V2”**；本审计以**磁盘实际文件 + 运行态**为准（见 FORENSICS 的当前/历史分离）。
