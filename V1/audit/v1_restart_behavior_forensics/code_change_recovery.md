# 代码变化恢复（`2026-10-01T14:33Z` 未提交的 `cycle.py` 修改）
## code_change_recovery.md

> 只读法证。目标：尽可能恢复 `2026-10-01T14:33Z`（本地 22:33:19）那次未提交 `cycle.py` 写入**到底改了什么**。
> 结论先行：**总窗口 delta 已恢复并完全刻画**；该次写入的**逐字归属**为 `UNKNOWN`（无 10-01 前后的成对样本）；但恢复出的 delta **不含**任何对 MT5 初始化 / 时间语义 / M1·M15 数据 / label_adapter / MA20·ATR14 / RiskGuard / signal_baseline / position / 订单执行的改动。

---

## 1. 恢复尝试与结果

| 通道 | 结果 | 证据 |
|---|---|---|
| Git working tree / index | `v1_upgrade/` 整个树在首次运行期间**未跟踪**（`?? research/hermes/trader_v1/v1_upgrade/`）；`cycle.py` 直到 `63d5a22`(10-02) 才首次提交 | `PRODUCTION_HASHES.txt`、`git log` |
| Git reflog / stash | reflog 仅含本次会话的提交；**无 stash** | `git reflog --all` / `git stash list` |
| Git 对象库（全部 blob） | 仅 **3 个** 含 `"NEW V1 cycle runner"` 的 blob，**全部 reachable** = 三个 10-02 已提交版本 | `analyze_blobs.py` |
| `.pyc` 头部 | `__pycache__/cycle.cpython-312.pyc`：`src_size=26761`、`src_mtime=2026-10-02 04:22:04Z` ⇒ 由 **10-02** 版本编译，**不含** 10-01 版本 | `recover.py` |
| mtime / backup / 临时件 | **成功恢复 V0**：`workspace/_cycle.py.backup_20260930_073745`（**15946 B**，mtime 保留为 **2026-09-28 23:34:50 本地 = 09-28T15:34:50Z**，即**首笔交易前 24 秒**）；另有 `v1_upgrade/backup/20261002T034821Z/cycle.py`（**V2**，19909 B，mtime **10-01T14:33:19Z**） | 本目录 `evidence_manifest.json` |
| ledger / reports 行为痕迹 | **未发现** 10-01T14:33 处的 schema 或行为变化（见 §4） | `_schema_drift.json` |

**结论**：git 对象库/reflog/pyc **均无法**给出 10-01 版本的独立副本；**唯一可比对的锚点是 V0（09-28 原始）与 V2（10-01T14:33 运行版）**。

---

## 2. 可恢复的完整版本链（`cycle.py`）

| 版本 | 时间 | sha256 | 字节 | 来源 |
|---|---|---|---|---|
| **V0** 09-28 baseline | 09-28T15:34:50Z | `ea686195556e28f5f007245172af2c67de6cdcd9a229abe9b7973e3c108dfe22` | 15946 | `workspace/_cycle.py.backup_20260930_073745` |
| **V2** 10-01 运行版 | 10-01T14:33:19Z | `dcb7edde220cfe07be93c72cda1fa55ae48ed71316b384a38c1898d7161b523b` | 19909 | `v1_upgrade/backup/20261002T034821Z/cycle.py` |
| **V3** `63d5a22` | 10-02T03:51:44Z | `a98d8d0eed4d6c08…` | 20895 | git blob `565a74c0…` |
| **V4** `eceeec2` | 10-02T04:13:08Z | `2d8f50d52cbb67d9…` | 23483 | git blob `fcc68625…` |
| **V5** current | 10-02T04:30Z | `0ed44fb8fe654ea0…` | 26864 | git blob `ea2a0fa3…` |

---

## 3. V0 → V2 = 整个窗口（09-28 → 10-01T14:33）的**全部**文本 delta

统一 diff：**+93 / −2，4 个 hunk**（原文见 `_diff/V0_20260928_baseline__TO__V2_20261001_1433_pre_fix.diff`）：

