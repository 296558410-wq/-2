# V1 逐笔亏损归因与策略错误法证报告
## V1_LOSS_FORENSICS_REPORT

- **任务**：对新版 V1（`research/hermes/trader_v1/v1_upgrade`）**全部已有交易**逐笔做 Loss Forensics。
- **窗口**：首笔开仓 `2026-09-28T15:35:14Z` → 末笔平仓 `2026-10-02T02:05:01Z`。
- **样本**：**32 笔**（全部已平） = 12 胜 / 20 负。
- **口径**：PnL 价差口径（ledger）净额 **−11.44**；含佣金/掉期净额 **−17.86**。
- **输入指纹**：ledger `ed7accbf28a118a0da9ba19f4019c1cf2f75ed55b645f1e09bcbc39e51db84d2`；M1 归档快照 `4471efda47446c8da5b54bf6cce1ebc48039ca1838bec8cdb7a407f5bd709242`。
- **硬边界遵守**：只读；`order_send = 0`；`order_check = 0`；未改策略/信号/参数/RiskGuard/历史账本/MT5 成交/V2/V3。原始事实与派生分析分离（见 §0.3）。

> **证据等级**：`FACT`（原始记录直读）/ `DIRECT CAUSAL EVIDENCE`（反事实可判定）/ `INFERENCE`（显式推断）/ `UNKNOWN`（证据不足）。
> **禁止**：把“亏损”等同于“策略错误”；不做策略好坏排名或人为打分。

---

## 0. 方法与机器状态

### 0.1 逐笔决策现场重建（PIT）
每笔从账本取 **DECISION → ORDER_CHECK → ORDER_REQUEST → ORDER_SEND → FILL → POSITION → CLOSE → PNL**；
结构特征只用 **决策时刻前已收盘** 的 1m/5m/15m/30m/60m K 线（`close_ms ≤ decision_ts`）+ 决策前 tick；
结果特征只用 **开仓之后** 的 tick。PIT / lookahead audit = **PASS**（`PIT_AUDIT.json`，32/32 行 `ok=true`）。

### 0.2 Hermes 输入 / 输出（本 run 是冻结控制臂）
- **输入** `live_state`：`state=EXPANSION`、`family=DIRECTIONAL`、`trend_20`、`atr`、`ma20`、`last_bar_utc`（label_adapter），快照 `bid/ask/mid/spread_bps`。
- **输出**：`action=ENTER` + `order_intent{side,lots=0.01,sl,tp,atr,m15_trend20,mapping_id=v1up-baseline-transition-order-map-v1}`。
- **信号层**：`signal_type=BASELINE_CONTROL`、`not_hermes_alpha=true`（机械映射，无 LLM 推理层）。⇒ 本样本中 `SIGNAL_REASONING_ERROR` **不适用**（无可证伪的推理链）。
- 32 笔 `action` 全为 `ENTER`，`signal` 全为 `family=DIRECTIONAL`，决策时 `risk_reasons=[]`（守卫彼时未接线）。

### 0.3 原始事实 vs 派生分析
- **原始事实**：`entry/exit/pnl_price/commission/swap/net/R`、`decision`、`execution`、`guard_cf`（重建态）、`pit`。
- **派生分析（不回改事实）**：`structure`（PIT 特征）、`path`（MFE/MAE/路径）、`cf`（反事实）。
- 逐笔记录：`TRADE_ERROR_DATABASE.jsonl`（32 行）。

### 0.4 仪器修正（先查仪器，再下结论）
归档 tick 的 `ts_utc` **标签为服务器帧（UTC+3）**（与引擎快照 328/390 精确 +3h 对齐、并按逐笔 fill/exit 锚点核验）。分析统一 **−3h** 换算为真实 UTC；**原始档未改**（`m1_bars_snapshot.parquet` 保留服务器帧原样 + 记录哈希）。
账本历史 `PNL` 事件只含价差分量（无 cost 字段）⇒ 净额口径另从券商 deal（`profit+commission+swap`）计算；两口径都报，不作混比。

---

## A. 每一笔到底为什么亏

### A.1 20 笔亏损逐笔（市场状态 → Hermes 判断 → 实际路径 → MAE/MFE → 主因 → 证据）

