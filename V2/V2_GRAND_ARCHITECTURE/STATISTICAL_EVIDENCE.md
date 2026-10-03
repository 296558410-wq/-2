# STATISTICAL_EVIDENCE

bootstrap(block) 95% CI + permutation p + BH-FDR(q=0.05)，全部在 discovery 上进行，再以 OOS 复核。

| strategy_id | n_eff | mean | CI_lo | CI_hi | perm_p | FDR_pass |
|---|---|---|---|---|---|---|
| SF-TREND-00 | 817 | -0.8885 | -1.6256 | -0.1047 | 0.9463 | n |
| SF-TREND-01 | 817 | -0.8885 | -1.6256 | -0.1047 | 0.9463 | n |
| SF-MOMENTUM-00 | 884 | -0.0425 | -0.6318 | 0.5585 | 0.3277 | n |
| SF-MOMENTUM-01 | 1133 | 0.0431 | -0.3907 | 0.5407 | 0.1860 | n |
| SF-REVERSAL-00 | 781 | -0.0348 | -0.7009 | 0.6754 | 0.3302 | n |
| SF-REVERSAL-01 | 806 | -0.1472 | -0.7523 | 0.4883 | 0.4905 | n |
| SF-RANGE-00 | 10 | nan | nan | nan | 0.1040 | n |
| SF-RANGE-01 | 3 | nan | nan | nan | nan | n |
| SF-BREAKOUT-00 | 0 | nan | nan | nan | nan | n |
| SF-BREAKOUT-01 | 0 | nan | nan | nan | nan | n |
| SF-VOL_EXPANSION-00 | 0 | nan | nan | nan | nan | n |
| SF-VOL_EXPANSION-01 | 0 | nan | nan | nan | nan | n |
| SF-VOL_CONTRACTION-00 | 56 | -0.9388 | -3.4512 | 0.8133 | 0.7993 | n |
| SF-MTF_STRUCTURE-00 | 1136 | -0.1631 | -0.8230 | 0.6364 | 0.5005 | n |
| SF-EVENT-00 | 265 | -0.2536 | -0.6431 | 0.4280 | 0.5900 | n |
| SF-MACRO-00 | 226 | -0.6237 | -2.7788 | 0.9699 | 0.7298 | n |
| SF-HYBRID-00 | 495 | -0.0601 | -0.9329 | 0.7518 | 0.4308 | n |

FDR 通过数：0 / 17

**结论**：样本跨度小、重叠持仓使独立样本有限，绝大多数统计量不显著 → 见 FINAL_REPORT 的诚实收口。