1. **`import`**：`from datetime import datetime, timezone` → `…, timedelta, timezone`（`timedelta` 供对账之用）。
2. **删除一行未使用常量**：`STATE_OUT = os.path.join(ROOT, "state", "state_package_latest.json")`（**无任何引用**，纯死代码行）。
3. **新增 `_ledger_rows()` + `reconcile_broker_closes()`（约 84 行）**：从券商成交史把 magic 90011 的已平仓 position 写回账本 `CLOSE`+`PNL`（幂等、只追加、`try/except` 包裹）。
4. **`main()` 内新增对账调用块（8 行）**：
   ```python
   try:
       _closes = reconcile_broker_closes(mt5, lg)
       res["reconciled_closes"] = len(_closes)
       ...
   except Exception as _e: ...
   ```

> **归属说明**：第 3+4 项 = **2026-09-30 的已记录改动**（见 `memory/2026-09-30.md`：当日新增 `reconcile_broker_closes()`，并留 `workspace/_cycle.py.backup_20260930_073745`）。第 1、2 项与该改动同源或属于 10-01 写入 —— **无法逐项区分**。除此之外，V0→V2 **无其它文本差异**。

---

## 4. 逐项回答（10-01T14:33 修改的**可确认差异** vs `UNKNOWN`）

| 检查项 | 结论 | 依据 |
|---|---|---|
| 修改前后可确认的差异 | **已刻画**：仅 §3 四项（`timedelta` 导入、删未用 `STATE_OUT`、对账函数、对账调用） | V0↔V2 diff |
| 涉及哪些函数 | 新增 `_ledger_rows`、`reconcile_broker_closes`；`main()` 增加对账调用 | 同上 |
| 是否影响 **MT5 初始化** | **未变**（`mt5_kwargs()`/`initialize()` 原样；`/v1_upgrade/` 树未跟踪但 V0↔V2 该段无差异） | 同上 |
| 是否影响 **时间处理** | **未变语义**（仅多一个 `timedelta` 导入；`NOW`/`roll_day(NOW[:10])` 原样） | 同上 |
| 是否影响 **M1/M15 数据** | **未变** | 同上 |
| 是否影响 **`label_adapter`** | **未变**（`live_state_family()` 原样） | 同上 |
| 是否影响 **MA20 / ATR14** | **未变**（`atr_m15()` 原样；MA20 由 label_adapter 产出，未变） | 同上 |
| 是否影响 **RiskGuard** | **未变**（`rg = RiskGuard(); rg.roll_day(NOW[:10])` 与写死 `0/0` 入参在 V0 与 V2 **均相同**） | 同上 |
| 是否影响 **`signal_baseline`** | **未变** | 同上 |
| 是否影响 **position/state** | **未变**（仅删除未用常量 `STATE_OUT`，无引用） | 同上 |
| 是否影响 **订单执行** | **未变**（`pick_filling`/`order_check`/`order_send`/`FILL`/`POSITION` 段原样） | 同上 |

**ledger 行为痕迹交叉验证**：DECISION 顶层 schema 在 `09-28T15:32` → `10-02T04:33` 之间**稳定为 17 字段**；`snapshot` 形状自 `09-28T12:43` 起恒为 5 键 —— **10-01T14:33 处无 schema/字段变化**（`_schema_drift.json`）。与 §3「除对账外无功能改动」一致。

---

## 5. 判定

- **`NO_CHANGE_FOUND`（对 9 个受检子系统）**：MT5 初始化 / 时间语义 / M1·M15 / label_adapter / MA20·ATR14 / RiskGuard / signal_baseline / position·state / 订单执行 —— 在首个交易周期（09-28T15:34:50Z）到 10-01T14:33Z 之间**无功能改动**。
- **`CONFIRMED_CHANGE`（唯一）**：新增**券商平仓对账**（`reconcile_broker_closes`）→ 只影响**账本观察层**（写 `CLOSE/PNL`），**不改变决策与下单**。
- **`DATA_GAP`**：10-01T14:33 那次写入的**逐字内容/其与 09-30 改动的边界**不可恢复（无成对样本；`git add` 从未发生、reflog/stash/pyc 均无）。
- **残留 `UNKNOWN`（不可证伪）**：若 10-01 写入做了「引入后又被 09-30 之前状态抵消」的**净零编辑**，diff 将看不见 —— 无证据存在，但**无法排除**。
