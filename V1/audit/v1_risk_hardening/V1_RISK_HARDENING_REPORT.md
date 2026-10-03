# V1 Risk Hardening 报告（V1_RISK_HARDENING_REPORT）

- 基线：全量审计 commit `e157789e741e9974f4cb44988a97998ee9a1b456`。
- 授权：2026-10-02 任务书（只修 RISK FAIL，不做策略研究）。
- 边界遵守：V1/V2/V3 隔离（未触碰 V2/V3）；`order_send=0`；未改信号/策略/参数/成本锚；**未改限额数值**；未改历史账本（只在沙箱副本写入）；未删改历史审计结论；所有修复先测试再接线；故障注入验证通过。
- 生产文件改动：仅 `gates.py` + `cycle.py`（2 文件）。
  - `gates.py` 修复前 `0f42d30104b31868fea427340f4f7a7f8c28feddce20d38be7416d91d3dc0919` → 后 **`b784999aa3b4517c527ba4087c8db0c7ad4ad5238a25d8bc500efc185f301c06`**
  - `cycle.py` 修复前 `a98d8d0eed4d6c081a09aa2fdb3507ed7a3a1d0e7ee4fe3a66ac5aef92dd343a` → 后 **`2d8f50d52cbb67d9259d4fa207163784d21551fae4cab9293989c3e4b5dbb31b`**

## 1. FAIL-CLOSED（完成）

规则：任何安全输入**无法可靠确定** ⇒ `WAIT_RISK/BLOCK`，**禁止默认值放行**。

| 输入 | 之前 | 现在 |
|---|---|---|
| position state | `positions_get() or []` ⇒ None 当空仓 | `positions_get()` 为 None ⇒ `POSITION_STATE_UNKNOWN` 拒单 |
| daily loss | 对账异常静默继续 ⇒ 计数偏低 | 对账失败 ⇒ `note_unavailable("PNL_STATE_UNKNOWN")` 拒单 |
| consecutive loss | 同上 | 同上 |
| data age | None ⇒ `STALE_DATA`（已有） | 保持；tick/bar 不可用 ⇒ None ⇒ 拒单 |
| slippage | 无历史 → 0 ⇒ 放行 | `None` ⇒ `SLIPPAGE_UNKNOWN` 拒单（`sl>limit` 语义不变） |

实现：`gates.RiskGuard.unavailable` + `note_unavailable()`；`evaluate()` 对 `slippage_bps=None` / `open_positions=None` 拒单；`cycle.py` 在 `_reconcile_ok=False` / `_positions_ok=False` 时登记不可用。**限额数值未改**。

## 2. DUPLICATE_ORDER（D002，完成）

设计：稳定去重键 `MAGIC:SYMBOL:M15_bucket(服务器帧)`；`already_sent` 由账本 `ORDER_SEND(dedup_key, ok)` **持久化重建**（跨周期/跨重启保持）；另加**券商侧**检查（本桶内已存在本 magic/symbol 的 order ⇒ “broker 已成交但本地未确认”）。`cycle.py` 把 `dedup_key` 写入 `ORDER_REQUEST/ORDER_SEND`。

## 3. KILL_SWITCH（D003，完成）

设计：`registry/kill_switch.json`（`cycle.py` 每周期读取）：文件**缺失 ⇒ OFF**；`{"on":true}` ⇒ **BLOCK**；**不可读/损坏 ⇒ ON**（fail-closed，`KILL_SWITCH_UNREADABLE`）。操作员可写文件即可急停，运行链路**可达且可验证**。

## 4. D008 missed-cycle / watchdog（评估 + 最小修复）

- 修复：`cycle.py` 每周期计算距上一条 DECISION 的间隔，写入 `schedule_gap_minutes`；>25min 标记 `watchdog=GAP_DETECTED:<n>min`（可观测）。
- 评估：漏拍本身 **fail-safe**（不产生新风险）；持仓由券商 SL/TP 托管。**残留**：若进程彻底停死则引擎内无法自报（需外部 watcher，属运维决策，见延期理由）。

## 5. D005 / D009 / D010 逐项判定

| 项 | 判定 | 理由 |
|---|---|---|
| D009（缺数据非 fail-closed） | **必须修 → 已修** | 本任务 §1 完成；空数据不再放行 |
| D005（券商平仓→账本对账延时） | **可延期** | 守卫在**决策前**先跑 `reconcile_broker_closes`（拉取全部缺失 close）⇒ **决策时账本已是最新**；延时只影响“两次 cycle 之间”，不影响该次判定 |
| D010（replay 含 None/0 非票据键） | **可延期** | 引擎判定用 **MT5 实时实仓**，不用 replay；replay 仅诊断用途 |
| D008（无外部 watchdog） | **可延期** | 见 §4；missed-cycle 无未托管风险 |

（每条延期均显式给出 `WHY SAFE TO DEFER`，不隐藏。）

## 6. 故障注入结果（全部真实阻断）

- `V1_FAIL_CLOSED_TEST.json` = **PASS**（6 例：position/pnl/age/slippage/nohistory 全拒；负控制放行）
- `V1_DUPLICATE_ORDER_TEST.json` = **PASS**（正常放行；重复 signal / 重复 cycle / restart / broker 未确认 全拒；下一桶放行）
- `V1_KILL_SWITCH_TEST.json` = **PASS**（ON 拒；OFF 正常；缺失=OFF；损坏=ON；**沙箱集成**：`WAIT_RISK:KILL_SWITCH`）
- `V1_RISK_RUNTIME_MATRIX.json` = **PASS**（7 规则 × A–E 全 PASS）
- `V1_REGRESSION_SUITE_RESULT.json` = **CI_PASS**（14/14）
- `order_send = 0`（本次全部测试；沙箱 `order_send_enabled=false` + `--dry-run`）

沙箱集成证据：baseline `WAIT_RISK:MAX_DAILY_LOSS,MAX_CONSECUTIVE_LOSS`；kill on/corrupt → `WAIT_RISK:KILL_SWITCH,...`；均 `order_sent=false`、`ledger_chain_ok=true`。

## 7. 未修复项与延期理由

- D005 / D010 / D008（外部 watchdog）→ 延期，理由见 §5（**非继续运行前的安全阻断项**）。
- D004（账本成本口径）→ 已缓解（新事件带 commission/swap）。
- 声明：**任何无法真实阻断的保护机制都不称 PASS**；上述 PASS 均由故障注入实测得出。

## 8. 边界

未改限额数值/策略/信号/成本锚；未触碰 V2/V3；未改历史账本；未恢复真实下单；`order_send=0`。
