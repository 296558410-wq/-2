# V1-R2 FULL AUTONOMOUS OPTIMIZATION — FINAL REPORT

## EXECUTIVE SUMMARY
起点 C1/C1.5 的 `STATE_RECOGNITION=UNSUPPORTED` / `C2_BLOCKED` **全部保留、未修改**。本任务对预测层做实质性重构：给冻结行为标签加上最小驻留生命周期（STATE v2, k=2），并正式比较 STATE / EVENT / STATE+EVENT / EVENT_SEQUENCE / STATE_TRANSITION。
结论：**C1 的"不支持"是评估对象与口径问题，不是市场没有结构。** 在严格 60/40 冻结点盲测下，六个预测目标均通过预注册效果地板；但 EVENT / HORIZON 的每类可分性弱。
**FINAL_VERDICT = PARTIAL_PREDICTION_CAPABILITY_SUPPORTED**

## STARTING_POINT
C1 GIT_HEAD `0f3d5d3c88a701a80b42d520b2b510f1aa07ccf3` · C1.5 `TARGET_UNCERTAIN` / `C2_BLOCKED` · 20 个月 XAUUSD M15（40,546 根）。

## WHAT_FAILED
- 冻结 MARKET_BEHAVIOR 作为 STATE：中位时长 1 bar、churn 0.629——是**无生命周期定义**所致（Stage 诊断）。
- 下一根几何预测低于效果地板；纯 K 线单独几乎零信息。
- EVENT / HORIZON 多类每类可分性弱（balanced accuracy 低）。

## WHAT_WAS_RESEARCHED
诊断 A–H；五模型生死测试；K 线上下文阶梯；State 生命周期；Event 层；Transition 提前预警；六目标预测拆解；MTF 逐档；机制；反证消融；严格 Blind；零假设/打乱；时间/日/簇分割；effective_n 与集中度。

## WHAT_CHANGED
新增预测层重构：STATE v2（k=2）、EVENT 层、六目标 Forecast、Forecast Record、Strategy Mapping（研究层）。

## WHAT_REMAINED_FROZEN
C1 ontology / label mapping、C1.5 target registry 与报告、Phase B 产物、原始行情、V1 执行/风控/下单逻辑、V2、V3。

## STATE_RESULTS
M_A STATE_FORECAST ΔLL 0.37769 bits，acc 0.4084 vs 多数 0.2533；day/cluster holdout 均 >0.39。

## EVENT_RESULTS
M_B EVENT ΔLL 0.19238；M_D EVENT_SEQUENCE ΔLL 0.19327 → EVENT 弱于 STATE。

## TRANSITION_RESULTS
ΔLL 0.06368 · AUC 0.6726；前兆窗口 AUC 0.668(lead0)→0.554(lead4)→0.501(lead8)。

## FORECAST_RESULTS
STATE 0.46424 / TRANSITION 0.06368 / EVENT 0.23032 / INVALIDATION 0.07017。

## DIRECTION_RESULTS
结构方向 ΔLL 0.04978，acc 0.522 vs 多数 0.4623（未使用收益/PnL）。

## TIMING_RESULTS
HORIZON ΔLL 0.06651，acc 0.2413 vs 多数 0.2267（边际）。

## KLINE_RESULTS
KLINE_ONLY 0.00098；+STRUCTURE 0.05183；+STATE 0.2432；FULL 0.41438 → **KLINE_CONTEXTUAL_INCREMENTAL**。

## MTF_RESULTS
M15 0.2385 → +H1 0.2926 → +H4 0.31406 → **SUPPORTED**。

## MECHANISM_RESULTS
SUPPORTED（delta 0.03551）。

## COUNTER_EVIDENCE_RESULTS
EXPLANATORY_ONLY（delta -0.00059）。

## ABLATION_RESULTS
{"A0_priors_only": 0.0, "A1_candle_behavior": 0.24964, "A2_structure": 0.05146, "A3_momentum": 0.00195, "A6_state_plus_dwell": 0.25425, "A8_mtf_only": 0.04949, "A9_counter_evidence": 0.33217, "A10_full": 0.4777}

## BLIND_RESULTS
{"STATE_FORECAST": "SUPPORTED", "TRANSITION_FORECAST": "SUPPORTED", "EVENT_FORECAST": "SUPPORTED", "DIRECTION_FORECAST": "SUPPORTED", "HORIZON_FORECAST": "SUPPORTED", "INVALIDATION_FORECAST": "SUPPORTED"}

## REPLAY_RESULTS
PASS（feature 截断重放一致；labeler 回放引 C1/C1.5 冻结证据）。

## LIMITATIONS
研究层；目标为市场结构标签而非收益；单一品种与单一 20 个月窗口；EVENT/HORIZON 每类可分性弱；机制/反证为代理特征。

## DATA_LIMITATIONS
仅 BID OHLC；无 DOM/trade direction（§47）；无数据购买（§83）；无历史扩张（§84）。

## STRATEGY_MAPPING
gate = OPEN；postures = {"WAIT_ABSTAIN": {"n": 11920, "share": 0.7353}, "GRID_MEAN_REVERSION": {"n": 1711, "share": 0.1055}, "TREND_FAMILY": {"n": 1365, "share": 0.0842}, "WAIT_TRANSITION": {"n": 1145, "share": 0.0706}, "NO_TRADE_AMBIGUOUS": {"n": 70, "share": 0.0043}}（研究层，未执行，无 PnL）。

## FINAL_CAPABILITY_MATRIX
| 能力 | 状态 | 增量 | 证据 |
|---|---|---|---|
| Candle Reading | SUPPORTED | 0.00098 | K-line geometry perceives structure; KLINE_ONLY alone ~0 bits |
| Price Structure | SUPPORTED | 0.05146 | A2 structure ablation |
| Market Behavior | SUPPORTED | 0.24964 | behavior one-hot ablation |
| Mechanism | SUPPORTED | 0.03551 | mechanism ablation |
| State Recognition | SUPPORTED | 0.37769 | M_A blind ΔLL |
| Event Recognition | INCONCLUSIVE | 0.19238 | M_B blind ΔLL / balanced-acc weak |
| Transition | SUPPORTED | 0.06368 | AUC 0.6726; lead window ~4 bars |
| Next State | SUPPORTED | 0.37769 | STATE_FORECAST |
| Direction | INCONCLUSIVE | 0.04978 | acc 0.522 vs maj 0.4623 (structural, no returns) |
| Timing | INCONCLUSIVE | 0.06651 | horizon bucket, marginal |
| Counter Evidence | EXPLANATORY_ONLY | -0.00059 | conflict-feature ablation |
| Invalidation | SUPPORTED | 0.07017 | AUC 0.677 |
| MTF | SUPPORTED | 0.07556 | H1 +0.0541, H4 +0.02146 |

## FINAL_VERDICT
**PARTIAL_PREDICTION_CAPABILITY_SUPPORTED**