| # | trade_id | session | 方向 | 入场(UTC) | 60m 状态 (dir_vs_MA20 / 趋势强度ATR) | 决策输出 | 持仓 | MFE_R | MAE_R | 出场 | R | 净额 | 应拦 | PRIMARY_ROOT_CAUSE | 证据等级 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `V1T-2377720619` | NY | SHORT | 09-28 15:35 | −1 / 4.05 | ENTER DIRECTIONAL | 49.5m | 0.534 | 0.99 | SL | −1.000 | −13.26 | 否 | `TIMING_ERROR` | 直接因果证据 |
| 2 | `V1T-2377901575` | NY | LONG | 09-29 14:18 | +1 / 1.61 | ENTER DIRECTIONAL | 61.2m | 1.081 | 0.987 | SL | −1.000 | −7.64 | 否 | `TIMING_ERROR` | 直接因果证据 |
| 3 | `V1T-2377943078` | NY | SHORT | 09-29 17:18 | +1 / 0.39 | ENTER DIRECTIONAL | 42.5m | 0.399 | 0.94 | SL | −1.026 | −9.66 | 否 | `DIRECTION_ERROR` | 事实+推断 |
| 4 | `V1T-2378032044` | LONDON | LONG | 09-30 07:03 | +1 / 1.62 | ENTER DIRECTIONAL | 129.4m | 0.953 | 0.997 | SL | −1.011 | −7.58 | 否 | `TIMING_ERROR` | 直接因果证据 |
| 5 | `V1T-2378052329` | LONDON | LONG | 09-30 09:18 | +1 / 1.41 | ENTER DIRECTIONAL | 93.5m | 0.240 | 0.996 | SL | −1.006 | −7.17 | 否 | `NO_IDENTIFIABLE_ERROR` | 事实 |
| 6 | `V1T-2378067697` | LONDON | SHORT | 09-30 11:18 | +1 / 0.72 | ENTER DIRECTIONAL | 8.2m | 0.352 | 0.993 | SL | −1.003 | −6.16 | 否 | `DIRECTION_ERROR` | 事实+推断 |
| 7 | `V1T-2378071359` | LONDON | SHORT | 09-30 11:33 | +1 / 0.72 | ENTER DIRECTIONAL | 4.0m | 0.023 | 0.994 | SL | −1.003 | −6.62 | **是** | `RISK_ERROR` | 直接因果证据 |
| 8 | `V1T-2378074134` | LONDON | SHORT | 09-30 11:48 | +1 / 0.72 | ENTER DIRECTIONAL | 22.2m | 0.119 | 0.948 | SL | −1.022 | −6.82 | **是** | `RISK_ERROR` | 直接因果证据 |
| 9 | `V1T-2378095101` | NY | LONG | 09-30 13:03 | +1 / 2.00 | ENTER DIRECTIONAL | 7.9m | 0.029 | 0.993 | SL | −1.025 | −8.08 | **是** | `RISK_ERROR` | 直接因果证据 |
| 10 | `V1T-2378098886` | NY | LONG | 09-30 13:18 | +1 / 2.00 | ENTER DIRECTIONAL | 14.5m | 0.132 | 0.991 | SL | −1.013 | −8.90 | **是** | `RISK_ERROR` | 直接因果证据 |
| 11 | `V1T-2378224663` | ASIA | LONG | 10-01 05:33 | +1 / 0.96 | ENTER DIRECTIONAL | 67.8m | 0.939 | 0.948 | SL | −1.021 | −5.92 | 否 | `TIMING_ERROR` | 直接因果证据 |
| 12 | `V1T-2378253584` | LONDON | SHORT | 10-01 08:33 | −1 / 0.25 | ENTER DIRECTIONAL | 51.2m | 0.648 | 0.996 | SL | −1.000 | −8.52 | 否 | `TIMING_ERROR` | 直接因果证据 |
| 13 | `V1T-2378264395` | LONDON | SHORT | 10-01 09:33 | −1 / 0.87 | ENTER DIRECTIONAL | 59.4m | 1.342 | 0.985 | SL | −1.000 | −8.31 | 否 | `TIMING_ERROR` | 直接因果证据 |
| 14 | `V1T-2378322488` | NY | SHORT | 10-01 14:33 | +1 / 0.03 | ENTER DIRECTIONAL | 6.2m | 0.156 | 0.991 | SL | −1.017 | −9.51 | 否 | `DIRECTION_ERROR` | 事实+推断 |
| 15 | `V1T-2378333628` | NY | SHORT | 10-01 15:03 | −1 / 0.13 | ENTER DIRECTIONAL | 17.0m | 0.659 | 0.991 | SL | −1.001 | −8.78 | 否 | `TIMING_ERROR` | 直接因果证据 |
| 16 | `V1T-2378343004` | NY | SHORT | 10-01 15:33 | −1 / 0.13 | ENTER DIRECTIONAL | 5.4m | 0.471 | 0.996 | SL | −1.025 | −11.01 | 否 | `REGIME_ERROR` | 事实+推断 |
| 17 | `V1T-2378348994` | NY | SHORT | 10-01 15:48 | −1 / 0.13 | ENTER DIRECTIONAL | 101.9m | 0.657 | 0.928 | SL | −1.047 | −11.81 | **是** | `RISK_ERROR` | 直接因果证据 |
| 18 | `V1T-2378382127` | NY | LONG | 10-01 18:48 | +1 / 0.20 | ENTER DIRECTIONAL | 333.5m | 0.496 | 0.983 | SL | −1.007 | −11.77 | **是** | `RISK_ERROR` | 直接因果证据 |
| 19 | `V1T-2378409328` | ASIA | SHORT | 10-02 01:18 | −1 / 1.02 | ENTER DIRECTIONAL | 20.8m | 0.132 | 0.977 | SL | −1.001 | −7.66 | 否 | `NO_IDENTIFIABLE_ERROR` | 事实 |
| 20 | `V1T-2378413449` | ASIA | SHORT | 10-02 01:48 | −1 / 1.02 | ENTER DIRECTIONAL | 17.0m | 0.460 | 0.993 | SL | −1.009 | −7.21 | 否 | `NO_IDENTIFIABLE_ERROR` | 事实 |

