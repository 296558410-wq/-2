# OOS_REPORT

Untouched OOS = ('2026-09-24', '2026-10-01')，在 discovery 选择与 validation 之前未参与任何选择。

## 工厂候选 OOS
| strategy_id | oos_n | oos_expectancy | oos_precision | oos_total |
|---|---|---|---|---|
| SF-TREND-00 | 605 | 0.5675 | 0.5124 | 343.3300 |
| SF-TREND-01 | 605 | 0.5675 | 0.5124 | 343.3300 |
| SF-MOMENTUM-00 | 652 | 0.0296 | 0.5046 | 19.3100 |
| SF-MOMENTUM-01 | 878 | -0.2083 | 0.4841 | -182.9200 |
| SF-REVERSAL-00 | 562 | 0.1153 | 0.4840 | 64.8050 |
| SF-REVERSAL-01 | 586 | -0.1269 | 0.4846 | -74.3700 |
| SF-RANGE-00 | 8 | 0.4700 | 0.6250 | 3.7600 |
| SF-RANGE-01 | 3 | 1.1967 | 0.6667 | 3.5900 |
| SF-BREAKOUT-00 | 0 | nan | nan | nan |
| SF-BREAKOUT-01 | 0 | nan | nan | nan |
| SF-VOL_EXPANSION-00 | 0 | nan | nan | nan |
| SF-VOL_EXPANSION-01 | 0 | nan | nan | nan |
| SF-VOL_CONTRACTION-00 | 38 | -0.3237 | 0.5000 | -12.3000 |
| SF-MTF_STRUCTURE-00 | 909 | -0.0069 | 0.4840 | -6.2350 |
| SF-EVENT-00 | 190 | 0.0836 | 0.5211 | 15.8750 |
| SF-MACRO-00 | 162 | -0.1667 | 0.5000 | -27.0100 |
| SF-HYBRID-00 | 355 | 0.3432 | 0.5211 | 121.8300 |

## 简单基准 OOS（Section 十）
| baseline | n | expectancy | total |
|---|---|---|---|
| V1_M15_vs_MA20 | 67 | -0.6236 | -41.7800 |
| SIMPLE_MOMENTUM | 75 | -3.3312 | -249.8400 |
| SIMPLE_MEANREV | 23 | -3.3730 | -77.5800 |
| SIMPLE_BREAKOUT | 0 | nan | nan |
| V2_REFERENCE_PROXY | 59 | 1.3913 | 82.0850 |
| RANDOM_CONTROL | 147 | 3.3174 | 487.6550 |

## GPU 搜索 top 组合 OOS（前 15）
| fast | slow | thr | sign | val_exp | oos_n | oos_exp |
|---|---|---|---|---|---|---|
| 35 | 60 | 0.003 | 1 | nan | 0 | nan |
| 7 | 20 | 0.003 | 1 | nan | 9 | 0.7254 |
| 9 | 15 | 0.002 | 1 | nan | 2 | -0.4525 |
| 37 | 60 | 0.003 | 1 | nan | 0 | nan |
| 33 | 55 | 0.003 | 1 | nan | 0 | nan |
| 39 | 55 | 0.002 | 1 | nan | 0 | nan |
| 21 | 40 | 0.003 | -1 | nan | 0 | nan |
| 39 | 65 | 0.003 | 1 | nan | 0 | nan |
| 7 | 10 | 0.001 | 1 | -2.1101 | 42 | 0.2581 |
| 3 | 15 | 0.003 | 1 | -2.9069 | 50 | -2.9063 |
| 5 | 20 | 0.003 | 1 | -4.2509 | 26 | -2.3656 |
| 17 | 35 | 0.003 | -1 | nan | 0 | nan |
| 37 | 65 | 0.003 | 1 | nan | 0 | nan |
| 19 | 40 | 0.003 | -1 | nan | 0 | nan |
| 5 | 15 | 0.003 | 1 | nan | 12 | 0.6908 |