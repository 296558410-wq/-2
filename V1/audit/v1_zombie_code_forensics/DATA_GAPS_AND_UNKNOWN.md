# 数据缺口与 UNKNOWN（DATA_GAPS_AND_UNKNOWN）

> 缺口一律标 `UNKNOWN`；不用时间先后补因果；不补造 commit/作者/调用链。

## 1. Git provenance 缺口
| 项 | 状态 | 说明 |
|---|---|---|
| R8 研究树（`v1_r8_target_redesign/`、`v1_r8_b_validation/`、`v1_hermes_prediction_route_archive/`、`v1_r2_prediction_upgrade/`、`v1_r6_hermes_validation/`、`v1_r7_information_diagnostic/`） | **UNTRACKED** | `git ls-files = 0` 且**无 `.gitignore` 规则命中** ⇒ 这些工件**不在 git 中**，无 commit provenance（仅有文件内容 + 自述哈希）。路线归档自述 `CHANGED_FILES=1`、`GIT_HEAD 9e8c4f9`，但该归档目录本身未被提交。 |
| R8-A/B 的脚本（`_r8a_preregister.py`、`_r8a_amendment1.py`、`_r8b_*.py`） | UNTRACKED | 同上；其行为只能从文件内容与产出核验，无法用 commit 反查“谁在何时改了什么”。 |
| `run_state/tmp/*`（探针/写决策脚本，多份） | 部分 tracked | 09-24 reset 时大批 `tmp/*` 被 A（新增）/D（删除）；属临时脚本，非 runtime entry。 |

## 2. 状态与时间线缺口
| 项 | 状态 | 说明 |
|---|---|---|
| 09-24 reset 时是否存在**未平仓**持仓被清 | **UNKNOWN** | 被删 `run_state/positions/POS-20260907T2355Z.json` 等为 09-07 起历史；reset 语义为“清空重开”，但**当时的券商/账本快照未在本目录内取证** ⇒ 不能断言“当时必为空仓”。 |
| 旧 V1 **每次重启**的精确时点与前后内存态 | **UNKNOWN** | 无逐次程序级快照（既有审计已记）。 |
| 旧 V1 **早期决策完整输入** | **UNKNOWN** | `run_state` 现仅覆盖 09-23→09-28（reset 后）；09-07→09-17 仅 `state_summary` 级残留。 |
| 09-24 reset 与旧 V1 后续亏损的**因果** | **NOT_SUPPORTED**（因） | reset 只移历史状态、未改代码/调用；无代码路径证据 ⇒ 仅时间相关，不作因果。 |

## 3. 未纳入范围的相邻项（明确排除，非本任务缺口）
- V3 的 `ff3f24a`（`research/hermes/trader_v3/audit/.../git_diff_stat.txt` R100）：**非 V1**。
- money-hunter 的 `_hb_tick_cron.ps1`（`7cb1dea`，09-13）：**非 V1 runtime**。
- V2 任何改动：**V2 完全未触碰**（本任务边界）。
- 10-02 的 V1 runtime 改动（riskguard/risk-hardening/truth）：**晚于 R8 冻结**，属后续独立任务，非“R8 前僵尸清理”。

## 4. 证据等级说明
- “V1 runtime 代码删除数 = 0”“`openclaw` 作者未触碰 trader_v1”“destructive-op 命中 = 0”：`FACT`（git 直读 + 代码扫描）。
- “被删文件属 runtime 引用目录”：`FACT`（`文件:行` 直读）。
- “删除未影响交易路径”：`DERIVED`（基于引用性质：报表/状态机读取历史，非决策依赖）。
- “reset 时是否有未平仓被清”：`UNKNOWN`（缺当时券商/账本快照）。

## 5. 不补造清单
- 不臆测 R8 树“曾被删除/改名”（无 git 证据，只能记 UNTRACKED）。
- 不因 `cleanup commit` 在前、`亏损` 在后而写因果。
- 不把 `run_state/tmp` 临时脚本称作 runtime entry。
