# V1-R7 TARGET & FEATURE INFORMATION DIAGNOSTIC — FINAL REPORT

只读、离线、无 Hermes 调用、无策略、无交易。目标：判断 R6 失败是**目标问题**还是**特征信息量问题**。

## 样本
开发期 (ts < 2026-06-01) n=33114 · 盲测期 n=7306 · 水平 H=8 bar (15m)

## 各目标判定（对照随机水平与多数基线）
| target | PRICE_ONLY balanced_acc | chance | majority_acc | 判定 |
|---|---|---|---|---|
| STATE | 0.2014 | 0.1111 | 0.2472 | INFORMATION_WEAK |
| TRANSITION | 0.5 | 0.5 | 0.657 | INFORMATION_ABSENT |
| DIRECTION | 0.3933 | 0.3333 | 0.457 | INFORMATION_WEAK |
| SCENARIO | 0.5207 | 0.3333 | 0.3893 | INFORMATION_PRESENT |
| TIMING | 0.25 | 0.25 | 0.4645 | TARGET_PROBLEM |

类别分布（开发期）：{"STATE": {"DECELERATION": 603, "REJECTION": 8269, "ACCEPTANCE": 1084, "NO_DEFINED_STATE": 1311, "EXPANSION": 5965, "BREAKOUT_ATTEMPT": 1590, "COMPRESSION": 6675, "TREND": 3958, "ROTATION": 3659}, "TRANSITION": {"1.0": 21448, "0.0": 11666}, "DIRECTION": {"NEUTRAL": 5064, "DOWN": 14846, "UP": 13204}, "SCENARIO": {"RANGE": 12531, "QUIET": 9070, "DIRECTIONAL": 11513}, "TIMING": {"<=2": 9730, "3-8": 15382, "9-24": 7502, ">24": 500}}

## 特征组增量（相对 PRICE_ONLY 的 Δbalanced_acc）
- STATE_HISTORY: {"STATE": 0.0064, "TRANSITION": 0.0009, "DIRECTION": 0.0027, "SCENARIO": 0.0174, "TIMING": 0.0001}
- EVENT_HISTORY: {"STATE": 0.0016, "TRANSITION": 0.0139, "DIRECTION": -0.0025, "SCENARIO": 0.0015, "TIMING": 0.0051}
- MTF: {"STATE": 0.0085, "TRANSITION": 0.0, "DIRECTION": 0.007, "SCENARIO": 0.0187, "TIMING": 0.0005}
- VOLATILITY: {"STATE": 0.0008, "TRANSITION": 0.0011, "DIRECTION": -0.0003, "SCENARIO": 0.0003, "TIMING": 0.0}
- CROSS_MARKET: {"STATE": null, "TRANSITION": null, "DIRECTION": null, "SCENARIO": null, "TIMING": null}