**逐类判据（先定义后应用，未事后修改）**
- `RISK_ERROR`（6）：按声明语义重建，**决策时刻已达 `MAX_CONSECUTIVE_LOSS(=3)` 或 `MAX_DAILY_LOSS(=≤−20)` ⇒ 本应拒单**，而当时守卫未接线 ⇒ 放行（`FACT` 账本 + `DIRECT CAUSAL EVIDENCE` 反事实）。对应第 7/8/9/10/17/18 笔。
- `TIMING_ERROR`（7）：方向未被证明错，但 **MFE ≥ 0.5R 后全数回吐至 SL**（进场/离场时机问题；`mfe_r≥0.5` 为 `FACT`，归类为 `INFERENCE`）。
- `DIRECTION_ERROR`（3）：入场方向与当时 **60m MA20 趋势相反**，且路径几乎未朝持仓方向展开（MFE < 0.5R）。
- `REGIME_ERROR`（1）：60m 趋势强度弱（`trend_strength_atr < 0.3`）且路径未展开——趋势信号在不成立的市况里被使用。
- `NO_IDENTIFIABLE_ERROR`（3）：无任何可识别错误特征（＝普通市场损失）。

**共性事实（全部 20 笔）**：`retcode=10009`；`|滑点| ≤ 3.39bps`（限 15）；SL/TP 全部随单；出场 **全部由券商按声明规则触发**（亏损 20/20 = `[sl …]`）；`realized_R ∈ [−1.047, −1.000]`。⇒ `EXECUTION_ERROR = 0`、`EXIT_ERROR = 0`。

### A.2 12 笔盈利（对照，不做排名）
`V1T-2377732264` `V1T-2377758482` `V1T-2377762527` `V1T-2377948868` `V1T-2377968902` `V1T-2378103348` `V1T-2378121712` `V1T-2378137348` `V1T-2378208028`* `V1T-2378214531` `V1T-2378246193` `V1T-2378281587`
出场全为 `[tp …]`（`V1T-2378208028` 的 tick 路径缺失，见 §9 / `DATA_GAPS_AND_UNKNOWN.md`，但其出场为 TP、R=+1.609 为 `FACT`）。
其中 `V1T-2378103348`、`V1T-2378121712` **也在“守卫本应拦下”集合内**（应拦未拦同样放过了 2 笔盈利）。

---

## B. 亏损是否存在重复模式（仅统计，不做评分/排名）

亏损 20 笔，按任务要求的维度：

