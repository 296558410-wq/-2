# ISSUE_NOTE — run V2-PAPER-20260915-112856-d341 (archived, BLOCKED)

## 事故
- 2026-09-16 **01:08:07Z（本地 09:08）** 起 `BLOCKED`：`PAPER_REPLAY_MISMATCH (net_pnl, trade_count, commission)`。
- 触发点：本 run 首笔真实成交被 **broker 侧 TP 自动平仓**（POSITION_OPEN seq 95 @4292.60 SHORT 0.01；
  broker deals 平仓 @4277.75 → gross +14.85 / commission −0.22 / **net +14.63**；账户 1035.96 → **1050.59**）。
- 此后 9.5 小时无新周期（调度每 15 分钟只做 0.2s 空转；run 保持 BLOCKED）。

## 根因（1 个工程 bug，已修）
`_account_match()`（BROKER_DEMO 分支）比较「账本 replay 的已实现量」与 `executor.acc["closed_trades"]`。

- `executor.acc["closed_trades"]` **只在 `BrokerDemoExecutor.close()` 里 append**；
- broker 侧（SL/TP）自动平仓走的是 `reconcile_broker_closes()` —— 它**只写账本，不更新 executor 状态**；
- 且每个周期都会 `pe.connect()` → `_fresh()` 把 `closed_trades` **清空**。

→ 于是对比必然为：`net_pnl:false (14.63 vs 0)`、`trade_count:false (1 vs 0)`、`commission:false (−0.22 vs 0)`，
`balance:true`（与 `state/v2_run_health.json` 记录的 detail 逐字一致）。

**即：只要发生一次 broker 侧先于账本平仓，V2 就必然 BLOCK。** commit `3113801` 引入的对账路径是该
bug 的载体，本 run 是其上线后**第一次真实触发**。

## 实际发生的 broker 事件（demo 160761384，非策略成绩）
- SHORT 0.01 XAUUSD @4292.60 → TP 4277.75，**net +14.63 USD**；0 持仓；余额 1050.59。
- 该笔**完整记入账本**（POSITION_CLOSED/COST/PNL/ACCOUNT_SNAPSHOT，seq 117–120），
  账本链 `verify_ledger` = True，`conservation` = True。

## 处置
- 本 run **finalize 归档为 BLOCKED**（保留全部历史；**未删改账本/决策/时间线**）。
- 修复见 commit（见 `RUN_META` / 最终报告）：
  `reconcile_broker_closes` 现在在状态语义上与 `close()` 一致：
  (Phase A) broker 侧平仓 → 账本 + executor 双写；
  (Phase B) 账本已平仓的全部 position → 从 broker deals **重建** executor 已实现视图（跨 reconnect/restart 持久）。
- 回归：`tests/test_broker_reconcile.py` T1–T8（含 broker 自动 TP/SL、重复对账、重启恢复、部分状态 fail-closed）。
- **不**通过修改历史账本让旧 run「看起来正常」；继续运行以**新建 continuation run** 承接。

## 该笔 +14.63 的定位
作为 **有效 Broker Demo 执行证据** 保留；同时它是 **GC=F / XAUUSD 价空间错配**的首个案例
（见 `research/ISSUE_GC_SPOT_PRICE_SPACE_MISMATCH.md`）。不得删除、不得重写、不得重算为「理论正确」。
