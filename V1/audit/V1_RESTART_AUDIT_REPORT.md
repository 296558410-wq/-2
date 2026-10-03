# V1 重启后连续亏损专项审计报告

- 生成：2026-10-02（GMT+8） · 范围：新版 V1（`research/hermes/trader_v1/v1_upgrade`，magic 90011，DEMO）
- 口径：**MT5 券商成交事实 > Ledger > Hermes 声明**；只读券商，未发单、未发 order_check。
- **判定：`RUNTIME_GUARD_BUG_CONFIRMED`（运行期守卫未接线）+ `NO_RESTART_STATE_BUG`（无重启特有状态缺陷）+ `FIX_VALIDATED_NO_PRODUCTION_CHANGE`（暂存修复已验证，未动生产）。**

---

## 1. 重启事件与调度

| 项 | 事实 |
|---|---|
| 重启时刻 | host `LastBootUpTime` **2026-10-01 21:52:15 GMT+8 = 13:52:15Z**；python 进程 21:54 起 |
| 调度 | OpenClaw cron `v1-upgrade-demo-cycle`（`3-59/15 * * * *` UTC），重启后存活 |
| 漏拍 | 重启期间 **漏 1 拍（14:03Z）**；14:18Z 恢复；缺口 **30.0 min**（13:48→14:18） |
| 看门狗 | 无专用看门狗；调度本身即唯一守护，无自愈动作 |

## 2. 重启余留状态审计

| 检查 | 结果 |
|---|---|
| 持仓 / 挂单 | **空仓、无挂单**（重启时 `positions=[]`；最近一笔已于 13:33Z 前平） |
| pending close / 未完成写 | **无跨重启的 CLOSE**；最大对账延时 112397s 属 09-29 批量补记（早于重启） |
| 数据新鲜度 | 重启后首轮 14:18Z；`live_state.last_bar`（服务器帧）17:15 = **14:15Z** ⇒ 实际 age ≈ **3 min（新鲜）**；但守卫被喂 **`data_age_seconds=0`（写死）**，运行期从未测量 |
| 时间帧 | 实测服务器偏移 **10800s（UTC+3）**，与声明一致；引擎 `roll_day(NOW[:10])` 用 **UTC 日期** |
| 权益 / 回撤 | 重启后净额 **−67.75**；全窗 max DD（净额）**−72.5**；余额 1923.39（09-28 审计快照 1949.93） |

## 3. 重启后逐笔追踪（7 笔，全亏）

引擎在这 7 笔后转为 `FAMILY_*_NO_TRADE` 观望，未再开仓（故不足 10 笔）。净额/连亏为券商事实（含 commission/swap）。

| # | position_id | 开(UTC) | 平(UTC) | 方向 | SL/TP | 滑点 bps | 净额 | 旧逻辑 | 正确接线 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2378322488 | 14:33 | 14:39 | SHORT | SL | −0.12 | −9.51 | 放行 | 放行 |
| 2 | 2378333628 | 15:03 | 15:20 | SHORT | SL | +3.39 | −8.78 | 放行 | 放行 |
| 3 | 2378343004 | 15:33 | 15:38 | SHORT | SL | 0.00 | −11.01 | 放行 | 放行 |
| 4 | 2378348994 | 15:48 | 17:30 | SHORT | SL | −0.38 | −11.81 | 放行 | **应拒（MAX_CONSECUTIVE_LOSS）** |
| 5 | 2378382127 | 18:48 | 10-02 00:21 | LONG | SL | +0.79 | −11.77 | 放行 | **应拒（MAX_CONSECUTIVE_LOSS）** |
| 6 | 2378409328 | 10-02 01:18 | 01:38 | SHORT | SL | −0.84 | −7.66 | 放行 | 放行（新 UTC 日，连亏计数重置） |
| 7 | 2378413449 | 10-02 01:48 | 02:05 | SHORT | SL | +1.45 | −7.21 | 放行 | 放行 |

- 重启后：**7 笔全部亏损、0 胜**；最长连亏 **7**（含重启前 10-01 14:33 起，跨 UTC 日共 4+3）。
- 正确接线后的反事实：**2 笔（第 4、5 笔）应被拒而实际放行**；日亏未破 −20（未触发 MAX_DAILY_LOSS）。

