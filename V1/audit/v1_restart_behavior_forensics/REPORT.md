# 新版 V1 重启前后行为差异法证 — 报告
## REPORT — v1_restart_behavior_forensics

- **范围**：新版 V1（`v1_upgrade`, magic 90011）。重启 = **2026-10-01T13:52:15Z**（host LastBootUpTime）；末笔 = 开 `10-02T01:48:02Z` / 平 `10-02T02:05:01Z`。
- **硬边界**：只读；`order_send=0`；未改/未修/未回滚代码·配置·状态·账本；未改策略·参数·Prompt·Risk；未分析旧 V1、未比较 V2/V3；`UNKNOWN/DATA_GAP` 保留。
- **产物**：`REPORT.md` · `code_change_recovery.md` · `pre_post_replay.csv` · `state_diff.json` · `evidence_manifest.json` · `SHA256SUMS.txt` · `_diff/`（版本链 diff）· `_schema_drift.json`。

---

## A. 10-01T14:33Z `cycle.py` 修改（摘要；详见 `code_change_recovery.md`）

- **恢复了 V0（09-28 原始）**：`workspace/_cycle.py.backup_20260930_073745`，`ea686195556e28f5f007245172af2c67de6cdcd9a229abe9b7973e3c108dfe22`（15946 B，mtime 保留为 **09-28T15:34:50Z**，即首笔前 24 秒）。
- **V0 → V2（10-01T14:33 运行版）全窗口 delta = +93 / −2，4 hunk**，仅 4 项：①`timedelta` 导入；②删除**未使用**常量 `STATE_OUT`；③新增 `_ledger_rows()`+`reconcile_broker_closes()`（≈84 行）；④`main()` 内对账调用（8 行）。
- ③④ = 已记录的 **09-30** 改动（券商平仓对账）。**9 个受检子系统（MT5 初始化 / 时间语义 / M1·M15 / label_adapter / MA20·ATR14 / RiskGuard / signal_baseline / position·state / 订单执行）在窗口内无功能改动**（`NO_CHANGE_FOUND`）。
- 该次写入的**逐字归属** = **`DATA_GAP`**（首次运行期 `v1_upgrade/` 未跟踪；reflog/stash/pyc/工作区均无 10-01 前后成对样本）。

---

## B. 重启前后输入一致性

**B1 记录级对齐（`pre_post_replay.csv`，重启前最后 6 个有效周期 vs 重启后前 6 个）**

| 侧 | ts_utc (cycle) | action | state | family | trend_20 (close−MA20) | atr14 | last_bar_utc(服务器帧) |
|---|---|---|---|---|---|---|---|
| PRE | 10-01T12:33:04 | WAIT_SIGNAL:FAMILY_RANGE_NO_TRADE | DECELERATION | RANGE | +15.11 | 7.41 | 15:30 |
| PRE | 10-01T12:48:07 | WAIT_SIGNAL:FAMILY_RANGE_NO_TRADE | DECELERATION | RANGE | +15.97 | 7.67 | 15:45 |
| PRE | 10-01T13:03:03 | WAIT_SIGNAL:FAMILY_RANGE_NO_TRADE | DECELERATION | RANGE | +10.47 | 7.93 | 16:00 |
| PRE | 10-01T13:18:04 | WAIT_SIGNAL:FAMILY_RANGE_NO_TRADE | ROTATION | RANGE | +2.04 | 7.81 | 16:15 |
| PRE | 10-01T13:33:06 | WAIT_SIGNAL:FAMILY_RANGE_NO_TRADE | ROTATION | RANGE | +0.77 | 7.84 | 16:30 |
| PRE | 10-01T13:48:03 | WAIT_SIGNAL:FAMILY_RANGE_NO_TRADE | ROTATION | RANGE | −6.11 | 8.00 | 16:45 |
| — | *（13:52:15 重启；漏 1 拍 14:03Z）* | | | | | | |
| POST | 10-01T14:18:02 | WAIT_SIGNAL:FAMILY_RANGE_NO_TRADE | ROTATION | RANGE | −12.88 | 8.55 | 17:15 |
| POST | 10-01T14:33:03 | ENTER | EXPANSION | DIRECTIONAL | −4.97 | 9.08 | 17:30 |
| POST | 10-01T14:48:04 | WAIT_SIGNAL:FAMILY_RANGE_NO_TRADE | REJECTION | RANGE | −4.66 | 9.53 | 17:45 |
| POST | 10-01T15:03:04 | ENTER | EXPANSION | DIRECTIONAL | −15.90 | 9.82 | 18:00 |
| POST | 10-01T15:18:02 | WAIT_POSITION_OPEN | EXPANSION | DIRECTIONAL | −8.44 | 10.06 | 18:15 |
| POST | 10-01T15:33:03 | ENTER | EXPANSION | DIRECTIONAL | −9.51 | 10.47 | 18:30 |

