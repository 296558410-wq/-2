# V1 Forensic Protocol（V1_FORENSIC_PROTOCOL）

> 本协议定义“可取证”的硬规则。任何未来改动（V1/V2/V3）必须遵守；违反即 DEFECT。

## 1. 优先级（不可倒置）

```text
Raw Facts  >  Derived Facts  >  Interpretation
```

- **Raw**：MT5 broker response、行情快照、账本事件原样。不得改写。
- **Derived**：ID、索引、Case、Incident、一致性检查、聚合 —— 必须**可由 Raw 复算**，并标注算法版本。
- **Interpretation**：文档/答复；**永不写入事实层**，不得当作证据。

## 2. 不可变与只增

1. 账本与证据文件**只追加**；任何修正=新记录（`update: true`），最新记录生效。
2. 历史事件**不得为了“完整”补造**：缺失 ⇒ `UNKNOWN`。
3. 每条关键记录自哈希（`sha256` + `prev` 链）；文件级 SHA256 记录在 `V1_EVIDENCE_REGISTRY.json`。
4. Git commit + `protocol_version` + `config_hash` + `code_version` 随快照落库。

## 3. ID 纪律

- 关联**只用 ID**，禁止仅靠日志文本模糊匹配。
- 从任意 ID 出发必须能列出：上游（为什么）→ 当次（做了什么）→ 下游（结果）→ 券商事实 → 复算。

## 4. 一致性检查（每周期；发现即 Incident）

```text
Signal↔Decision · Decision↔Risk · Decision↔Intent · Intent↔MT5 · MT5↔Fill · Fill↔Position
Position↔Close · Close↔PnL · MT5↔Ledger · Ledger↔Replay
```

## 5. 安全与解耦（Truth System 不得成为风险源）

- Truth 写失败：**记录 UNKNOWN + 安全状态**（`WAIT_TRUTH:RECORD_FAILED`：不进新仓）；**不得伪造 PASS**。
- Truth 层不得：改变 signal、绕过 RiskGuard、导致重复下单、修改历史证据。
- forensic 查询**只读**。

## 6. 取证问答模板（回答“当时究竟看到了什么/为什么/做了什么/结果/哪层出问题”）

1. `--trade <trade_id>`：十段链 + raw broker + derived 一致性 → 因果链。
2. `--incident <incident_id>`：类型/首末次/严重度/根因/受影响 ID/原始证据/状态。
3. `--cycle <cycle_id>`：该周期全部事件（signal/risk/order/broker/ledger）。
4. `--date <YYYY-MM-DD>`：当日 FACTS_ONLY 报告 + incident 索引。

## 7. 历史兼容

- Truth 启用前的交易：账本证据原样保留；缺 `cycle_id/decision_id` ⇒ 用时间相邻补齐并**标注 link_method=time_adjacency(legacy)**；其余全部如实 `UNKNOWN`。
- 新系统从启用时刻起完整记录（snapshot 从第一个新周期开始）。
