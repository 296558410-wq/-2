# V1 RiskGuard 生产接线修复报告

- 授权：2026-10-02 用户任务书（**正式授权**将推荐方案落地生产）
- 最终状态：**`PATCH_APPLIED_VALIDATED`**
- 边界：未改策略/信号/限额数值/仓位规则/执行路径/cron/MT5 配置；未主动开仓；未触碰 V2/V3；`LIVE` 逻辑未升级。

## 1. 采用方案（按要求）
1. **写入生产**：`gates.py` + `cycle.py` 暂存补丁（不新增独立 state JSON）。
2. **状态**：**账本回放重建** RiskGuard 状态（`rebuild_risk_state`）。
3. **盈亏**：统一 **净额 `profit + commission + swap`**（`realized_pnl(basis="net")`；PNL 事件增补 `commission/swap`，不改既有键与 replay 口径）。
4. **真实输入**：真实 `data_age`（tick 与 bar **同源服务器帧**相减）、真实滑点（最近一次 `ORDER_SEND` 实测）、`note_close()` 正式接入、跨轮恢复、跨日隔离（UTC 日）。

## 2. 备份
- `v1_upgrade/backup/20261002T034821Z/`（`gates.py` / `cycle.py` / `runtime_config.json` / ledger 副本 + `backup_manifest.json`）。
- 前置账本快照：`v1_upgrade/ledger/_pre_apply_snapshot.json`（**619 行**，sha256 `2001d238286c4d9131a57188ef59088d8a70092d51dae4972b7e4ea947c16721`）。

## 3. 修复前后生产文件 SHA256

| 文件 | 修复前 | 修复后 | 变化 |
|---|---|---|---|
| `gates.py` | `0e02a424…f2c9d3` | `0f42d301…3dc0919` | ✅ 改（新增回放/真实输入 5 个 helper） |
| `cycle.py` | `dcb7edde…61b523b` | `a98d8d0e…2dd343a` | ✅ 改（回放重建 + 真实输入 + PNL 增补 + 观测字段） |
| `run_gates.py` | `c2fc89be…e7018a7` | 同 | ⚪ 未变 |
| `registry/runtime_config.json` | `0732456a…f062b38` | 同 | ⚪ 未变 |
| `label_adapter.py` | `3e67542e…c4d5d4189` | 同 | ⚪ 未变 |

完整 unified diff：`V1_PATCH_DIFF.txt`；机器可读：`V1_PATCH_HASHES.json`。

## 4. 验收结果

| 项目 | 结果 |
|---|---|
| **12/12 回归测试** | **12/12 PASS**（连亏达3拒第4笔、日亏≤−20拒、陈旧拒、滑点拒、正常不误拒、跨日隔离、账本复现） |
| **8/32 故障复现** | **8/32**（09-30:6、10-01:2），价差/净额 × UTC/服务器帧四种组合一致 |
| **隔离验证** | `ISOLATED_VERIFICATION_PASS`（临时副本账本链 OK 619 条目；反事实 8；跨日隔离 true；`cycle.py` order_send/order_check 仍各 1） |
| **dry-run 结果** | `action=`**`WAIT_RISK:MAX_DAILY_LOSS,MAX_CONSECUTIVE_LOSS`**；`order_sent=false`；真实 `data_age=17.0s`、真实滑点 `1.4464 bps`、`daily_loss=-25.41`、`consecutive_losses=3` |
| **`order_send`** | **0** |
| **`order_check`** | **0** |
| **新增真实成交数** | **0**（dry-run 新增事件只有 1 条 DECISION，无 ORDER_SEND/ORDER_CHECK/FILL/POSITION） |
| **账本 SHA256 链** | **OK**（620 条目，`verify()`=True） |
| **Git commit** | 见文末 `PATCH_COMMIT` |

## 5. dry-run 副作用诚实说明（**非零副作用**）

- `--dry-run` **不是零副作用**：它向**生产账本**追加了 **1 条 `DECISION`**（seq 620），账本 619→620 行。
- 明确区分：**修复前生产事件 = 1..619**（sha256 `2001d238…`）；**本次验证新增事件 = 仅 seq 620 的 DECISION**（无其它类型）。明细见 `V1_DRYRUN_ACCOUNTING.json`。
- **无真实订单、无 order_check、无 broker 侧副作用**（`mt5.order_send`/`order_check` 调用数 = 0；未产生 FILL/POSITION）。
- 该新增 DECISION 由修复后的引擎自身写入，是**修复在生产运行中的首次真实决策**：它证明守卫已生效并**当场拒绝了开仓**。

## 6. 未变 / 残留（如实收口）

- 未修改任何限额数值、策略、信号、映射、cron、MT5 配置；V2/V3 未触碰。
- 交易券商侧 SL/TP 平仓 → 账本对账最大约 31h 延时**未修**（超范围）。
- `already_sent`/`DUPLICATE_ORDER` 因 `order_id = f"{MAGIC}-{NOW}"` 每轮唯一而结构性失效（非 4 条声明限额之一，未改）。
- 旧 PNL 事件无 `commission/swap`（按价差计），新事件按净额；混合口径仅影响 apply 之前的历史。
- 无成交历史时滑点默认 0（不拦）；首单不被“未测量量”拦。

## 7. 最终状态

**`PATCH_APPLIED_VALIDATED`**

*PATCH_COMMIT: `63d5a22109126770efd3ff235a7d32593f25e484`（path-limited：`v1_upgrade/gates.py` + `v1_upgrade/cycle.py` + `trader_v1/audit/` 修复报告与验证产物）*
<!-- project: path:C:\AIQuant -->
