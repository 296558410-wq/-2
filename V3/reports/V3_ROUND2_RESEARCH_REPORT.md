# V3 第二轮研究报告（Round 2）

`ts_utc = 2026-09-25T01:00:42.276099+00:00` · **`final_status = V3_STRATEGY_RESEARCH_ROUND2_COMPLETE`**
`V3_FORWARD_READY = False` · `V3_STRATEGY_FORWARD = NOT_ENABLED` · `V3_LIVE_ALLOWED = NO`

---

## 1. 第一轮基线（永久保留，未修改）

```text
H01–H12 = FROZEN      registry_hash = 1650e065911e72c93f85cf26d51cdb179f252b089eb4a2c86ad8be2c7682c52d
CANDIDATE = 0 · EDGE_UNCERTAIN = 0 · REJECT = 9 · INSUFFICIENT_SAMPLE = 3
报告 : reports/V3_STRATEGY_SIGNAL_RESEARCH_REPORT.md      Git : 7d2f485
本轮未修改任何 H01–H12 条目（文件级核对：hypotheses.json 未被写入）
```

## 2. Risk Layer（§6–§13）

```text
位置 : strategy/risk.py（独立模块；不在 signals.py / v3_adapter.py / calibration_pilot.py 内）
职责 : 只回答"该 Signal 在当前执行环境下是否允许进入下一阶段"——不预测方向
输入 : Signal Contract + market_state + execution_state + account_state + risk_state
输出 : ALLOW / NO_TRADE / BLOCK        （绝无 LONG/SHORT）
检查 : signal_validity · data_freshness · symbol_check · account_check · execution_mode_check ·
       spread_check · cost_check · position_check · exposure_check · duplicate_check ·
       cooldown_check · stale_signal_check（+ live_gate_check / forward_gate_check 两个闸门附加项）
边界 : [PASS] no_broker_call · [PASS] no_broker_import_in_risk_module
确定性: [PASS] determinism_replay: 146455076ac9 == 146455076ac9   方向未改写: [PASS] direction_unchanged: LONG/SHORT
单元测试（§37）：=== RISK_TEST_COUNT=16 PASS=16 FAIL=0 | extra_checks=4/4 ===
红线段（§38）全部 BLOCK：future_timestamp / wrong_account / wrong_symbol / live_mode /
       invalid_signal / duplicate_intent / stale_data(+forward_enabled)
未绕过 Execution Guard（§39）：risk.py 无任何 broker 调用；ALLOW 仍需经 v3_adapter 守卫
```

## 3. PIT 数据（§14–§19、§34）

```text
登记表 : research/v3_pit_macro_registry/pit_macro_registry.json
强制字段: source/instrument/observation_time/publication_time/retrieval_time/timezone/value/revision/availability/hash
结论   : NO_PIT_SAFE_MACRO_SOURCE_AVAILABLE   admitted_count = 0
```

| instrument | 候选源 | PIT_STATUS | publication_time | 说明 |
|---|---|---|---|---|
| DXY | ALFRED/FRED DXY series; stooq DX.F | NOT_PIT_SAFE | NO | no PIT-provable source reachable without credentials; publication_time cannot be |
| UST2Y | ALFRED/FRED DGS2 (real-time vintages); treasury.gov daily | NOT_PIT_SAFE | NO | no PIT-provable source reachable without credentials; publication_time cannot be |
| UST10Y | ALFRED/FRED DGS10 (real-time vintages); treasury.gov daily | NOT_PIT_SAFE | NO | no PIT-provable source reachable without credentials; publication_time cannot be |
| REAL_YIELD_PROXY | ALFRED DFII10; derived | NOT_PIT_SAFE | NO | no PIT-provable source reachable without credentials; publication_time cannot be |
| VIX | stooq VI.F; yahoo ^VIX | NOT_PIT_SAFE | NO | no PIT-provable source reachable without credentials; publication_time cannot be |
| TIP | stooq TIP.US; yahoo TIP | NOT_PIT_SAFE | NO | no PIT-provable source reachable without credentials; publication_time cannot be |
| GLD | stooq GLD.US; yahoo GLD | NOT_PIT_SAFE | NO | no PIT-provable source reachable without credentials; publication_time cannot be |
| GC | stooq GC.F; yahoo GC=F | NOT_PIT_SAFE | NO | no PIT-provable source reachable without credentials; publication_time cannot be |

