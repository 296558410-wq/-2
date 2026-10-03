# V1-R2 Market Reading Architecture R1

## 1. Executive Summary
- DEFINE → FREEZE → RUN 已执行；ontology_hash `8436866dfe71030b`，registry_hash `752bf2273f6a509d`（冻结于运行之前）。
- 资产盘点：共 45 项 → KEEP 25 / REWORK 13 / REJECT 0 / UNVERIFIED 7。
- Ledger 条目 140（140 个决策点，严格 PIT）；tests 27/27 PASS。

## 2. Architecture (L1..L5)
- L1 PERCEPTION（K线/序列/多周期）→ L2 READING（结构生命周期、承接/拒绝、防御强度）→ L3 MECHANISM（竞争假设 + support/counter/invalidation）→ L4 STATE（STATE_VECTOR + transition + forecast）→ L5 STRATEGY ADAPTER（**仅接口**）。

## 3. Frozen Principles
- 市场决定交易方法；K线是语言不是信号；预测必须携带证据/反证/失效条件；交易是最后一层。

## 4. Existing Asset Inventory
- 见 `audit/EXISTING_CAPABILITY_INVENTORY.json`（45 项，含 F-* 与 Phase B-R1..B-R13）。

## 5. Classification
- KEEP 25 / REWORK 13 / REJECT 0 / UNVERIFIED 7。无资产被删除。

## 6. Candle / Japanese Candlestick
- 16 个几何事件 + 12 个序列事件；几何与上下文标签分离（几何=HAMMER_GEOMETRY，上下文=HAMMER_CONTEXT）。**只产生 CANDLE_EVENT**。

## 7. Price Structure
- 生命周期 11 态；触碰分类 6 类；PENETRATION 仅作观察（B-R11 结论沿用）。LEVEL/TOUCH/BREAK 归入同一 PRICE_STRUCTURE 信息轴（B-R7/B-R8）。

## 8. Behaviour / Mechanism
- 机制 10 个，每个含 support/counter/invalidation；竞争输出 DOMINANT/SECONDARY/UNCERTAIN，**不伪造概率**。

## 9. State / Transition / Forecast
- STATE_VECTOR 9 轴；UNKNOWN 被拆分为 6 类，不再单一黑洞；forecast 预测 NEXT_MARKET_STATE 而非 BUY/SELL。

## 10. Multi-Timeframe
- H4 90 / H1 335 / M15 1328 / M5 3945；高周期与低周期可并存冲突。

## 11. Ledger
- `ledger/v1_r2_market_reading_ledger.jsonl`（140 条），含 context_hash / state_vector / hypotheses / forecast / invalidation / data_quality / registry_hash；OBSERVED_OUTCOME 仅在预测固定后单独写入。

## 12. Audit
- see `audit/R1_AUDIT.json`（architecture/ontology/registry/input hash，lookahead/replay/deterministic 状态）。

## 13. Tests
- 27/27 PASS（见 `tests/TEST_RESULTS.json`）。

## 14. Limitations
- K线/机制/状态/预测层均为 R1 **定义 + 首次落地**，尚未做预测验证；按 §64 不追求漂亮结果。
- M5 由 tick 重建；H1/H4 由 M15 重采样（已在 ontology 记录）。
- ABSORPTION / LIQUIDITY 仍为 PROXY，未升级（§22）。

## 15. Acceptance (§65)
- A 资产未丢失 ✔ / B 全部分类 ✔ / C K线进入 Perception ✔ / D Price Structure 进入 Reading ✔ / E 承接·吸收·衰竭·破位·流动性进入 Behavior·Mechanism ✔ / F 证据·反证·失效为一等公民 ✔ / G 状态与策略解耦 ✔ / H Forecast ≠ BUY/SELL ✔ / I 可表达连续叙事 ✔（见 narratives）/ J PIT·Replay·Deterministic·Audit ✔。

## 16. Safety
- ORDER_SEND=0 / ORDER_CHECK=0 / BROKER_WRITE=0；FORWARD/SHADOW/LIVE=OFF；V1 execution/risk/order logic 未修改；GIT_COMMIT=NONE。