## 消融（ALL vs 去一组）
{"STATE": {"minus_PRICE": {"balanced_acc": 0.1777, "delta_vs_ALL": -0.0392}, "minus_STATE_HISTORY": {"balanced_acc": 0.2127, "delta_vs_ALL": -0.0042}, "minus_EVENT_HISTORY": {"balanced_acc": 0.2165, "delta_vs_ALL": -0.0004}, "minus_MTF": {"balanced_acc": 0.2096, "delta_vs_ALL": -0.0073}, "minus_VOLATILITY": {"balanced_acc": 0.2171, "delta_vs_ALL": 0.0002}, "minus_CROSS_MARKET": {"balanced_acc": 0.2169, "delta_vs_ALL": 0.0}, "minus_MACRO": {"balanced_acc": 0.2169, "delta_vs_ALL": 0.0}}, "TRANSITION": {"minus_PRICE": {"balanced_acc": 0.5486, "delta_vs_ALL": 0.0017}, "minus_STATE_HISTORY": {"balanced_acc": 0.5221, "delta_vs_ALL": -0.0248}, "minus_EVENT_HISTORY": {"balanced_acc": 0.5083, "delta_vs_ALL": -0.0386}, "minus_MTF": {"balanced_acc": 0.5438, "delta_vs_ALL": -0.0031}, "minus_VOLATILITY": {"balanced_acc": 0.545, "delta_vs_ALL": -0.0019}, "minus_CROSS_MARKET": {"balanced_acc": 0.5469, "delta_vs_ALL": 0.0}, "minus_MACRO": {"balanced_acc": 0.5469, "delta_vs_ALL": 0.0}}, "DIRECTION": {"minus_PRICE": {"balanced_acc": 0.3822, "delta_vs_ALL": -0.0192}, "minus_STATE_HISTORY": {"balanced_acc": 0.4004, "delta_vs_ALL": -0.001}, "minus_EVENT_HISTORY": {"balanced_acc": 0.4011, "delta_vs_ALL": -0.0003}, "minus_MTF": {"balanced_acc": 0.3926, "delta_vs_ALL": -0.0088}, "minus_VOLATILITY": {"balanced_acc": 0.4018, "delta_vs_ALL": 0.0004}, "minus_CROSS_MARKET": {"balanced_acc": 0.4014, "delta_vs_ALL": 0.0}, "minus_MACRO": {"balanced_acc": 0.4014, "delta_vs_ALL": 0.0}}, "SCENARIO": {"minus_PRICE": {"balanced_acc": 0.4771, "delta_vs_ALL": -0.0734}, "minus_STATE_HISTORY": {"balanced_acc": 0.5408, "delta_vs_ALL": -0.0097}, "minus_EVENT_HISTORY": {"balanced_acc": 0.5527, "delta_vs_ALL": 0.0022}, "minus_MTF": {"balanced_acc": 0.5381, "delta_vs_ALL": -0.0124}, "minus_VOLATILITY": {"balanced_acc": 0.5528, "delta_vs_ALL": 0.0023}, "minus_CROSS_MARKET": {"balanced_acc": 0.5505, "delta_vs_ALL": 0.0}, "minus_MACRO": {"balanced_acc": 0.5505, "delta_vs_ALL": 0.0}}, "TIMING": {"minus_PRICE": {"balanced_acc": 0.2624, "delta_vs_ALL": 0.0001}, "minus_STATE_HISTORY": {"balanced_acc": 0.2599, "delta_vs_ALL": -0.0024}, "minus_EVENT_HISTORY": {"balanced_acc": 0.2499, "delta_vs_ALL": -0.0124}, "minus_MTF": {"balanced_acc": 0.2634, "delta_vs_ALL": 0.0011}, "minus_VOLATILITY": {"balanced_acc": 0.26, "delta_vs_ALL": -0.0023}, "minus_CROSS_MARKET": {"balanced_acc": 0.2623, "delta_vs_ALL": 0.0}, "minus_MACRO": {"balanced_acc": 0.2623, "delta_vs_ALL": 0.0}}}
ALL_MODEL：{"STATE": {"balanced_acc": 0.2169, "macro_f1": 0.1938, "n_te": 7306}, "TRANSITION": {"balanced_acc": 0.5469, "macro_f1": 0.5177, "n_te": 7306}, "DIRECTION": {"balanced_acc": 0.4014, "macro_f1": 0.3632, "n_te": 7306}, "SCENARIO": {"balanced_acc": 0.5505, "macro_f1": 0.5531, "n_te": 7306}, "TIMING": {"balanced_acc": 0.2623, "macro_f1": 0.2007, "n_te": 7306}}
被剔除（开发期无覆盖）：{"STATE": ["xs_DXY", "xs_DXY_d12", "xs_TNX", "xs_TNX_d12", "xs_VIX", "xs_VIX_d12"], "TRANSITION": ["xs_DXY", "xs_DXY_d12", "xs_TNX", "xs_TNX_d12", "xs_VIX", "xs_VIX_d12"], "DIRECTION": ["xs_DXY", "xs_DXY_d12", "xs_TNX", "xs_TNX_d12", "xs_VIX", "xs_VIX_d12"], "SCENARIO": ["xs_DXY", "xs_DXY_d12", "xs_TNX", "xs_TNX_d12", "xs_VIX", "xs_VIX_d12"], "TIMING": ["xs_DXY", "xs_DXY_d12", "xs_TNX", "xs_TNX_d12", "xs_VIX", "xs_VIX_d12"]}

