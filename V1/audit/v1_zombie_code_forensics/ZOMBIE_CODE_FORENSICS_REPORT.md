# V1 R8 僵尸代码清理与 Runtime Provenance 法证 — 报告
## ZOMBIE_CODE_FORENSICS_REPORT

- **任务**：查清 R8 冻结前 OpenClaw 是否清理/删除过所谓“僵尸代码”，这些代码是否实际属于 V1 runtime path，是否可能造成运行行为变化。
- **硬边界遵守**：只读；**未改**任何代码/配置/参数/Prompt/RiskGuard/账本/历史成交/运行状态；**未回滚/未恢复旧状态**；**未切换 Git commit 运行**；`order_send=0`；V2/V3 未触碰；V1 R8 冻结现状未变。
- **结论词表**：`CONFIRMED / NOT_SUPPORTED / UNKNOWN`（最终结论只用这三个）。

---

## 0. 方法与判定锚点

- **R8 冻结锚点**：R8-A 目标注册表 `v1_r8_target_redesign/registry/v1_r8_target_registry.json` 的 `frozen_at_utc = 2026-09-28T10:47:20Z`（`frozen_before_any_validation=true`）；路线归档 `2026-09-28T12:03:12Z` @ `GIT_HEAD 9e8c4f9`。
- **枚举口径**：`git log --all --no-merges`（含全部 refs/作者），筛选 `research/hermes/trader_v1/**` 的变更；并按 `git log --all --diff-filter=DR` 全仓库枚举删除/重命名。
- **引用检查口径**：对 V1 runtime 代码（`trader_v1/*.py` + `v1_upgrade/**/*.py`，19 个 tracked）逐文件检索被删路径/目录名与 destructive 操作；同名副本区分树（旧引擎 vs v1_upgrade vs V2）。
- **不写因果**：不因 commit 在先、亏损在后而认定因果。

---

## 1. 必查项汇总（delete / cleanup / refactor / rename / dead-code / dependency / runtime entry）

| 类别 | V1 命中 | 证据 |
|---|---|---|
| delete / cleanup | **1 次**（`43f9b2f`，09-24，72 个文件，**全部 state 类**） | `git_deletions_raw.json` |
| rename / move | **0 次**（V1）；1 次为 **V3**（`ff3f24a`，`git_diff_stat.txt` R100） | 同上 |
| refactor | 0 次（无 V1 重构提交） | `git_changes_raw.json` |
| dead-code removal | **0 次**（V1 runtime .py 删除数 = 0） | 同上 |
| dependency removal | **0 次**（`requirements*.txt`/`-lock` 无删除） | 同上 |
| runtime entry 修改 | 有 **M（修改）无 D**：09-07/09-08、**09-20 `acaef08`**、10-02 `63d5a22`/`eceeec2`/`ec0907e`/`0f4ce66` | `GIT_CLEANUP_TIMELINE.csv` |
| 作者归属 | V1 提交作者 = `296558410-wq`；**`openclaw` 从未触碰 `trader_v1`**（其提交均在 V3） | `check_references.py` |
| destructive 操作（os.remove/rmtree/unlink/rmdir） | **0**（V1 runtime + R8 脚本） | 同上 |

**唯一删除操作 `43f9b2f`（2026-09-24，作者 `296558410-wq`，`reset(v1): archive pre-reset history and start V1_RUN_20260924_RESET_01`）**：
- 删除 72 个文件：`run_state/decisions/*.json`（69）、`run_state/positions/POS-*.json`（2）、`run_state/trader_summary.txt`（1）。
- 同 commit **Modify**（非删）：`state_package_latest.json`、`plan_ledger.jsonl`、`statistics.json`、`workflow_history.jsonl` 等。
- 声明：`reset, not an optimization; no strategy/parameter change`。

---

## 2. Runtime Reference 证据链（commit → 被删代码 → runtime path → R8 行为）

