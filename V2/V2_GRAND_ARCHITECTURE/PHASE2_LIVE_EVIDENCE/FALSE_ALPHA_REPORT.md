# FALSE_ALPHA_REPORT

> 假 Alpha 防火墙（spec §16）：只单窗口成立→`FRAGILE`；只单 regime→`REGIME_CONDITIONAL`；FDR 不通过→`NOT_VALIDATED`。

| strategy_id | mechanism | looks_positive | exp | n_eff | fdr_pass | single_regime | verdict |
|---|---|---|---|---|---|---|---|
| SF-TREND-00 | TREND | False | -0.6126361031523926 | 698 | False | False | **NOT_SIGNIFICANT** |
| SF-TREND-01 | TREND | False | -0.6126361031523926 | 698 | False | False | **NOT_SIGNIFICANT** |
| SF-MOMENTUM-00 | MOMENTUM | False | -0.40356521739184653 | 805 | False | False | **NOT_SIGNIFICANT** |
| SF-MOMENTUM-01 | MOMENTUM | False | -0.3499471598420296 | 757 | False | False | **NOT_SIGNIFICANT** |
| SF-REVERSAL-00 | REVERSAL | False | -0.3581567796615395 | 236 | False | False | **NOT_SIGNIFICANT** |
| SF-REVERSAL-01 | REVERSAL | False | -0.6062310606065879 | 264 | False | False | **NOT_SIGNIFICANT** |
| SF-RANGE-00 | RANGE | False | 0.4483333333328119 | 3 | False | True | **NOT_SIGNIFICANT** |
| SF-RANGE-01 | RANGE | False | 2.4499999999989086 | 1 | False | True | **NOT_SIGNIFICANT** |
| SF-BREAKOUT-00 | BREAKOUT | False | nan | 0 | False | False | **NOT_SIGNIFICANT** |
| SF-BREAKOUT-01 | BREAKOUT | False | nan | 0 | False | False | **NOT_SIGNIFICANT** |
| SF-VOL_EXPANSION-00 | VOL_EXPANSION | False | nan | 0 | False | False | **NOT_SIGNIFICANT** |
| SF-VOL_EXPANSION-01 | VOL_EXPANSION | False | nan | 0 | False | False | **NOT_SIGNIFICANT** |
| SF-VOL_CONTRACTION-00 | VOL_CONTRACTION | False | -2.0614705882360473 | 17 | False | False | **NOT_SIGNIFICANT** |
| SF-MTF_STRUCTURE-00 | MTF_STRUCTURE | False | -0.18741869918754098 | 738 | False | False | **NOT_SIGNIFICANT** |
| SF-EVENT-00 | EVENT | False | -1.5290972222228068 | 72 | False | False | **NOT_SIGNIFICANT** |
| SF-MACRO-00 | MACRO | True | 0.23788008565256966 | 467 | False | False | **NOT_VALIDATED** |
| SF-HYBRID-00 | HYBRID | False | -0.44671641791099237 | 670 | False | True | **NOT_SIGNIFICANT** |

## 方法

- 检查项：multiple testing (BH-FDR)、sample size、regime concentration、time concentration、
  cost sensitivity、placebo/shuffled control、unseen OOS。
- 结论按最严格口径给出；任何'好看'结果先经受上述检查再谈。