## 4. 根因判定（重启 vs 运行期）

1. **重启本身未注入错误风控状态。** 重启时刻"应有状态"按券商事实重算 = `daily_loss=+38.99, consecutive_losses=0`（UTC 日 10-01），因此即使守卫已正确接线，**重启那一瞬也不会拦截**。
2. **旧逻辑下计数器恒为 0**（`cycle.py:287` 每轮新建 `RiskGuard()`；`gates.py` 的 `note_close()` 全仓无调用）。"重启后从 0 恢复"与"本来就恒为 0"**不可区分** ⇒ 缺陷**非重启特有**。
3. 真正的运行期缺陷 = 已知的 4 条声明限额（`MAX_DAILY_LOSS / MAX_CONSECUTIVE_LOSS / STALE_DATA / SLIPPAGE_LIMIT`）未接线，从不生效；实际只有 `MAX_POSITION` + `SPREAD_LIMIT` 发话。
4. ⇒ **`NO_RESTART_STATE_BUG` + `RUNTIME_GUARD_BUG_CONFIRMED`**。重启后连亏 = 策略进入亏损段 × 守卫哑火（不是重启残留/状态不恢复）。

## 5. 修复验证（暂存，未应用）

| 项 | 结果 |
|---|---|
| 回归测试（独立重跑） | **12/12 PASS**（连亏达3拒第4笔、日亏≤−20拒、陈旧拒、滑点拒、正常不误拒、跨日隔离、账本复现） |
| 故障复现（独立重跑） | **应拒而放行 = 8 / 32**（09-30:6，10-01:2），四种口径组合一致 |
| 执行路径 | `cycle.py` 的 `mt5.order_send(` / `order_check(` 仍各 **1**；补丁**新增 0** 个此类调用；`--dry-run` 下 action=WOULD_ENTER ⇒ 发单块不可达 |
| ORDER_SEND 控制 | 仍受 `registry/runtime_config.json` 的 `order_send_enabled` 控制（本次审计未改；本次 0 下单 / 0 order_check） |
| 生产副作用 | 生产文件指纹与审计前基线**逐一相同**（`gates.py`/`cycle.py`/`run_gates.py`/`runtime_config.json`） |
| 判定 | **`FIX_VALIDATED_NO_PRODUCTION_CHANGE`** |

修复仅把 `RiskGuard` 的**状态来源**从"每轮归零"改为"按账本 CLOSE/PNL 回放"，并把 `data_age_seconds`/`slippage_bps` 从写死改为真实量；不涉及 alpha/策略/阈值/限额/执行路径。

## 6. 边界声明

- 未改动任何生产代码 / 配置 / 限额 / 权限 / 运行状态；未启动生产周期；未下单、未发 order_check。
- 仅只读读取 MT5 成交/订单历史与 v1_upgrade 账本。
- 本次只提交 V1 审计产物（见文末 commit）。

## 7. 产物与复现

| 文件 | 内容 |
|---|---|
| `V1_RESTART_TRADE_TRACE.json` | 重启前后全量逐笔（券商事实 + 账本交叉引用） |
| `V1_RESTART_STATE_AUDIT.json` | 重启状态审计（持仓/写操作/数据新鲜度/时间帧/调度/回撤/反事实） |
| `V1_RISKGUARD_FIX_VALIDATION.json` | 修复验证（回归/复现/执行路径/副作用） |
| `README.md` | 脚本与复现说明 |
| `v1up_restart_audit_build.py` / `v1up_restart_details.py` / `v1up_fix_validation.py` | 生成脚本（自包含可重跑） |

复现：`C:\AIQuant\.venv\Scripts\python.exe <script>`；暂存修复与回归测试见 `v1_upgrade/audit/staged_fix/`。

---

*AUDIT_COMMIT: `df18f6bb769394d6fb4b3d971015b037396d655d`（仅提交本目录审计产物；生产代码未改动/未提交）*
<!-- project: path:C:\AIQuant -->