```
commit 43f9b2f (09-24 reset)
  │ 删除
  ├─ run_state/decisions/*.json ──引用──> engine.py:31  DEC_DIR = RUN/"decisions"      (每轮写入)
  │                                    ├ metrics.py:130-133 decisions_recent()  (*.json glob, 只读报表)
  │                                    └ opportunity.py:17  DEC_DIR              (只读研究)
  ├─ run_state/positions/*.json ─引用──> position.py:23  STATE_DIR = run_state/positions
  │                                    └ position.py:360 open_positions()       (仓位状态机读取)
  └─ run_state/trader_summary.txt ──> 引用 0 命中（非 runtime 依赖）
        │
        ▼
   R8 冻结 (09-28T10:47Z)：V1 runtime 代码 = 零差异（见 R8_BEFORE_AFTER_DIFF.md）
        │
        ▼
   行为变化：无代码路径证据（仅时间相关，NOT_SUPPORTED）
```

- **被删的是 state/历史工件，不是代码**；删除后 `decisions/`、`positions/` 目录仍存在并被 runtime 持续读写。
- 唯一潜在影响面 = **只读报表消费者**（dashboard `metrics` 的历史决策/持仓视图、`opportunity` 频率研究）**丢失 09-07→09-24 历史**；**交易路径（signal→risk→execution）不读历史决策 JSON，未被触及**。

---

## 3. 时间线（cleanup / R8 freeze / 重启 / 收益变化 / 行为变化）

| 时间(UTC) | 事件 | 证据 |
|---|---|---|
| 09-07 | 旧 V1 P0 闭环上线（首版 runtime） | git 09-07 commits |
| 09-08 | I6 对账接线修复 | `cf25d5d`/`1b61fb8` |
| 09-13 | money-hunter 删除 `_hb_tick_cron.ps1`（**非 V1**） | `7cb1dea` |
| 09-20 | mt5-isolation 修复（retire phantom `fxtm_demo_v3`） | `acaef08` |
| 09-22 | V3 文件重命名（**非 V1**） | `ff3f24a` |
| **09-24** | **V1 run reset：删 72 个 state 文件（0 代码）** | `43f9b2f` |
| 09-25–09-26 | R8-A 预注册/冻结准备（研究；untracked） | R8 树 |
| **09-28T10:47Z** | **R8-A 目标注册表冻结** | `frozen_at_utc` |
| 09-28T12:03Z | 预测路线归档（UT，`CHANGED_FILES=1`） | 归档 md |
| 09-28 | 新 V1（v1_upgrade, magic 90011）开始交易 | 券商 deals |
| 10-01T13:52Z | host 重启（旧 V1 早已弃用；新 V1 续跑） | 既有审计 |
| 10-02 | V1 riskguard 修复 / risk-hardening / truth 系统 | `63d5a22`/`eceeec2`/`ec0907e` |
| 收益变化 | 旧 V1 09-16/09-17/09-25 亏损；新 V1 09-30 起衰减 | 既有券商事实 |

> **注意**：09-24 删除发生在 09-25 旧 V1 亏损日**之前**，但 **二者仅时间相关**；删除内容为历史 state、非代码，无路径证据 → 不作因果。

---

## 4. 特别检查（逐项）

| 检查 | 结果 | 证据 |
|---|---|---|
| “看似僵尸代码、实际仍被调用” | **代码：否**；**状态目录：是**（`decisions/`、`positions/` 被 runtime 引用，但被删的是其历史文件，目录仍在） | §2 |
| fallback 被误删 | **否**（无 fallback 代码删除；destructive 扫描 0） | `check_references.py` |
| 状态恢复/初始化代码被误删 | **否**（无 .py 删除；`position.py` 状态机完整） | §1 |
| 数据/PIT 代码被误删 | **否**（无 .py 删除；`v1_upgrade` 数据/PIT 未动） | §1 |
| cron / 调度入口变化 | **否**（V1 由 OpenClaw cron `v1-upgrade-demo-cycle` 驱动，无 V1 cron 文件被删） | `GIT_CLEANUP_TIMELINE.csv` |
| Truth/Forensic 代码变化 | **N/A 于 R8 前**（truth 系统 10-02 才建，晚于 R8） | `ec0907e` |

---

## 5. 最终必须回答

**① 是否发现被误判为“僵尸代码”、但实际上仍属于 V1 runtime path 的代码？**
→ **代码：`NOT_SUPPORTED`** —— git 全历史中 **V1 runtime `.py` 删除数 = 0**。
→ **状态工件：`CONFIRMED`（事实性）** —— 唯一删除操作清掉的是**被 runtime 引用的状态目录中的历史文件**（`run_state/decisions/`、`run_state/positions/`），但它们是**state（非代码）**。