## 六个专项问题
1. 为何 State 输给 persistence：{"majority_share_dev": 0.2497, "state_entropy_bits": 2.79, "persistence_acc": 0.343, "previous_state_acc": 0.3144, "PRICE_ONLY_balanced_acc": 0.2014, "note": "the state label is sticky (high persistence) AND the classes are imbalanced; a 9-class model with weak signal loses to copying the current state"}
2. 为何 Transition 低于 0.5：{"PRICE_ONLY_balanced_acc": 0.5, "majority_share_dev": 0.6477, "note": "transition base rate and near-random balanced accuracy indicate little H=8 timing information in the current features"}
3. 为何 Scenario 高于 State：{"scenario_classes": 3, "state_classes": 9, "scenario_entropy_bits": 1.5722, "state_entropy_bits": 2.79, "scenario_PRICE_ONLY": {"balanced_acc": 0.5207, "macro_f1": 0.5199, "n_te": 7306}, "state_PRICE_ONLY": {"balanced_acc": 0.2014, "macro_f1": 0.1629, "n_te": 7306}, "note": "collapsing 9 states into 3 families removes most of the uncertainty, so coverage is high while exact STATE is not"}
4. 跨市场是否有增量：{"STATE": {"available": false, "note": "group empty or insufficient data"}, "TRANSITION": {"available": false, "note": "group empty or insufficient data"}, "DIRECTION": {"available": false, "note": "group empty or insufficient data"}, "SCENARIO": {"available": false, "note": "group empty or insufficient data"}, "TIMING": {"available": false, "note": "group empty or insufficient data"}} → CROSS_MARKET increment could not be estimated: the cross-market series only cover ~63 days (from 2026-07-17), so the development window has no cross-market observations -> DATA_LIMITATION, not evidence of no value.
5. MTF 增量：{"STATE": {"balanced_acc": 0.2099, "macro_f1": 0.1784, "delta_balanced_acc": 0.0085, "delta_macro_f1": 0.0155, "available": true}, "TRANSITION": {"balanced_acc": 0.5, "macro_f1": 0.3965, "delta_balanced_acc": 0.0, "delta_macro_f1": 0.0, "available": true}, "DIRECTION": {"balanced_acc": 0.4003, "macro_f1": 0.3622, "delta_balanced_acc": 0.007, "delta_macro_f1": 0.007, "available": true}, "SCENARIO": {"balanced_acc": 0.5394, "macro_f1": 0.5395, "delta_balanced_acc": 0.0187, "delta_macro_f1": 0.0196, "available": true}, "TIMING": {"balanced_acc": 0.2505, "macro_f1": 0.1598, "delta_balanced_acc": 0.0005, "delta_macro_f1": 0.0012, "available": true}}
6. 方向不平衡影响：{"direction_distribution_dev": {"NEUTRAL": 5064, "DOWN": 14846, "UP": 13204}, "majority_share_dev": 0.4483, "majority_baseline_acc": 0.457, "PRICE_ONLY_balanced_acc": 0.3933, "note": "majority share is high; raw accuracy is dominated by the NEUTRAL class, balanced accuracy is the honest metric"}

## PIT 审计
{"features_used": ["dwell", "ev_0", "ev_1", "evchg_1", "evchg_2", "evchg_4", "evchg_8", "f_acc", "f_act3", "f_atr_pctl", "f_eff3", "f_er10", "f_rng_exp", "f_slope5", "f_vel4", "mtf_0", "mtf_1", "mtf_2", "mtf_3", "mtf_4", "mtf_5", "nod8", "st_0", "st_1", "st_2", "vol_20", "vol_5", "volr", "xs_DXY", "xs_DXY_d12", "xs_TNX", "xs_TNX_d12", "xs_VIX", "xs_VIX_d12"], "forbidden_used": [], "shift_direction": "all lags use .shift(+k) (past only) and cross-market uses reindex(method='ffill') as-of t", "available_at_t": true, "status": "PASS"}

## 结论
MAIN_BOTTLENECK = **MIXED**
分类：{"STATE": "INFORMATION_WEAK", "TRANSITION": "INFORMATION_ABSENT", "DIRECTION": "INFORMATION_WEAK", "SCENARIO": "INFORMATION_PRESENT", "TIMING": "TARGET_PROBLEM"}
MACRO_DATA = 不可得（MACRO_EVENTS / CFTC_COT / GLD / GC / ETF_FLOWS 均 UNKNOWN → DATA_LIMITATION）
未生成 profit_score / win_probability / expected_profit。
R3/R4/R5/R5.1/R6 不可变性：{"R3": "PASS", "R4": "PASS", "R5": "PASS", "R5_1": "PASS", "R6": "PASS"}
tests = 12/0
