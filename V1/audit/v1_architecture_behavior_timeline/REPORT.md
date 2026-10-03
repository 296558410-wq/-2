# 新版 V1 初始架构 → 当前版本 · 行为变化法证报告
## REPORT — v1_architecture_behavior_timeline

- **基准**：已恢复的「新版 V1 最初运行架构」（2026-09-28 首次正式运行）。**不用当前架构反推历史。**
- **边界**：只读；`order_send=0`；未改代码/配置/账本/状态/成交；未回滚/未修复；不分析旧 V1；不比较 V2/V3。
- **范围**：magic 90011（`v1_upgrade`），ledger + 券商 facts + Git + registry + 调度。
- **产物**：`REPORT.md` · `timeline.json` · `trade_alignment.csv`(32) · `evidence_manifest.json`（+ 脚本 `build_timeline.py`/`facts.py`）。

---

## 0. 仪器修正（先查仪器）

- **券商 deal `time` 为服务器帧（UTC+3）**。本报告的**交易时间取自 ledger（真 UTC）**；券商服务器帧时间另存于 `*_broker_serverframe` 列。若直接用券商时间会整体偏 +3h，导致把末笔误判到架构变化之后。
- 券商 roundtrips = 32 == ledger `POSITION` order_ids = 32（**集合一致，无孤儿**）。
- 末笔 **平仓真实时间 = 2026-10-02T02:05:01Z**（券商），账本 `CLOSE` 事件记录于 02:18:01Z（对账写入时刻）。

---

## 1. 完整时间线（`timeline.json`）

| 时间 (UTC) | 类型 | 事件 | 证据 |
|---|---|---|---|
| 2026-09-28T12:33:29 | RUNTIME_START | 首次 cycle（ledger seq 1） | ledger |
| 2026-09-28T12:45 | CONFIG | `signal_source=BASELINE_TRANSITION` | `registry/runtime_config.json` |
| 2026-09-28T15:27:55 | CODE | `gates.py` 最后改动（**原始版**） | 备份 mtime + hash `0e02a424…` |
| 2026-09-28T15:35:00 | CONFIG | `order_send_enabled=true` 开闸 | `runtime_config` |
| 2026-09-28T15:35:14 | TRADE | **首笔成交** | ledger seq 48/49 |
| 2026-09-29T23:38:02 | CODE_EVIDENCE | **首个 `CLOSE/PNL`**（券商平仓对账在跑） | ledger seq 228/229 |
| **2026-10-01T13:52:15** | RESTART | **主机重启**（漏 1 拍 14:03Z） | 前序重启审计 |
| **2026-10-01T14:33:19** | CODE | `cycle.py` 改动（**未提交**，内容不可得） | 备份 `cycle.py` mtime |
| 2026-10-02T01:48:02 | TRADE | **末笔开仓** | ledger/券商 |
| 2026-10-02T02:05:01 | TRADE | **末笔平仓（此后无新成交）** | 券商 deals |
| 2026-10-02T03:48:21 | BACKUP | 修复前备份 | `backup/…/backup_manifest.json` |
| **2026-10-02T03:51:44** | CODE | `63d5a22` **RiskGuard 接线修复**（`cycle.py`,`gates.py`） | git |
| **2026-10-02T04:13:08** | CODE | `eceeec2` **Risk Hardening** | git |
| **2026-10-02T04:31:39** | CODE | `ec0907e` **Truth/Forensic 系统** | git |
| 2026-10-02T04:35:14 | CODE | `0f4ce66` Truth 首周期证据 | git |
| 2026-10-02T04:03:02 起 | BEHAVIOR | `DECISION=WAIT_RISK:MAX_DAILY_LOSS,MAX_CONSECUTIVE_LOSS`（风控变为**可达**） | ledger seq 621+ |

> **决定性事实**：**第一处架构变化（03:51:44Z）晚于末笔平仓（02:05:01Z）1 小时 46 分**。全部 32 笔交易都发生在**任何**代码/风控/Truth 变化**之前**。

---

## 2. 每次变化逐项回答（改了什么 / 何时生效 / 影响哪条路径 / 是否进入运行链 / 是否可能改变交易决策 / 证据）

