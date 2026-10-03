# V3 阶段2 · PIT 数据补充 R1 — 解放 D / 重评 E 族

- 任务：`V3-PHASE2-PIT-DATA-SUPPLEMENT-001`
- 口径：`pit-data-source-audit`（**只读取数**；不购买、不注册、不试用；不申请/不使用/不打印/不存储任何 key；`order_send=0`；`ALPHA_SEARCH=OFF`）
- 边界：`V3_EXECUTION_MODE=RESEARCH_READONLY` · `ORDER_SEND=NO` · `FORWARD=NO` · V1/V2 零交互
- 收口：`V3_PIT_PARTIAL`

---

## 1. 冻结（取数之前）

`PIT_FIELD_DICTIONARY.json`，sha256 = `1b33f28b7f4e81b85a02ede4772ef2ea2318c4716ed7a585a25b90f7b35c7c51`（在任何一次取数**之前**写盘）

字段：`observation_time` / `publication_time` / `availability_time` / `revision_time·vintage_time`
状态枚举：`PASS` / `CONDITIONAL` / `FAIL` / `NOT_AVAILABLE` / `AUTH_REQUIRED`
终态枚举：`V3_PIT_READY` / `V3_PIT_PARTIAL` / `V3_PIT_SOURCE_UNAVAILABLE`

## 2. 源审计表（每候选只探测一次）

| 源 | 层 | http | payload_verified | 复现 | 状态 | 理由 |
|---|---|---|---|---|---|---|
| YAHOO_DXY_1H_2Y | T3 | **403** | false | — | `NOT_AVAILABLE`（本次） | 本机间歇性 403；**回退到已存产物**（不得写成"覆盖不足"） |
| YAHOO_VIX_1H_2Y | T3 | **403** | false | — | 同上 | 同上 |
| YAHOO_DXY_5M_60D | T3 | **403** | false | — | 同上 | 同上 |
| YAHOO_VIX_5M_60D | T3 | **403** | false | — | 同上 | 同上 |
| JIN10_MCP_list_calendar | T2 | 200 | true | 窗口已滚动 | `CONDITIONAL` | 见 §3：**滚动约一周窗口，历史不可回溯** |
| US_TREASURY_YIELD_CURVE | T1 | local | true | hash 一致 | `CONDITIONAL` | 官方口径，仅日粒度；本地文件哈希校验通过 |

**状态计数**：`PASS=0` · `CONDITIONAL=2` · `NOT_AVAILABLE=4` · `FAIL=0` · `AUTH_REQUIRED=0`
（`PASS=0` 是合法结论：没有任何一个源能同时证明"历史观测 + 该观测的历史可得性/版本"。）

## 3. 本轮最重要发现：Jin10 日历是**滚动窗口**，历史不可回溯

| vintage | 抓取时刻(UTC) | 覆盖(北京时间) | 事件数 | raw_hash |
|---|---|---|---|---|
| `V3_JIN10_EVENT_PIT.json`（9/25 存量） | 2026-09-25T09:05Z | 2026-09-21 → 09-26 | 158 | `0c9c6cea…` |
| `JIN10_CALENDAR_20261001T130733Z.json`（本次） | 2026-10-01T13:07Z | 2026-09-28 → 10-03 | 283 | `c28e56dd…` |

两个 vintage **完全不重叠** ⇒ 日历只能"当时抓到才算数"。这既是 D 族的**唯一数据来源**，也是一条运维约束：
**必须按计划持续抓取**，否则窗口永久丢失（不可补）。

> 附带口径瑕疵（如实记录）：本次 vintage 的 `importance` 字段为空（字段名与存量 vintage 不同），
> 故其 223 条窗口内事件**无法按星级分层**；存量 vintage 的星级分层完好（1★45 / 2★78 / 3★30 / 4★3）。

## 4. 新快照（copy-on-cut，不可变）

