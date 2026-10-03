# V1 失败知识库（V1_FAILURE_KNOWLEDGE_BASE）

> 失败实验也是资产。以下条目已证伪或已定位；**除非数据/机制发生实质变化，禁止重复研究**。每条附复现与影响。

## F-001 声明风控限额可在每周期新建守卫下生效
- 假设：`RiskGuard` 在 `evaluate()` 里检查的 4 条限额会在运行时触发。
- 结论：**证伪**。守卫每周期新建 + `note_close` 无调用 + 输入写死 ⇒ 4 条永不触发（V1-D001）。
- 影响期：2026-09-28T12:33Z → 2026-10-02；影响交易 32 笔（8 笔应拒未拒）。
- 复现：`v1_upgrade/audit/staged_fix/offline_repro.py` → 8/32。
- 状态：**已修**（commit `63d5a22`）。

## F-002 “重启导致连续亏损”是重启状态缺陷
- 假设：重启后风控状态从 0 错误初始化，导致连亏。
- 结论：**证伪**。计数器**本来就恒为 0**（每周期归零）；重启点“应有状态”= daily +38.99 / consec 0，正确接线也不会拦（`NO_RESTART_STATE_BUG`）。
- 复现：`V1_RESTART_STATE_AUDIT.json`。
- 状态：归因于 F-001（守卫哑火），非重启。

## F-003 账本 PnL 等于净额
- 假设：ledger 的 PnL 可直接当净收益。
- 结论：**证伪**。账本 PnL = 价差分量；净额需加 commission/swap（窗口内 13.97 vs 8.78，差 5.19）。
- 复现：`V1_TRADE_RECONCILIATION.json` identities；`V1_LEDGER_REPLAY_AUDIT.json` cross_check。
- 状态：新事件已补成本项（V1-D004，MITIGATED）。

## F-004 单日盈亏可用服务器帧日期聚合
- 假设：按服务器帧(UTC+3)日期分桶即可。
- 结论：**证伪**。会把最差日算成 −9.59；按引擎 UTC 日口径才是 −19.70（帧选择直接翻转“是否贴限”）。
- 复现：见前期审计 §8 与 `V1_ALPHA_STATS.json` 按 UTC 日。
- 状态：口径已固定为 UTC。

## F-005 “1 次成功发单 = 1 张 order”
- 假设：券商 order 数 == ledger 成功发单数。
- 结论：**证伪**。券商 SL/TP 触发也各生成 1 张 order（窗口内 59 = 30 开 + 29 平）。
- 复现：`V1_EXECUTION_AUDIT.json`（orders 64 = 32 开 + 32 平）。
- 状态：对账已按 comment/filling 拆分；此为自查误报，已纠正。

## F-006 控制臂收益可作为 V1 策略有效性证据
- 假设：`BASELINE_TRANSITION` 的历史收益能证明 V1 有 alpha。
- 结论：**证伪**。该臂是控制组（非 Hermes），registry 明示 UNSUPPORTED；n=32、t≈−0.3、p=0.78、成本后为负 ⇒ 无 edge（V1-D012/D013）。
- 状态：ALPHA STATUS = UNKNOWN。

## F-007 DUPLICATE_ORDER 能防重复下单
- 假设：该守卫在运行时会拦截重复。
- 结论：**证伪**。`order_id` 每周期唯一、`already_sent` 恒空 ⇒ 结构性不可达（V1-D002）。
- 复现：`V1_RISK_RUNTIME_MATRIX.json` DUPLICATE_ORDER。
- 状态：OPEN（超出「4 条声明限额」范围，未改）。