| # | 变化 | 生效 | 影响路径 | 进入运行链? | 可能改变交易决策? | 证据 |
|---|---|---|---|---|---|---|
| C1 | `signal_source=BASELINE_TRANSITION`（配置） | 09-28T12:45Z（首笔前） | Signal 准入 | 是 | 是（决定是否出信号） | runtime_config |
| C2 | `order_send_enabled=true`（配置·开闸） | 09-28T15:35Z | Execution 准入 | 是 | 是（决定是否真发单） | runtime_config |
| C3 | `gates.py` 原始版定稿 | ≤09-28T15:27Z（首笔前） | Risk/Ledger 定义 | 是 | 是 | 备份 hash `0e02a424…` |
| C4 | 券商平仓对账机制运行 | ≥09-29T23:38Z（首笔后） | Ledger 观察层 | 是 | **否**（只补 CLOSE/PNL，不改风控判决/不发单） | ledger seq 228/229 |
| C5 | **主机重启**（非代码） | 10-01T13:52:15Z | 调度 + 进程内状态 | 是 | **UNKNOWN**（漏 1 拍；内存态重建） | 前序重启审计 |
| C6 | **`cycle.py` 未提交改动** | 10-01T14:33:19Z | **未知**（内容不可得） | 是（其后周期用新文件） | **UNKNOWN / DATA_GAP** | 备份 mtime |
| C7 | `63d5a22` RiskGuard 接线修复 | 10-02T03:51:44Z | Risk（+cycle/gates） | 是 | 是——**但晚于全部交易** | git + diff |
| C8 | `eceeec2` Risk Hardening（fail-closed/dup/kill-switch/gap） | 10-02T04:13:08Z | Risk/调度 | 是 | 是——**但晚于全部交易** | git |
| C9 | `ec0907e`/`0f4ce66` Truth 系统 | 10-02T04:31–04:35Z | 观察/证据层（新 ID/快照） | 是 | **否**（只增记录） | git；ledger DECISION schema 于 04:33 起由 17→20 字段 |
| C10 | 风控由"不可达"变"可达"的**行为** | 10-02T04:03Z 起 | Risk | 是 | 是——**但晚于全部交易**（现网持续 `WAIT_RISK`） | ledger seq 621+ |

---

## 3. 逐笔交易对齐（`trade_alignment.csv`，32 行）

逐笔列：`trade_id, entry_ts(真UTC), exit_ts, side, entry/exit, profit/net, outcome, epoch, decision_seq, signal_source, risk_reasons_at_entry, send_retcode, slippage_bps`。

**分段汇总（按 entry 时间）**

| 段 | 定义 | n | 胜率 | 价差 | 净额 | signal_source | 入场时 risk_reasons | retcode | 滑点(最大) |
|---|---|---|---|---|---|---|---|---|---|
| **A 重启前** | < 2026-10-01T13:52:15Z | **25** | 0.480 | **+54.28** | **+49.89** | BASELINE_TRANSITION×25 | 全 0 | 10009×25 | 2.26 bps |
| **B 重启后** | ≥ 2026-10-01T13:52:15Z | **7** | **0.000** | **−65.72** | **−67.75** | BASELINE_TRANSITION×7 | 全 0 | 10009×7 | 3.39 bps |
| （架构变化后） | ≥ 2026-10-02T03:51:44Z | **0** | — | — | — | — | — | — | — |

- **全部 32 笔 epoch = E0（原始架构）**：E0_initial 25 + E0b_restart 7。
- 首笔 2026-09-28T15:35:14Z；末笔开仓 2026-10-02T01:48:02Z / 平仓 02:05:01Z。

---

## 4. 分段检查：是否存在与架构变化同步的行为断点

- **风控行为是否有结构性变化**：**无**。A/B 入场时 `risk_reasons` 全为空；两段跑的是**同一** `RiskGuard` 语义（且该语义的"计数恒 0 / 写死输入"特征**自 E0 即存在**）。风控**真正生效**是在 10-02T04:03Z 起（架构变化之后）。
- **信号行为是否有结构性变化**：**无**。A/B 全部 `signal_source=BASELINE_TRANSITION` + 冻结 successor 表；`signal_type=BASELINE_CONTROL` 恒定。
- **执行行为是否有结构性变化**：**无**。A/B 全部 `retcode=10009`、SL/TP 随单、滑点同量级（2.26 vs 3.39 bps，均 < 15bps 限）。
- **行为断点**：**唯一与事件同步的断点是 P&L**（A `+49.89` → B `−67.75`），**同步对象是"主机重启"，不是任何架构变化**。A/B 的 signal/risk/exec **语义一致**；因此"断点"是结果层，而非结构层。
- ledger DECISION **字段集**在整个交易窗口（09-28T15:32 → 10-02T04:33 前）**稳定**；唯一一次 schema 变化发生在 **10-02T04:33Z**（Truth 系统），**在所有交易之后**。

