# 新版 V1 启动后独立审计报告（V1_STARTUP_AUDIT_REPORT）

- 判定：**RISK_VIOLATION**
- 审计时间范围（UTC）：2026-09-28T12:33:29.751274+00:00 → 2026-10-01T23:33:02.821798+00:00
- 生成时间：2026-10-01T23:44:53.100007+00:00
- 口径：**MT5 券商成交事实 > Ledger > Hermes 声明**；审计只读券商，未发单、未发 order_check。

## 1. 新 V1 起始状态（启动隔离）
- 新 run 起点：ledger seq 1 @ 2026-09-28T12:33:29.751274+00:00，本条即新版 V1 第一个周期（WAIT_POSITION_OPEN）。
- 新 ledger：`v1_upgrade/ledger/v1_upgrade_ledger.jsonl`（586 事件，sha256=b5c6923c5b1da997…）；09-28T15:29:07Z 做过一次 quarantine：归档 34 条、隔离 7 条 gate 自测合成记录（order_id=X1）、保留 27 条真实记录（manifest 与归档文件哈希见 V1_AUDIT_HASHES.json）。
- 新 state/registry：`registry/v1_upgrade_registry.json`（task=V1_UPGRADE_DEMO_BUILD, magic=90011, comment=V1UP_DEMO, 预留 magic 90001/90002/90003 未被占用）+ `registry/runtime_config.json`（signal_source=BASELINE_TRANSITION，order_send_enabled=true @09-28T15:35Z 由操作员开启）。
- 初始账户/持仓：启动时 `account_positions=1`、`own_positions=0`（即账上带 1 笔**旧 V1 遗留**持仓；新版自己 0 仓，且风险门立即给出 MAX_POSITION ⇒ 未下单）。该遗留持仓由券商于 **2026-09-28T12:37:38Z 以 SL/TP 平掉**（deal 2364445494，magic=0，net −1.4；开仓腿在 08:51:31Z、magic=90002），此后 `account_positions=0`（seq 4 起），新版全过程未与旧 V1 持仓/账目发生交互。
- 初始计数器：DECISION=0 起步；本次审计期内 决策 348 条（ENTER 45 / 其它观望类 303）。
- 与旧 V1 隔离：旧 V1 magic=90002 的历史 deal 共 82 笔，最后一笔（UTC）2026-09-28T08:51:31Z ⇒ 全部早于审计窗口起点（隔离成立）。
- 代码层隔离：新版 V1 代码中对旧 V1 运行态路径的引用 = 无。

## 2. 交易总数 / 3. MT5 独立重算交易数 / 4. Ledger 交易数
- Ledger：POSITION 30（=开仓 30），PNL 29（=已平仓 29），当前在持 1。
- MT5（magic=90011）独立重算：持仓 30（已平 29，在持 1）。
- **一致**：开仓 30 == 30；平仓 29 == 29；在持 1 == 1。

## 5. PnL 独立重算 / 6. 胜负独立重算
- Ledger 声明已实现盈亏合计 = **13.97**（仅价差分量）
- MT5 独立重算（已平 29 笔）：价差分量 13.97，commission -5.82，swap 0.63 ⇒ **净额 8.78**
- 差额 = 5.19 = 佣金+swap（账本 PnL 不含成本项）⇒ 属**口径差异，非账实不符**。
- 胜负（独立重算，net>0 为胜）：**12 胜 / 17 负**。
- 余额恒等式（锚 = 券商 deal 事实）：余额现值 1949.93 − gates 快照 1941.25（2026-09-28T15:29:17Z）= **8.68**；该区间新 V1 券商净额 = **8.68**，其它 magic = **0** ⇒ **恒等式成立**
- 全窗口交叉验证：审计窗口内全部 magic 合计 7.28 = 新 V1 8.68 + 遗留平仓 -1.4（该笔发生在 gates 快照之前，已含在 1941.25 内）⇒ 1941.25 + 8.68 = 1949.93 ✓

## 7. order / deal / position 对账
- Ledger 发送尝试 40（成功 30 / 拒绝 10，拒绝 retcode 分布 {'None': 5, '10018': 5}）
- MT5 该 magic 的 order 记录 59 = **开仓单 30**（comment=V1UP_DEMO，filling 0=FOK）+ **券商 SL/TP 触发平仓单 29**（comment=[sl…]/[tp…]，filling 1=IOC）；全部 state=4 FULLY_FILLED
- 订单完整性：券商 deal 引用的 order 全都能在 order 历史中找到 = True；无 deal 的 order = 0；同一持仓重复记账 = 0；幽灵单 = 0 ⇒ 逐单可追溯
- deal 数：magic 90011 59（每笔持仓 2 条：进+出）
- ghost / missing / duplicate：0 / 0 / 0