逐项检查（全部 `NO_CHANGE_FOUND`）：
- **MT5 symbol/tick**：`snapshot.bid/ask/spread_bps` 两侧正常、量级一致（spread ~0.3bps）。
- **M1/M15 bars、candle close 时间**：`last_bar_utc` **连续推进**（16:45 → 17:15，跨越 30min 缺口），无回退/重置。
- **MA20**：`live_state.ma20` 两侧均存在并按 `trend_20 = close − MA20` 自洽变化。
- **ATR14**：两侧均有值，`7.4 → 10.5` 平滑上行，无跳变。
- **9-state / family**：`ROTATION→EXPANSION` 平滑转移，符合冻结标签链，**无重启处断裂/复位**。
- **hysteresis**：内部路径量，未记录；由 B2 的确定性证据间接排除其非确定性。
- **signal / order intent / SL·TP**：`signal_for_state`+`order_intent` 输出两侧同构（RANGE→不下单；DIRECTIONAL→按 M15 趋势符号定方向、`SL=1.0×ATR`、`TP=1.5×ATR`、`lots=0.01`）。
- **position state**：`account_positions` 两侧一致按券商实仓计。
- **Risk 输入**：两侧 `risk_reasons=[]`；`data_age/slippage` 两侧均为**写死 0**（既有缺陷，非重启引入）。

**B2 可 replay 部分（已执行，输入 hash 已保存）**：
- `label_adapter.py --replay`（用冻结 M1 源重建 M15 再标注，与冻结序列逐点比对）：
  `overlap_bars=40546 / frozen_match=40546 / state_match=40546 / 100% / reproducible=true`。
  - 输入 hash：`xauusd_m1_histdata.parquet` = `dd633889fa63586baae9a726079c1643f9671c20895306f49f284d57783601dd`；
    `state_v2_series.parquet` = `792356d34ffe6b2c5d0b6c956095e7ddbb1d4bab12b46dca3c70722b79b5c914`。
- **限制（`DATA_GAP`）**：live 路径的逐周期 **MT5 M1 bars 未归档**（只存于终端）；且 tick 归档仅 ~25 天 < hysteresis 收敛所需 ~5000 根 M15（约 52 天）⇒ **无法**对重启前后那两个周期的**实况输入**做逐字 replay。标签链本身的确定性已由 B2 证明。

---

## C. 隐藏状态清单（`state_diff.json`）

