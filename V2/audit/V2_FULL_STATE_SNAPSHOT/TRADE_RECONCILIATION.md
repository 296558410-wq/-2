# TRADE_RECONCILIATION — 三方逐笔对齐（broker ↔ ledger ↔ 决策/执行记录）
结论先行：**V2 从未产生一笔真实（券商或 paper 正式）成交。** 三方对齐结果 = **0 笔**。

## 1. Broker（MT5 权威事实）
按 magic 扫描 `history_deals_get`（2026-08-01 → now）：

| magic | 开/平（deals） | 归属 | 备注 |
|---|---|---|---|
| 0 | 1 / 1 | 遗留 | — |
| 90001 | 41 / 41 | collect/测试 | comments: cleanup/exec-instrument/diag |
| 90002 | 110 / 109 | **旧 V1** | — |
| 90011 | 32 / 32 | **新 V1** | — |
| **（V2 magic）** | **不存在** | — | **无任何 magic 映射到 V2** |

⇒ **V2 券商成交 = 0**。（当前账户为空仓/无挂单。）

## 2. V2 ledger — `ledger/hermes_v2_ledger.jsonl`
- **12 条事件，全部发生于 2026-09-11T13:09:29Z**（同一秒），`strategy_id="demo_calibration"`、`environment=execution_mode="BROKER_DEMO"`。
- 类型：DECISION×2 · EXECUTION_REQUEST×2 · ORDER_REJECTED×1 · EXECUTION_RESPONSE×1 · ORDER_ACCEPTED×1 · FILL×1 · POSITION_OPEN×1 · POSITION_CLOSE_REQUEST×1 · POSITION_CLOSED×1 · PNL×1。
- 性质：**一次 calibration 自测序列**（含 1 次 FILL 与 1 次 REJECT），**无对应券商成交、无对应计划/运行**。

## 3. 决策 / 机会记录
- `state/hermes_memory.jsonl`：**1671 条决策**（WAIT 1443 / **TRADE 167** / REJECT 61），**outcome=null 者 1671/1671（0 条有结果标注）**。
- `state/opportunity_ledger.jsonl`：**2815 条机会**（geo_shock 1442、narrative_flow_divergence 431、macro_repricing_short 329、trend_long 152、bo_long 140、fbo_long 93、bo_short 75、fbo_short 68、trend_short 58、macro_repricing_long 27）。
- **167 条 TRADE 决策 → 0 笔执行**。

## 4. paper 记录
- `state/paper_executions.jsonl`：**6 行**，全为 smoke/合成（`DEC-ctx-smoke`、`P`）：
  - `PPOS-DEC-ctx-smoke`：fill 4350.21 → close 4349.79，`net_usd=-1.68`（module4_close）
  - `PPOS-P`：4 行 fill（plan `P`），**从未平仓**
- `state/paper_account.json`：initial_balance=200 · balance=150 · equity=149.79 · **realized_pnl=0.0** · `closed_trades=[]` · 1 个 OPEN 合成位 `PPOS-P`（2026-09-12 开）。

## 5. 统计（V2 真实）
| 指标 | 值 |
|---|---|
| 总交易数 | **0**（券商 0；正式 paper 0） |
| LONG / SHORT | 0 / 0 |
| W / L | 0 / 0 |
| gross P&L | 0 |
| commission / swap | 0 |
| net P&L | 0 |
| R | n/a |
| 胜率 | n/a |
| 最大连续亏损 | n/a |
| 每日 P&L | n/a（无成交日） |
| 每笔交易的 Agent/opportunity/decision/risk/execution 映射 | **不存在**（无成交可映射） |
> 仅存在两笔**测试性**合成记录：smoke `−1.68`（已平）与 `PPOS-P`（未平，浮亏 −0.21，未实现）。

## 6. 历史声明 ↔ broker 实际 不一致清单（全部列出）
| # | 声明/记录 | 实际 | 性质 |
|---|---|---|---|
| 1 | config `account.initial_balance=10000` | `paper_account.initial_balance=200` | 配置 vs 运行态不一致 |
| 2 | config `execution_mode=BROKER_DEMO`、`broker_demo_enabled=true` | 活跃 run = `V2-PAPER-*`；`backend=paper_local`；券商无 V2 成交 | **执行模式漂移** |
| 3 | 167 条 `TRADE` 决策 | 0 笔执行 / 0 挂单 | 决策 ≠ 执行（参照器占位） |
| 4 | `paper_account.balance=150`（自 200 降） | `realized_pnl=0.0`、`closed_trades=[]` | 余额变动无已平仓对应（合成夹具） |
| 5 | V2 ledger 含 1 次 `FILL` | broker 无对应 magic 成交 | 账本事件无券商对手方 |
| 6 | `paper_executions` 有 `PPOS-DEC-ctx-smoke` 平仓 net −1.68 | `paper_account.closed_trades=[]` | 账实未对平 |
| 7 | run 计数（wait 1059/trade 125/reject 25=1209） | `hermes_memory`（1443/167/61=1671） | 口径不同（本 run 窗 vs 全历史） |
| 8 | `runs/ACTIVE.json` end_utc 2026-10-02T20:52Z | 当前 14:1xZ（窗内） | 一致（无异常） |

**结论**：#1–#7 均为**记录/口径不一致**，非“隐藏成交”；核心事实是 **V2 无任何真实交易**。
