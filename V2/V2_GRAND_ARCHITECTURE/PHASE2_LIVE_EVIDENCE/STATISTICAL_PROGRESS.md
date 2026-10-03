# STATISTICAL_PROGRESS

> effective_n / bootstrap CI / permutation / FDR。样本受限，多为 INCONCLUSIVE。

| strategy_id | primary_h | n_eff | expectancy | bootstrap_lo | perm_p | fdr_pass |
|---|---|---|---|---|---|---|
| SF-TREND-00 | 60 | 698 | -0.61264 | -1.9798040390014648 | 0.84355 | False |
| SF-TREND-01 | 60 | 698 | -0.61264 | -1.9798040390014648 | 0.84355 | False |
| SF-MOMENTUM-00 | 15 | 805 | -0.40357 | -0.7763113379478455 | 0.90535 | False |
| SF-MOMENTUM-01 | 15 | 757 | -0.34995 | -0.7557877898216248 | 0.82135 | False |
| SF-REVERSAL-00 | 15 | 236 | -0.35816 | -1.166046142578125 | 0.70295 | False |
| SF-REVERSAL-01 | 15 | 264 | -0.60623 | -1.2770460844039917 | 0.8853 | False |
| SF-RANGE-00 | 15 | 3 | 0.44833 | None | None | False |
| SF-RANGE-01 | 15 | 1 | 2.45 | None | None | False |
| SF-BREAKOUT-00 | 30 | 0 | nan | None | None | False |
| SF-BREAKOUT-01 | 30 | 0 | nan | None | None | False |
| SF-VOL_EXPANSION-00 | 15 | 0 | nan | None | None | False |
| SF-VOL_EXPANSION-01 | 15 | 0 | nan | None | None | False |
| SF-VOL_CONTRACTION-00 | 30 | 17 | -2.06147 | -2.8744118213653564 | 0.93765 | False |
| SF-MTF_STRUCTURE-00 | 30 | 738 | -0.18742 | -0.9830284118652344 | 0.5466 | False |
| SF-EVENT-00 | 15 | 72 | -1.5291 | -3.544480800628662 | 0.8982 | False |
| SF-MACRO-00 | 60 | 467 | 0.23788 | -1.6009336709976196 | 0.2509 | False |
| SF-HYBRID-00 | 30 | 670 | -0.44672 | -1.2293875217437744 | 0.82975 | False |

## GPU 统计计算

- device: NVIDIA RTX A2000 Laptop GPU  per_strategy_gpu_s: 1.6642
- pooled benchmark (identical 60000-resample block bootstrap on 5426 values): GPU 0.1064s vs CPU 4.4944s → speedup 42.25x, peak_vram_mb 208.9, batch 256
- n_bootstrap: 20000  n_permutation: 20000  fdr_q: 0.05
- 结论：FDR 通过数 ≤ 个位数；诚实标注 INCONCLUSIVE / NOT_VALIDATED。