`V3-SNAP-PIT2-20261001T131500Z` — 9 文件 / **1,712,560 ticks** / `2026-09-21T01:08Z → 2026-10-01T12:54Z`
逐文件 sha256 + 只读属性 + `MANIFEST.json`（含 `LIVE_SOURCE_MUTABLE=TRUE` / `RESEARCH_SNAPSHOT_IMMUTABLE=TRUE`）。
日历 2 个 vintage 一并入册（带各自 hash）。

**tick × calendar 重叠**
- 存量 vintage（09-21..09-26）：窗口内 **156** 事件，落在 09-21..09-25 共 5 个交易日
- 本次 vintage（09-28..10-03）：窗口内 **223** 事件，落在 09-28..10-01 共 4 个交易日

## 5. 保守可用性规则（冻结）

```
daily_market_bar_dated_D      -> D+1T00:00:00Z
official_daily_value_dated_D  -> D+1T00:00:00Z
calendar_event_with_pub_time  -> 其自身 pub_time_utc（不早放、不加滞后）
calendar_revision_value       -> vintage 抓取时刻（revision_time 不可证 ⇒ 取保守值）
unfinished_bar                -> FORBIDDEN
tick_market_data              -> 其自身时间戳
```

## 6. 重放接口 + 5 项防泄漏测试

`get_information_available_at(T)` 只返回 `availability_time ≤ T` 的观测，并输出 `withheld_future` 与 `registry_hash`。

```
=== PIT_LEAKAGE_TEST_COUNT=5 PASS=5 FAIL=0 ===
T1_future_publication_invisible        PASS  (violations=0, withheld=197)
T2_future_revision_invisible           PASS  (revision rows visible at T = 0)
T3_replay_deterministic                PASS  (逐字节一致)
T4_hash_integrity                      PASS  (篡改可检出; 文件哈希 0 mismatch)
T5_timezone_normalized_preserving_orig PASS  (UTC 归一 + 保留原 tz)
```
`registry_hash = 9166703176ec377c0a430112…`，observations = **505**

## 7. 能力 vs 假设对齐（粒度匹配才允许测试）

| 族 | 前 | 后 | 粒度 | 依据 / 说明 |
|---|---|---|---|---|
| A 微观结构 | TESTABLE | **TESTABLE** | tick | 不变 |
| C 流动性·价差 | TESTABLE | **TESTABLE** | tick | 不变 |
| F 非方向 | TESTABLE | **TESTABLE** | tick | 不变 |
| **D 事件微观结构** | **NOT_TESTABLE** | **✅ TESTABLE** | event-time + tick | 阻断原因本是**日历窗口与冻结快照零重叠**；新快照覆盖 09-21..10-01，与**两个 vintage** 都有重叠 ⇒ 解封。**但窗口很薄**（合计 9 个交易日、且分属两个不重叠 vintage）⇒ `INSUFFICIENT_SAMPLE` 是**很可能**的阶梯落点，届时如实报，不硬凑 |
| **E 跨市场 Lead-Lag** | LIMITED | **TESTABLE_AT_1H（部分）** | 1h bar（2y 重叠 624 天） | 用已存 Yahoo 1h/2y 产物；**本轮实时重取 403**；bar 开/收语义仍 `UNKNOWN`；5m 仅 ~63 天 |
| **B 执行 Alpha** | NOT_TESTABLE | **仍 NOT_TESTABLE** | — | **不是日历/跨市场能解决的问题**：`bid_vol/ask_vol` 恒为 0（DATA_GAP）⇒ 无 size-weighted microprice/队列/成交概率。需要 **L2/order-book** 数据（另一条可得性支线）。本轮**不解封 B，也不假装解封** |

**规则核对**：未改写任何假设定义；能力升级只催生**新 id + 重新预注册**的假设。

## 8. 终态

```
V3_PIT_PARTIAL
- D：解封（薄窗口）→ 可进 D-R1 事件微观结构研究
- E：1h 部分可用（语义 UNKNOWN ⇒ 结论需标注 CONDITIONAL）
- B：不变（结构性数据缺口，非日历问题）
- 两轴分开：reachability 与 capability —— Jin10 主机**可达**但**历史能力受限**（滚动窗口）；
  Yahoo 主机本轮**不可达(403)** 但**已存产物可用**。不写成"源不可达"
```