## 8. 风险审计（逐笔）
- 单笔 volume：全部 0.01 ⇒ OK（冻结规则 max_position=1, lots=0.01）
- SL/TP 随单：全部具备（规则 SL=1.0×ATR14 / TP=1.5×ATR14，实测 realized_R ∈ {-1.0, +1.5}）
- 同时持仓上限：窗口内重叠持仓段 = **0**（0 = 从未并行持仓）
- 最大连续亏损（独立重算）：**7** 笔（净额口径；价差口径 7 笔）⇒ **突破冻结声明限额 3**；按自然日重置口径 {'2026-09-28': 1, '2026-09-29': 2, '2026-09-30': 7, '2026-10-01': 4}
- 规则接线核查：`RiskGuard.note_close()` 在 v1_upgrade 全量代码中**只有定义、无调用**；`cycle.py:287` 每轮新建 RiskGuard（计数器恒 0），`cycle.py:289-290` 把 `data_age_seconds=0`、`slippage_bps=0` 写死传入 ⇒ 声明的 MAX_DAILY_LOSS / MAX_CONSECUTIVE_LOSS / STALE_DATA / SLIPPAGE_LIMIT **不可能触发**；实际生效的只有 MAX_POSITION（实时账户持仓）与 SPREAD_LIMIT（实时点差）。证据：347 条决策的 risk_reasons 只出现过 MAX_POSITION 162 次。
- 单日亏损（UTC 自然日）：{'2026-09-28': 15.54, '2026-09-29': 15.06, '2026-09-30': -19.7, '2026-10-01': -2.12}（最差 -19.7，限额 -20.0）⇒ 未突破，但已贴限（最差日距限额仅 -0.3）
- 点差上限：实测最大 0.559 bps（限额 30.0）；滑点最大 3.3941 bps（限额 15.0）
- 越权/异常加仓/追单：账本中 ORDER_SEND 与 POSITION 一一对应，无同周期重复开仓；STOP 类事件无 ⇒ 未发现越权交易。

## 9. lookahead / PIT 检查
- data_age_seconds 取值 -10590–557s（stale 门限 900s）
- 负值（未来数据窗口）出现 1 次：[(1, '2026-09-28T12:33:29.751274+00:00', -10590.2, 'WAIT_POSITION_OPEN')] ⇒ 仅 seq 1（09-28T12:33:29Z，**该轮为 WAIT_POSITION_OPEN，未下单**）；根因是当时陈旧度用 UTC 与服务器帧 bar 时间相减，已于 09-28 修复（cycle.py 改为服务器 tick 时间同源比较）。
- 时间因果 signal→request→send→fill 违例：**0** 条
- 服务器帧标注：MT5 的 `time/time_msc` 与账本 `broker_time_utc`、`live_state.last_bar_utc` 均为 **UTC+3 服务器帧**（实测偏移 10800s，账户服务器 ForexTimeFXTM-Demo01）⇒ 与 UTC 比较时需换算；本报告中所有跨源比较均已换算。

## 10. replay 检查
- 组件官方回放 `gates.Ledger.replay()`：realized_pnl=13.97、events=586、sends=32
- 独立重建（只用券商事实，不看 V1 统计）：已平 29 笔 / 净额 8.78 / 12 胜 17 负 ⇒ 与账本笔数一致
- replay/audit hash：`f71f4bdea148004bf95bbb92c6ab3980633f2800dbea7ef485bb1a14796207d5`（同输入可复算；输入哈希见 V1_AUDIT_HASHES.json）

## 11. mismatch 清单
- 无（逐笔成交价、平仓价、PnL(价差口径) 全部逐笔相等）

## 12. 非关键问题（不影响账实一致性，但建议修）
- DECLARED_RULE_NOT_ENFORCED: max_consecutive_loss=3 被实际连亏 7 笔突破，且守卫未接线
- 账本 PnL 口径 = 价差分量（不含 commission/swap）⇒ 与券商净额差 −5.19（佣金 −5.82 + swap +0.63）；建议在账本/面板注明该口径。
- `broker_time_utc` 与 `live_state.last_bar_utc` 是 **UTC+3 服务器帧**但字段名标注 UTC（实测偏移 10800s）⇒ 按 UTC 解释的消费者会看到「未来时间」；建议改名或注明帧。
- 券商 SL/TP 平仓 → 账本观测延时最大约 31 小时（09-29T23:38Z 一次性补记 8 笔、09-30T00:03Z 补记 1 笔）；属对账补记设计，但会让「实时平仓数/连亏计数」滞后。
- `gates.Ledger.replay()` 的 open_positions 输出含 `None`/`0` 两个非票据键（早期被拒发送所致），属回放口径瑕疵；引擎判定用 MT5 实仓，未受影响。
- 10 次发单被拒：5 次 retcode=None（09-28T15:31 前后 IPC 未就绪，含「No IPC connection」）、5 次 retcode=10018（休市）；均发生在 order_send 授权（15:35Z）之前或休市时段，无越权。
- ledger 的 CLOSE 事件带 `detect_lag_sec`（券商 SL/TP 平仓 → 账本观测到的延时），最大 112397 秒；平仓由券商 SL/TP 触发、引擎在下一次对账时补记（本次 09-29T23:38Z 批量补记 8 笔 + 09-30T00:03Z 1 笔）。

## 13. 最终判定
**RISK_VIOLATION**

> 审计快照口径：ledger 是**追加式活文件**，本报告锁定的是 sha256=b5c6923c5b1da9978b54eac1ba1148e9be10a28b103312a4a28d2de9a2a7318b（审计窗口末端 2026-10-01T23:33:02.821798+00:00）。此后新周期会继续追加事件，但这些新事件不改变本窗口内的结论；需要重核时以同 sha256 + 同窗口端点复算。
> 本审计不改变任何交易权限/运行模式；未发任何订单；只读券商。新版 V1 历史表现为审计后的历史记录，不反向影响下一笔决策。