---

## 5. 最终分类

**A. 事实确认（FACT）**
1. 全部 32 笔交易（25 前置 + 7 重启后）均运行于**原始架构**；首处架构变化 `03:51:44Z` 晚于末笔平仓 `02:05:01Z`。
2. A/B 两段的 signal/risk/execution 语义一致（signal_source 同、risk_reasons 空、retcode 10009、滑点同量级）。
3. 变化集中的代码/风控/Truth 均在 **2026-10-02T03:51:44Z–04:35:14Z** 生效（commit + backup + ledger 字段漂移三重佐证）。
4. 主机重启于 2026-10-01T13:52:15Z；`cycle.py` 于 10-01T14:33:19Z 有一次未提交改动。

**B. 存在关联但无法证明因果（ASSOCIATION_ONLY）**
5. **重启时点与 P&L 反转**（A `+49.89` → B `−67.75`，胜率 0.48 → 0.00）：时间同步，但**重启不是架构变化**，且 A/B 结构一致 ⇒ 关联，非因果（前序重启审计亦为 `NO_EVIDENCE_OF_RESTART_CAUSALITY`）。

**C. 有证据排除（EXCLUDED）**
6. **架构变化（RiskGuard 接线修复 / Risk Hardening / Truth）对本轮 32 笔亏损的因果**：**有证据排除** —— 其生效时间（≥03:51:44Z）晚于末笔平仓（02:05:01Z），不可能进入任何交易的决策/执行路径。
7. 执行链异常：**排除**（retcode 全 10009、滑点均在限内）。

**D. UNKNOWN / DATA_GAP**
8. `cycle.py` 10-01T14:33Z 那次改动的**具体内容与差异**：不可得（未提交、无更早版本，备份即该版本）。
9. 重启瞬间的**反事实**（若未重启会如何）：未知反事实，不作因果。
10. 09-28 首个 cycle（12:33:29Z）的精确源码版本：`cycle.py` 未在首运前提交（`gates.py` 有原始 hash）。

---

## 6. 结论（必须回答的问题）

> **当前新版 V1 的亏损，更接近原始 BASELINE 架构自身表现，还是某个后续架构变化后的行为变化？**

**`CLOSER_TO_ORIGINAL_BASELINE_ARCHITECTURE`（更接近原始 BASELINE 架构自身表现）。**

依据：
1. **所有 32 笔亏损都早于任何架构变化**；RiskGuard 接线修复（03:51:44Z）、Risk Hardening（04:13:08Z）、Truth（04:31:39Z）都在末笔平仓（02:05:01Z）之后生效，**不在这批亏损的因果路径内**（有证据排除）。
2. 这批交易全程运行**同一原始架构**，signal/risk/execution 语义在交易窗口内**无结构性变化**。
3. 原始架构自带的特征（控制臂信号、风控计数不跨轮恢复、输入写死等）**自 E0 即存在**；因此这批亏损属于**原始 BASELINE 架构自身表现**，而非"某个后续架构变化后的行为变化"。
4. **需并列声明**：交易窗口内唯一与结果同步的断点是**主机重启**（关联，非因果）；以及一次**内容不可得**的 `cycle.py` 未提交改动（`DATA_GAP`）。

**是否 INCONCLUSIVE？** 对"**架构变化导致的亏损**"这一问题，证据充分，**不属 INCONCLUSIVE**（有证据排除）。对"**重启是否导致 B 段亏损**"，证据不足，**属 UNKNOWN/关联**，未强行给根因。

---

## 7. 边界声明
- 本次法证未修改任何代码/配置/账本/状态/成交记录；未回滚、未修复、未发单（`order_send=0`）；未分析旧 V1、未比较 V2/V3。
- 证据哈希见 `evidence_manifest.json`；时间线见 `timeline.json`；逐笔见 `trade_alignment.csv`。