| 维度 | 计数 | 明细 |
|---|---|---|
| **direction** | 3 | `DIRECTION_ERROR`（均入场逆 60m MA20 且 MFE<0.5R） |
| **timing** | 7 | `TIMING_ERROR`（MFE≥0.5R 后回吐至 SL） |
| **regime** | 1 | `REGIME_ERROR`（60m 趋势强度 <0.3ATR） |
| **signal reasoning** | 0 | 本 run 为冻结控制臂（`not_hermes_alpha=true`），无推理层可证伪 |
| **exit** | 0 | 20/20 券商 SL 按 1R 声明规则触发，无提前/延后离场 |
| **execution** | 0 | retcode 全 10009；滑点 ≤3.39bps；SL/TP 随单 |
| **risk** | 6 | `RISK_ERROR`（守卫应拦未拦） |
| **data** | 0（对交易因果） | 交易期决策用实时终端数据；归档帧问题只影响本研究分析 |

**附加切片（事实）**：方向 13 空 / 7 多；时段 NY 10 / LONDON 7 / ASIA 3；按日 09-28:1、09-29:2、09-30:7、10-01:8、10-02:2。

**重复模式判定（只陈述证据强度）**
- `TIMING_ERROR` 是最大亏损桶（7/20），即“**浮盈≥0.5R 后回吐**”这一描述性模式在样本内可重复观察到（`FACT` 级 MFE）。
- 但它**不构成已验证的可修复机制**：反事实（§C / `COUNTERFACTUAL_ANALYSIS.md`）显示延迟进场 **15m：0/20 转 TP**、**30m：0/20 转 TP**；固定 15m 时间止损均值仅 **−0.34R（5/20 为正）**。⇒ 样本内 **无一致证据** 表明“改时机”能系统性改善。
- `RISK_ERROR` 的重复性来自**单一接线缺陷**（非市场模式）：同一缺陷在整个窗口对所有 32 笔结构性失效。

---

## C. 哪些错误可以修复

| 类别 | 笔数 | 可修复性 | 证据 |
|---|---|---|---|
| `RISK_ERROR` | 6 | **`CONFIRMED_FIXABLE`** | `guard_cf.block=True`（价差/净额**两口径一致**）；此前审计判定 `RISK_VIOLATION`，修复已部署+验收（commit `63d5a22` / `eceeec2`；dry-run 当场 `WAIT_RISK:MAX_DAILY_LOSS,MAX_CONSECUTIVE_LOSS`；现网决策已出现同款 `WAIT_RISK`）。**属风控治理缺陷，非 alpha 缺陷。** |
| `TIMING_ERROR` | 7 | `POTENTIALLY_FIXABLE` | 描述性 MFE 模式存在，但反事实不支持系统性改善（延迟进场 0/20 转 TP）⇒ 证据不足以支撑改动 |
| `DIRECTION_ERROR` | 3 | `POTENTIALLY_FIXABLE` | n=3，样本不足 |
| `REGIME_ERROR` | 1 | `POTENTIALLY_FIXABLE` | n=1，样本不足 |
| `NO_IDENTIFIABLE_ERROR` | 3 | `NOT_FIXABLE_FROM_CURRENT_DATA` | 无可识别错误特征 |
| `UNKNOWN`（盈利笔路径缺失） | 1* | `UNKNOWN` | tick 归档缺口（见 §9） |

> *该 `UNKNOWN` 为盈利笔 `V1T-2378208028` 的**路径特征**缺失，不影响其 R/出场（`FACT`）。

**结构性 vs 因果性（两个数都要报）**：守卫接线缺陷对本窗口 **32/32 笔结构性失效**（决策时 `risk_reasons` 全空）；但**因果责任 = 8/32**（本应拦下：6 笔亏损 + 2 笔盈利）。可预防的亏损 = **6 笔**（对应价差合计 **−52.15**）。

---

## D. 是否值得进入下一轮策略优化

**结论：以当前证据 —— 不值得，不应强行提出新规则。**