有界探测（§19 不做无限抓取）：

| 源 | 可达 | HTTP | 错误 | PIT 评估 |
|---|---|---|---|---|
| fred_alfred_api | False | None | HTTPError: HTTP Error 400: Bad Request | POTENTIAL (ALFRED real-time vintages expose realtime_start/end) — requ |
| fred_alfred_realtime | False | None | HTTPError: HTTP Error 400: Bad Request | POTENTIAL (ALFRED real-time vintages expose realtime_start/end) — requ |
| treasury_csv | True | 200 | - | PARTIAL (daily release, but only publication DATE; intraday availabili |
| stooq_daily | True | 200 | - | NO (end-of-day OHLCV snapshot; no publication_time; history is restate |
| yahoo_chart | True | 200 | - | NO (end-of-day OHLCV snapshot; no publication_time; history is restate |

```text
关键判定：stooq / yahoo / treasury 虽"可达"，但
  - stooq / yahoo : EOD OHLCV 快照，无 publication_time，历史可被复述  => NOT PIT-SAFE
  - treasury CSV  : 只有发布日期，无法证明盘中何时可得             => NOT PIT-SAFE（用于盘中 Signal）
  - FRED/ALFRED   : 具备 realtime vintages（理论可 PIT），但需要 API key，本环境无 => 不可用
=> 按 §15/§36：不得进入 Signal。H10 与全部跨市场/宏观/新闻假设 = NOT_TESTABLE（保持原状，未强行补测）
```

## 4. 第二轮 Registry（H13+，冻结）

```text
文件 : research/v3_strategy_registry/hypotheses_round2.json
registry_hash = 5f135bfe60a2c0c0f53ce785046af2759eec69a75f92d6fb21b908910688ecef
条数 = 11    冻结于任何评估之前 = True
每条含 : mechanism / parent_hypothesis / novelty_reason（§22 要求）
```

| ID | 方向桶 | 假设 | parent | 结果 |
|---|---|---|---|---|
| H13_EXEC_REGIME_GATED_BREAKOUT | F_LIQUIDITY_EXECUTION_REGIME | a range breakout only continues when the execution environment is  | - | REJECT |
| H14_LIQUIDITY_VACUUM_REVERSAL | F_LIQUIDITY_EXECUTION_REGIME | after a tick-rate collapse (z < -2) the next bar reverts | - | REJECT |
| H15_VOL_TRANSITION_EXPANSION | D_VOLATILITY_STATE_TRANSITION | a low-vol -> expansion transition continues in the expansion direc | - | INSUFFICIENT_SAMPLE |
| H16_VOL_TRANSITION_CONTRACTION | D_VOLATILITY_STATE_TRANSITION | after a volatility climax the market quiets and mean-reverts for 8 | - | REJECT |
| H17_SESSION_HANDOFF_CONTINUATION | A_SESSION_STRUCTURE | the London leg continues for 6 bars after the 13:00 UTC handoff | - | INSUFFICIENT_SAMPLE |
| H18_ASIA_RANGE_FAKEBREAK | A_SESSION_STRUCTURE | an Asia-range extreme broken during London and reclaimed fades for | - | REJECT |
| H19_COST_GATED_MOMENTUM | F_LIQUIDITY_EXECUTION_REGIME | short-horizon momentum is only net-positive when realised spread i | - | REJECT |
| H20_CTRL_RANGE_BREAKOUT_RETEST | CONTROL_DUPLICATE | (CONTROL) a close beyond the prior 20-bar high continues 10 bars | H02_5M_RANGE_BREAKOUT | REJECT_DUPLICATE_HYPOTHESIS |
| H21_CROSS_ASSET_DIVERGENCE | C_CROSS_MARKET_DIVERGENCE | a Gold/DXY/UST10Y/VIX state combination precedes a repeatable gold | - | NOT_TESTABLE |
| H22_MACRO_REPRICING_WINDOW | B_MACRO_REPRICING | after a macro release the repricing window is tradable for 6 bars | - | NOT_TESTABLE |
| H23_NEWS_NARRATIVE_SHIFT | B_MACRO_REPRICING | a narrative shift (LLM-classified) precedes a repeatable gold move | - | NOT_TESTABLE |

## 5. Novelty（§22 去重证明）

```text
去重门实现：以 (mechanism, hold_bars, range_window, side) 与 H01–H12 比对
结果：
{
 "H13_EXEC_REGIME_GATED_BREAKOUT": {
  "dup": false,
  "versus": null,
  "action": "ADMIT"
 },
 "H14_LIQUIDITY_VACUUM_REVERSAL": {
  "dup": false,
  "versus": null,
  "action": "ADMIT"
 },
 "H15_VOL_TRANSITION_EXPANSION": {
  "dup": false,
  "versus": null,
  "action": "ADMIT"
 },
 "H16_VOL_TRANSITION_CONTRACTION": {
  "dup": false,
  "versus": null,
  "action": "ADMIT"
 },
 "H17_SESSION_HANDOFF_CONTINUATION": {
  "dup": false,
  "versus": null,
  "action": "ADMIT"
 },
 "H18_ASIA_RANGE_FAKEBREAK": {
  "dup": false,
  "versus": null,
  "action": "ADMIT"
 },
 "H19_COST_GATED_MOMENTUM": {
  "dup": false,
  "versus": null,
  "action": "ADMIT"
 },
 "H20_CTRL_RANGE_BREAKOUT_RETEST": {
  "dup": true,
  "versus": "H02_5M_RANGE_BREAKOUT",
  "action": "REJECT_DUPLICATE_HYPOTHESIS",
  "why": "explicit control; mechanism+params identical to H02_5M_RANGE_BREAKOUT"
 },
 "H21_CROSS_ASSET_DIVERGENCE": {
  "dup": false,
  "versus": null,
  "action": "ADMIT"
 },
 "H22_MACRO_REPRICING_WINDOW": {
  "dup": false,
  "versus": null,
  "action": "ADMIT"
 },
 "H23_NEWS_NARRATIVE_SHIFT": {
  "dup": false,
  "versus": null,
  "action": "ADMIT"
 }
}
=> 7 条新机制 ADMIT；1 条【刻意控制项】H20 被判 REJECT_DUPLICATE_HYPOTHESIS（证明去重门真的工作）；
   3 条跨市场/宏观/新闻 = NOT_TESTABLE（数据缺口，非重复）
未发生"H13 ≈ H02 重复跑一遍"的情况。
```

## 6. 实验结果（完整统计）

bars = 18342（2026-09-07 01:05:00+00:00 → 2026-09-24 23:54:00+00:00）
覆盖局限：18 days only: cannot fully cover the §35 regime matrix (low/high vol, trend/range, event-heavy/light)

| ID | signals | eff n | gross bp/笔 | 0x | 1x | 2x | 3x | walk-forward | regime(vol) | 判定 |
|---|---|---|---|---|---|---|---|---|---|---|
| H13_EXEC_REGIME_GATED_BREAKOUT | 1049 | 519 | 0.056 | 0.056 | -0.858 | -1.772 | -2.686 | {"fold1": -0.644, "fold2": -0.303, "fold3": -1.698} | {"low": -1.234, "mid": 0.389, "high": -1.702} | REJECT |
| H14_LIQUIDITY_VACUUM_REVERSAL | 801 | 398 | -0.1 | -0.1 | -1.014 | -1.928 | -2.842 | {"fold1": -0.775, "fold2": -1.097, "fold3": -1.25} | {"low": -0.811, "mid": -1.455, "high": -0.782} | REJECT |
| H15_VOL_TRANSITION_EXPANSION | 0 | - | - | - | - | - | - | "-" | "-" | INSUFFICIENT_SAMPLE |
| H16_VOL_TRANSITION_CONTRACTION | 1363 | 444 | -0.282 | -0.282 | -1.196 | -2.11 | -3.024 | {"fold1": -1.178, "fold2": -1.738, "fold3": -0.678} | {"low": -0.112, "mid": -2.045, "high": -1.426} | REJECT |
| H17_SESSION_HANDOFF_CONTINUATION | 14 | 14 | -1.676 | -1.676 | -2.59 | -3.504 | -4.418 | {"fold1": -4.515, "fold2": -0.784, "fold3": -2.109} | {"low": -4.266, "mid": -5.495, "high": 1.411} | INSUFFICIENT_SAMPLE |
| H18_ASIA_RANGE_FAKEBREAK | 62 | 32 | -1.342 | -1.342 | -2.256 | -3.17 | -4.084 | {"fold1": -2.324, "fold2": -2.53, "fold3": -1.895} | {"low": -4.19, "mid": -0.536, "high": -1.959} | REJECT |
| H19_COST_GATED_MOMENTUM | 18302 | 3064 | -0.077 | -0.077 | -0.991 | -1.905 | -2.819 | {"fold1": -1.023, "fold2": -0.921, "fold3": -1.017} | {"low": -0.879, "mid": -0.855, "high": -1.235} | REJECT |
| H20_CTRL_RANGE_BREAKOUT_RETEST | 0 | - | - | - | - | - | - | "-" | "-" | REJECT_DUPLICATE_HYPOTHESIS |
| H21_CROSS_ASSET_DIVERGENCE | 0 | - | - | - | - | - | - | "-" | "-" | NOT_TESTABLE |
| H22_MACRO_REPRICING_WINDOW | 0 | - | - | - | - | - | - | "-" | "-" | NOT_TESTABLE |
| H23_NEWS_NARRATIVE_SHIFT | 0 | - | - | - | - | - | - | "-" | "-" | NOT_TESTABLE |

## 7. Cost Stress（§26）

```text
锚 : 0.914 bp 往返（沿用第一轮）
实测校准成本核对：round_trips=19 ·
  realised fee USD mean/min/max = 0.22/0.22/0.22
  cost_stable = True  => 未观察到 cost regime shift
压力档 : 0x / 1x / 2x / 3x 全部记录于上表
```

## 8. OOS（§27）

```text
方法 : time-ordered walk-forward（3 折 0–40% / 40–70% / 70–100%），无 shuffle
结果 : 见 §6 的 walk-forward 列；所有假设均未通过"三折全部非负"
```

## 9. Regime（§29）

```text
已做 : volatility tercile（low/mid/high）· session（Asia/London/NY/rollover，见评估 JSON）
未做 : DXY regime / yield regime / macro-event regime —— 因无 PIT 数据，无法分层（§29：样本足够才拆分）
```

## 10. FDR（§30）

```text
第二轮 : 测试 11 个 · 走到 FDR 阶段 0 个 ·
         BH(q=0.05) 阳性 0 个
累计   : 第一轮 12 + 第二轮 11 = 23（统一计入，未分 Tier 各报一次）
```

## 11. Candidate

```text
CANDIDATE = 0   []
门槛（§31）：1x 成本后为正 ∧ 2x 不灾难坍塌 ∧ OOS 支持 ∧ regime 不依赖单一区间 ∧ effective_n 足够 ∧
             无 lookahead ∧ 无 same-bar ∧ 机制可解释 ∧ 反证未击穿 —— 全部同时满足才算 Candidate
结果分布 : {"CANDIDATE": 0, "EDGE_UNCERTAIN": 0, "REJECT": 5, "INSUFFICIENT_SAMPLE": 2, "NOT_TESTABLE": 3, "REJECT_DUPLICATE_HYPOTHESIS": 1}
```

## 12. Shadow（§40/§41）

```text
状态 : N/A (no candidate) · ORDER_SEND = 0
未创建空账本（§40 明确：CANDIDATE=0 时 SHADOW = N/A）
```

## 13. Forward Preflight（§42）

```text
registry_hash  = 5f135bfe60a2c0c0f53ce785046af275…
strategy_hash  = 066cbb0985de55c23556dce38aad3ece…
risk_hash      = 29a0a94aa9cbe1c00745293cad014bd4…
execution_hash = b207ce1903d1ca6b900000602d0ebc40…
account = 160766418 · magic = 90004 · symbol = XAUUSD
V3_LIVE_ALLOWED = NO
V3_FORWARD_READY = False
V3_STRATEGY_FORWARD = NOT_ENABLED   （§43：绝不自动升级到 Forward）
```

## 14. 数据缺口（明确记录）

```text
NOT_TESTABLE（无 PIT-safe 源，§15/§34/§36）
  H21_CROSS_ASSET_DIVERGENCE   : 需 PIT DXY/UST10Y/VIX
  H22_MACRO_REPRICING_WINDOW   : 需带 publication_time 的宏观发布
  H23_NEWS_NARRATIVE_SHIFT     : 需 PIT 新闻（publication_timestamp）
  H10_DXY_CONFIRMED_REVERSAL   : 保持第一轮 NOT_TESTABLE（§34；未强行补测）

INSUFFICIENT_SAMPLE（有效样本不足，未降门槛）
  H15_VOL_TRANSITION_EXPANSION, H17_SESSION_HANDOFF_CONTINUATION

覆盖缺口（§35）
  现有 PIT 数据仅 18 天（live_fxtm），无法完整覆盖 low/high vol · trend/range · event-heavy/light 矩阵。
  按 §36（质量 > 长度）与 §51（不勉强），未使用 DUKA（不同交易所）或不可审计的预计算特征来"凑长度"。
```

## 最终状态（§49）

```text
V3_STRATEGY_RESEARCH_ROUND2_COMPLETE
V3_FORWARD_READY     = False
V3_STRATEGY_FORWARD  = NOT_ENABLED
V3_LIVE_ALLOWED      = NO
```

## §50 成功标准自查

```text
Risk Layer 完整            : YES（独立模块 + 16 用例 + 4 附加检查全绿）
PIT 数据可信               : 结论为"无可信 PIT 宏源"，缺口已如实登记（admitted=0）
H13+ 假设冻结              : YES（registry_hash=5f135bfe60a2c0c0…）
第一轮假设未被污染          : YES（hypotheses.json 未写入）
第二轮没有重复挖掘          : YES（去重门生效；控制项被拒）
成本压力 / OOS / Regime / FDR : 全部完成
所有失败真实记录           : YES（REJECT 5 · INSUFFICIENT 2 · NOT_TESTABLE 3 · DUPLICATE 1）
Candidate 不存在则明确为 0  : YES
Forward 不自动开启          : YES（V3_STRATEGY_FORWARD=NOT_ENABLED）
Execution / Calibration / V1 / V2 不被修改 : YES
Git 干净可追溯              : 见提交
```

## 结论（§51）

> 第二轮的目标不是把 0 Candidate 变成 1，而是判断在更完整的机制与数据空间里是否真的存在 Candidate。
> 本轮答案仍然是 **CANDIDATE = 0**，并且**数据侧的根本约束已经被明确指出**：缺少 PIT 可信的宏观/跨市场价格与发布时刻，
> 因此"跨市场确认 / 宏观重定价 / 事件反应 / 新闻叙事"这四类最有希望的新机制在本环境下**无法被严格检验**。
> 我们**接受 0**，未调参救策略、未降低门槛、未为交易而交易。
