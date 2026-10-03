# V1 Truth System 架构（V1_TRUTH_SYSTEM_ARCHITECTURE）

- 目标：**V1 无论发生什么（交易/亏损/拒单/重复/重启/数据异常/MT5 异常/账实不一致），都能用唯一 ID 还原事实链与因果链。**
- 版本：`v1-truth-1`（schema v1）· 边界：只增不覆盖、`order_send=0`、不改策略/阈值/历史账本、V1/V2/V3 隔离。
- 落点：运行时库 `v1_upgrade/truth/`（`truth_lib.py` + `v1_forensic.py`）；证据 `v1_upgrade/truth/evidence/`；文档与回归 `trader_v1/audit/v1_truth_system/`。

## 1. 三层分离（不可混用）

```text
Raw Facts        MT5 broker responses / market data / 账本事件原样        ← 最高优先级
Derived Facts    ID/事件索引、Case、Incident、一致性检查、日聚合（可复算）
Interpretation   人工/AI 报告文字（仅文档，永不写进事实层）
```

## 2. 事实链覆盖（每一环都可追溯）

```text
Market Data → Data Snapshot → Hermes Context → Signal → Risk Evaluation → Decision
→ Order Intent → Order Check → Order Send → Broker Response → Fill → Position
→ SL/TP → Close → PnL → Ledger → Replay
```

| 环节 | 承载 | ID |
|---|---|---|
| Market/Snapshot/Context/Signal | DECISION.snapshot / live_state / signal | `cycle_id`,`decision_id`,`event_id` |
| Risk/Decision/Intent | DECISION.risk_* / order_intent | 同上 |
| Order Check/Send | ORDER_CHECK / ORDER_REQUEST / ORDER_SEND | `order_id`,`dedup_key` |
| Broker Response/Fill/Position | broker_facts.json + FILL/POSITION | `order_id` |
| SL/TP/Close/PnL | CLOSE/PNL + broker deals | `position_id`(=trade_id) |
| Ledger/Replay | SHA256 链 + replay | `event_id` |

## 3. 统一 ID（从任一 ID 可反查上下游）

- `event_id` = `V1E-<sha12(seq,current_hash,event)>`（确定性派生）
- `cycle_id` = `V1C-<UTC ts>`（新事件打标；旧事件由 ts 派生）
- `decision_id` = `V1D-<sha10(cycle|action)>`（新事件打标）
- `order_id` = 券商 ticket；`trade_id` = `V1T-<position_id>`；`dedup_key` = `MAGIC:SYMBOL:M15桶(服务器帧)`
- `incident_id` = `V1I-<类型>-<sha8(事实键)>`（同一事实永远同一 ID）

## 4. 关键机制

1. **Decision Snapshot（执行前写）**：`truth/evidence/decision_snapshots.jsonl`，逐行 sha256+prev 链；含“系统当时看到了什么、为什么允许/拒绝”（27+ 字段）。**写失败 ⇒ 不进新仓**（`WAIT_TRUTH:RECORD_FAILED`，fail-closed，且不改变信号/不绕过 RiskGuard/不导致重复下单）。
2. **Evidence Store（只增）**：账本（原样）+ snapshots + incidents + broker_facts（最新态缓存，标注非追加）+ cases。任何修复只形成**新事件**。
3. **Incident System**：结构性（链断/序号缺/位错/对账/PnL/计划缺口）+ 事件级（风控阻断/重复/Kill/陈旧/缺数据/MT5拒单/填充不匹配），全部确定性 ID、可标记状态；`root_cause` 允许 `UNKNOWN`。
4. **一致性检查（每周期）**：Signal↔Decision↔Risk↔Intent↔MT5↔Fill↔Position↔Close↔PnL↔Ledger↔Replay；发现不一致 ⇒ Incident（不静默）。
5. **Trade Case**：`CASE-V1T-<pid>` 十段链（signal→…→pnl）+ raw broker deals + derived（gross/commission/swap/net/一致性）。
6. **Daily Truth Report**：FACTS_ONLY 聚合 + incident 索引 + 完整性。

## 5. 运行时接线（cycle.py，最小侵入）

- 决策前：写 snapshot（失败→安全状态）；
- DECISION 事件携带 `cycle_id/decision_id/truth_record_ok`；
- 周期末尾：一致性检查 + incident 生成（**包裹在 try/except，绝不影响决策/发单**）。

## 6. 已知边界（详见 FINAL 的 UNKNOWN 列表）

- 历史事件（Truth 启用前）无 `cycle_id/decision_id`，链路由“时间相邻”补齐并**明确标注**；
- `broker_facts` 是最新态缓存（append-only 缺口，诚实标注）；
- 与交易解耦：Truth 层故障不会改变信号、不会绕过 RiskGuard；仅可能触发“不进新仓”的安全状态。