依据：
1. **无“重复且可独立验证”的错误机制**存在于信号/执行层：本 run 是冻结控制臂（`not_hermes_alpha=true`），无推理层；执行/数据/出场失败均为 0；`TIMING_ERROR` 虽为最大桶，但其可修复性被反事实**否定**（无一致改善）。
2. **样本不足**：`DIRECTION_ERROR` n=3、`REGIME_ERROR` n=1、`NO_IDENTIFIABLE_ERROR` n=3——不足以形成统计上可辩护的新假设。
3. **唯一的系统性缺陷（守卫未接线）已判定并已修复**，且它回答的是“**该不该被执行**”的风控问题，而非“信号是否有 alpha”。
4. 因此，按任务书要求：**不为了“优化”强行提出新规则**；不推导任何参数调整。

**（可选，非本轮动作）** 若后续要谈优化，唯一“先决条件”是：在**信号层接上可证伪的推理/预测**并积累足够样本后，再按同一 PIT 协议重跑本流程——这属于未来触发条件，不是本轮建议。

---

## 9. UNKNOWN 与数据缺口（摘要，详见 `DATA_GAPS_AND_UNKNOWN.md`）

- `V1T-2378208028`（盈利，入场 10-01 03:03Z）：tick 归档缺口 `02:39:06Z→04:00:27Z`（81.3min）覆盖其窗口 ⇒ `mfe_r/mae_r/时间点` 记为 **UNKNOWN**（只影响盈利笔路径，不影响任何亏损归类）。
- 决策期 `data_age` 未记录（守卫彼时被喂固定 0）⇒ 当时“真实数据新鲜度”为 **UNKNOWN**。
- 账本历史 `PNL` 无 cost 字段 ⇒ 净额口径须用券商 deal 另算（口径缺口，非错误）。

---

## 验收自检（对照任务书）

| 验收项 | 结果 | 依据 |
|---|---|---|
| 全部已有交易逐笔覆盖 | **PASS 32/32** | `VERIFY.json`：ledger↔券商 magic 90011↔DB 三向差集均为空 |
| 每笔唯一 `trade_id` | PASS | `V1T-<position_id>`，32 个唯一 |
| 决策数据与未来路径严格分离 | PASS | `PIT_AUDIT.json` verdict=PASS |
| PIT / lookahead audit | PASS | 32/32 行 `ok=true` |
| 原始事实与派生分析分离 | PASS | §0.3 |
| UNKNOWN 不被强行填充 | PASS | §9（1 笔路径 UNKNOWN 照实记） |
| 数据源/时间范围/hash 可追溯 | PASS | §10 + `SHA256SUMS.txt` |
| 结果可独立复现 | PASS | 重跑 `v1_loss_build.py`+`v1_loss_render.py` 逐笔一致；`v1_loss_verify.py`=PASS |
| V1/V2/V3 隔离 | PASS | `VERIFY.json`：只读 V1 路径 + 券商 magic 90011；未触 V2/V3 |
| `order_send = 0` | PASS | 本包脚本 `order_send/order_check` 调用 = **0**（`VERIFY.json` 静态扫描） |
| Git commit + SHA256 | PASS | §10 + `SHA256SUMS.txt` |

---

## 10. 证据与指纹

- **输入指纹**：ledger `ed7accbf28a118a0da9ba19f4019c1cf2f75ed55b645f1e09bcbc39e51db84d2`；M1 快照 `4471efda47446c8da5b54bf6cce1ebc48039ca1838bec8cdb7a407f5bd709242`。
- **事件 ID**：每笔决策 `V1E-<sha12>`（见 `TRADE_ERROR_DATABASE.jsonl` 的 `decision.event_id`）；交易 ID `V1T-<position_id>`。
- **守卫重建口径**：`gates.realized_close_utc` 日界 + 引擎帧；价差/净额两口径判决**一致**。
- **产物**：`TRADE_ERROR_DATABASE.jsonl`、`TRADE_ERROR_SUMMARY.csv`、`COUNTERFACTUAL_ANALYSIS.md`、`ROOT_CAUSE_MATRIX.md`、`DATA_GAPS_AND_UNKNOWN.md`、`PIT_AUDIT.json`、`V1_LOSS_MACHINE.json`、`VERIFY.json`、`SHA256SUMS.txt`、脚本 `v1_loss_build/render/stats/verify.py`。
- **Git commit**：`ec396124846b8def793a9ff1d5fc3ea6c4c6fa93`（产物 path-limited 提交；本报告回填该 commit 号后二次提交记录）。

**本任务只负责找原因，不修改策略。完成后停止，不自动进入策略优化、不改参数、不重新交易。**