| 状态 | 重启前 | 重启后 | 机制 | 结论 |
|---|---|---|---|---|
| **label / hysteresis** | 存在（进程内） | **重算** | 每周期由 MT5 M1（~90000 根，>5000 根 M15 收敛阈）重算；k=2 路径相关 | **不持久 → 不丢**（B2 证明确定） |
| **RiskGuard**（`daily_loss`/`consecutive_losses`/`day`） | 恒 0（内存态） | 恒 0 | 每周期 `RiskGuard()` 新建；**从不写回** | **无状态可丢**（前后同值） |
| **position state** | 券商持有 | 券商持有 | `mt5.positions_get()` | **不丢**（非引擎持久） |
| **时间基准** | 模块导入时 `NOW` | 同 | `roll_day(NOW[:10])` | 仅进程启动时刻变 |
| **MT5 terminal/data cache** | — | 刷新 | 重启重建连接（显式 path） | 无持久状态 |
| **ledger** | 存在 | **恢复** | `Ledger.verify()` 每周期；链跨重启延续 | **持久**（未丢） |
| **snapshot 字段** | — | — | 无重启相关变化（形状自 09-28T12:43 恒定 5 键） | 无变化 |

**无「重启后未恢复」的状态项**；亦无「重启后才初始化」的新状态。

---

## D. 最终判定

**最终回答：重启后 7 笔全部亏损，是否存在可证实的运行输入/状态/代码变化可以解释这一行为？**

> **`INCONCLUSIVE`** —— **不存在可证实的**运行输入 / 状态 / 代码变化可解释这 7 笔全亏。

依据：
1. **代码**：重启窗口内**没有**影响决策/执行的代码变化（唯一改动 = 券商平仓对账，属**账本观察层**，不改变决策与下单）；10-01T14:33 写入的逐字内容 `DATA_GAP`，但总 delta 已恢复且行为中性。
2. **输入**：重启前后记录的 `state/family/trend_20/atr/bar 时间/spread/signal/order intent` **连续且同构**；`last_bar_utc` 无回退。
3. **状态**：`label/hysteresis` 每周期重算（无持久态可丢）；`RiskGuard` 前后恒 0（无状态可丢）；`position` 由券商持有；`ledger` 跨重启验证通过。
4. **唯一与结果同步者 = 重启本身**（时间关联），且前序重启审计为 `NO_EVIDENCE_OF_RESTART_CAUSALITY`。
5. 已知使 2 笔“本可避免”的**风控接线缺陷**是 `E0` 起即存在的**原始架构自带**问题，**非重启造成**，且不足以解释 7 笔全亏。

### 判定分类

| 判定 | 对象 | 依据 |
|---|---|---|
| `CONFIRMED_CHANGE` | 09-30 新增**券商平仓对账**（账本观察层） | V0→V2 diff；memory 2026-09-30 |
| `NO_CHANGE_FOUND` | MT5 初始化 / 时间语义 / M1·M15 / label_adapter / MA20·ATR14 / RiskGuard / signal_baseline / position·state / 订单执行（窗口内） | V0→V2 diff + ledger schema 恒定 |
| `NO_CHANGE_FOUND` | 重启前后**记录输入/状态**（state/family/trend/atr/bar/spread/signal/intent） | `pre_post_replay.csv` |
| `ASSOCIATION_ONLY` | 重启时点 ↔ 7 笔全亏（A 段 +49.89 → B 段 −67.75） | 时间同步但无结构/输入/状态变化 |
| `CAUSAL_EVIDENCE` | **不存在** | 未发现任何可证实的因果通道 |
| `UNKNOWN` | 10-01T14:33 写入的逐字内容；净零编辑之可能 | 无成对样本 / 不可证伪 |
| `DATA_GAP` | live 路径逐周期 MT5 M1 输入未归档 → 实况输入不可 replay | B2 限制 |

---

## E. 关键证据与指纹
- 版本链：V0 `ea686195…` / V2 `dcb7edde…` / V3 `a98d8d0e…` / V4 `2d8f50d5…` / V5 `0ed44fb8…`（全哈希见 `evidence_manifest.json`）。
- 冻结 replays 输入：M1 `dd633889…`、state 序列 `792356d3…`。
- 产物哈希：`SHA256SUMS.txt`。

**边界声明**：本报告未修改任何代码/配置/状态/账本，未回滚、未修复、未发单（`order_send=0`）。
