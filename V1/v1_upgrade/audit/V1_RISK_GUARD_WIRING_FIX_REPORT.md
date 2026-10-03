# V1 risk-guard wiring fix — staged report (READ-ONLY + STAGED; production NOT modified)

- 任务：修 `v1_upgrade` 声明的 4 条风控限额"运行时不可能触发"，最小修复。
- 判定：缺陷**确认成立**；修复**已完整实现并离线验证，但未写入生产**（任务书要求先获用户同意；本次未获答复）。
- 生产文件状态：**未改动**。未发任何订单，未发 order_check。

## 1. 只读复核结论（任务书 4 处缺陷逐条确认）

| 声明限额 | 检查点 | 谁喂它 / 实参 | 是否生效 |
|---|---|---|---|
| MAX_POSITION | `gates.py` `evaluate()` | 实时 `len(positions)` | ✅ 生效 |
| SPREAD_LIMIT | `evaluate()` | 实时 `spread_bps` | ✅ 生效 |
| MAX_DAILY_LOSS | `evaluate()` | `daily_loss` ← `note_close`（**全仓无调用**） | ❌ 未接线 |
| MAX_CONSECUTIVE_LOSS | `evaluate()` | `consecutive_losses` ← `note_close`（**无调用**） | ❌ 未接线 |
| STALE_DATA | `evaluate()` | `data_age_seconds` ← **写死 0** | ❌ 未接线 |
| SLIPPAGE_LIMIT | `evaluate()` | `slippage_bps` ← **写死 0** | ❌ 未接线 |

- `gates.py:113` `note_close()`：仅定义、无调用。
- `cycle.py:287` `rg = RiskGuard(); rg.roll_day(NOW[:10])`：每轮新建 ⇒ 计数器恒 0。
- `cycle.py:289-290` `slippage_bps=0, data_age_seconds=0`：写死。
- 活账本（复核时 610 事件，sha256=`86bdd2b2…`，`verify()`=True）DECISION 的 `risk_reasons` 直方图**仍只有 `MAX_POSITION`（167 次）**。
- 缺陷**仍在活跃**：复核时 10-02 已再度出现 2 笔 SL，且引擎仍按下单路径运行。

## 2. 离线复现（只用账本 + 券商事实，未连 MT5、未写文件）

脚本：`audit/staged_fix/offline_repro.py`（只读）。
**"应拒绝而实际放行"次数 = 8 / 32 笔真实开仓**（09-30：6，10-01：2）；四种口径组合（价差/净额 × UTC/服务器帧）**均为 8**，结论稳健。

09-30 的关键序列（净额、UTC 日）：日亏累计一路走低至 **−51.33**，第 4 笔起 `MAX_CONSECUTIVE_LOSS` 触发；
10-01 连亏达 4，第 4 笔触发。即：**声明 `max_consecutive_loss=3`，线上实际放到 7 连亏 / 4 连亏。**

## 3. 修复（STAGED，未应用）— 见 `audit/staged_fix/PATCHES.md`

- `gates.py`：新增 `rebuild_risk_state()`（从账本 CLOSE/PNL 回放重建计数器，`roll_day`/`note_close` 语义不变）、`data_age_seconds()`（**同源服务器帧**）、`last_realized_slippage_bps()`、`realized_pnl()`；`import` 增 `timedelta`。
- `cycle.py`：`287-290` 改为"回放重建状态 + 真实 data_age（同源帧）+ 真实滑点（最近一次 ORDER_SEND 实测）"；`reconcile_broker_closes` 的 PNL 事件**增补** `commission/swap`（不改既有键，replay 口径不变）。
- 未改：alpha / 策略 / 映射表 / prompt / 阈值 / **任何限额数值** / 执行路径 / 权限。仅让守卫**更能拒**。

暂存实现：`audit/staged_fix/risk_state.py`（非生产模块，import 未改动的 `gates.RiskGuard`）。

## 4. 回归测试（暂存，已跑）

`audit/staged_fix/test_risk_guard_wiring.py` → **12/12 PASS**：
连亏达 3 → 第 4 笔拒；日亏 ≤ −20 → 拒；陈旧数据（同源 age>900 / age=None）→ 拒；滑点超限 → 拒；
正常路径不误拒；跨日隔离不误计；账本级复现 = 8。

## 5. 验收状态

| 项 | 结果 |
|---|---|
| 离线重算 09-30 窗口"应拒而放行"次数 | **8**（09-30:6 / 10-01:2） |
| 回归测试（连亏/日亏/陈旧/正常/滑点） | **12/12 PASS**（暂存） |
| 账本哈希链 `verify()` | True（只读复核；未改动账本） |
| `--dry-run` | **未执行** —— 需先获同意；且现 `--dry-run` 会向**生产账本**追加 DECISION（及可能的 reconcile CLOSE/PNL），并非零写入 |
| 生产文件"未触碰" | 见 `audit/staged_fix/PRODUCTION_HASHES.txt`（`gates.py`/`cycle.py`/`run_gates.py`/`registry/*` 哈希已留档，可复算比对） |

## 6. 遗留观察（不在本次范围内，未改）

- `DUPLICATE_ORDER` 结构性失效：`order_id = f"{MAGIC}-{NOW}"` 每轮唯一，永不匹配；非 4 条声明限额之一。
- 券商 SL/TP 平仓 → 账本对账**最大约 31h 延时**，会让连亏/日亏计数滞后。
- 旧 PNL 事件无 `commission/swap`（按价差计），新事件按净额 —— 混合口径仅影响 apply 前的历史。
- 无成交历史时滑点默认 0（不拦）；首单无法被"未测量量"拦。

## 7. 待用户确认（阻塞 apply）

1. 是否批准将上述改动写入生产 `gates.py` / `cycle.py`（并按需补 `commission/swap`）并落回归测试？
2. 状态持久化方式：**账本回放重建（推荐，暂存实现即此）** vs 独立 state JSON。
3. 日亏/连亏口径：**净额 profit+commission+swap（推荐）** vs 价差（账本现有 `PNL.pnl`）。

未发现需要改动"限额数值本身"的情况；声明值维持 `max_daily_loss=-20 / max_consecutive_loss=3 / stale=900 / slippage=15bps / spread=30bps`。