**② 如果有：文件、commit、调用链、实际影响？**
→ 文件：`run_state/decisions/20260907T*.json`…（69）+ `run_state/positions/POS-20260907T2355Z.json` 等（2）+ `run_state/trader_summary.txt`（1）。
→ commit：`43f9b2f`（2026-09-24，`296558410-wq`，run reset）。
→ 调用链：`engine.py:31` / `metrics.py:130-133` / `opportunity.py:17`（decisions）；`position.py:23` / `open_positions()`（positions）。
→ 实际影响：**只读报表层丢失 09-07→09-24 历史**；**交易路径未受影响**；`state_package_latest.json` 为 Modify 非删除，引用未断。**是否有未平仓被清 = `UNKNOWN`**（缺当时券商/账本快照）。

**③ 如果没有（代码层）：排除依据？**
→ `git log --all --diff-filter=DR` 全仓库仅 4 个删除/改名 commit，其中匹配 V1 的仅 `43f9b2f`（72 个 **state** 文件，runtimeD=0）与 `ff3f24a`（**V3** 文件）。**V1 runtime `.py` 删除 = 0**；`openclaw` 作者**从未**触碰 `trader_v1`；V1 runtime 与 R8 脚本 destructive-op 命中 = 0。

**④ cleanup 时间与重启/亏损变化：仅时间相关 or 代码路径证据？**
→ **仅时间相关**。删除只移历史 state、未改任何 runtime 代码或调用路径；**无代码路径证据**支持其改变了 signal/risk/execution/data/PIT/truth。

**⑤ 是否存在足够证据支持 `CLEANUP → RUNTIME CHANGE → BEHAVIOR CHANGE`？**
→ **`NOT_SUPPORTED`**（代码层无删除、无引用断裂；唯一删除为 state 历史工件；且无行为变化的代码路径证据）。

**⑥ 最终结论**
→ **`NOT_SUPPORTED`**（不存在“被误判为僵尸代码但仍属 V1 runtime path 的**代码**”，亦不成立 `CLEANUP→RUNTIME→BEHAVIOR` 因果链）。
→ 附带事实（非反例）：唯一删除 = **state-history removal，non-code，non-trading-path**（`CONFIRMED` 的事实陈述）。

---

## 6. 验收自检

| 验收项 | 结果 | 依据 |
|---|---|---|
| Git provenance 完整 | **PASS（含缺口披露）** | 全 refs 枚举；R8 树 `UNTRACKED` 已披露 |
| Runtime reference 检查完成 | **PASS** | `RUNTIME_REFERENCE_MAP.md` + `DELETED_CODE_IMPACT.jsonl` |
| R8 当前版本未改变 | **PASS** | 本任务零写入 runtime；`R8_BEFORE_AFTER_DIFF.md` |
| 工作区干净 | **PASS** | 仅新增本审计目录；见 §7 commit |
| `order_send=0` | **PASS** | 本目录脚本无 order 调用 |
| V1/V2/V3 隔离 | **PASS** | 仅读 trader_v1；未触 V2/V3 |
| 无策略/参数/Prompt/RiskGuard 修改 | **PASS** | 零写入 |
| 无状态恢复/回滚 | **PASS** | 只读 |
| SHA256 完整 | **PASS** | `SHA256SUMS.txt` |

## 7. 证据与指纹
- 产物：本目录 `GIT_CLEANUP_TIMELINE.csv`(882 行) · `git_changes_raw.json` · `git_deletions_raw.json` · `DELETED_CODE_IMPACT.jsonl`(72) · `RUNTIME_REFERENCE_MAP.md` · `R8_BEFORE_AFTER_DIFF.md` · `DATA_GAPS_AND_UNKNOWN.md` · `SHA256SUMS.txt` · 脚本 `enumerate_git.py` / `enumerate_deletions.py` / `check_references.py` / `ref_scan2.py` / `build_deliverables.py`。
- Git commit（两笔式）：见 `SHA256SUMS.txt` 头部 `artifact_commit`。

**完成后停止。** 不修复、不回滚、不启动新交易、不进入下一轮 Alpha Research。
