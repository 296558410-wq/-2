# GPU_USAGE_REPORT

> 复用 Phase-1 `gpu_research/engine.py`；**不重复** 13,296 组合全量搜索（spec §12），
> 只做新增 shadow 结果驱动的增量批处理。

## 真机与耗时

- device: **NVIDIA RTX A2000 Laptop GPU** (cuda=True)
- per-strategy bootstrap+permutation GPU runtime: **1.6642s**
- pooled benchmark (identical 60000-resample block bootstrap on 5426 values): GPU **0.1064s** vs CPU **4.4944s** → speedup **42.25x**
- peak VRAM: **208.9MB**, batch size: 256
- n_bootstrap: 20000, n_permutation: 20000, block: 5, FDR q: 0.05
- series processed: 11; incremental grid combos: 32 (0.0667s)
- purpose: incremental bootstrap/permutation/FDR on shadow outcomes + small incremental grid; full 13,296-combo search intentionally NOT re-run (spec section 12)

## 每策略统计（GPU）

| strategy_id | n_eff | boot_lo | boot_hi | perm_p | fdr_pass |
|---|---|---|---|---|---|
| SF-TREND-00 | 698 | -1.9798040390014648 | 0.7468636631965637 | 0.84355 | False |
| SF-TREND-01 | 698 | -1.9798040390014648 | 0.7468636631965637 | 0.84355 | False |
| SF-MOMENTUM-00 | 805 | -0.7763113379478455 | -0.026706648990511894 | 0.90535 | False |
| SF-MOMENTUM-01 | 757 | -0.7557877898216248 | 0.051824674010276794 | 0.82135 | False |
| SF-REVERSAL-00 | 236 | -1.166046142578125 | 0.24995209276676178 | 0.70295 | False |
| SF-REVERSAL-01 | 264 | -1.2770460844039917 | -0.008603906258940697 | 0.8853 | False |
| SF-RANGE-00 | 3 | None | None | None | False |
| SF-RANGE-01 | 1 | None | None | None | False |
| SF-BREAKOUT-00 | 0 | None | None | None | False |
| SF-BREAKOUT-01 | 0 | None | None | None | False |
| SF-VOL_EXPANSION-00 | 0 | None | None | None | False |
| SF-VOL_EXPANSION-01 | 0 | None | None | None | False |
| SF-VOL_CONTRACTION-00 | 17 | -2.8744118213653564 | 0.4017646610736847 | 0.93765 | False |
| SF-MTF_STRUCTURE-00 | 738 | -0.9830284118652344 | 0.6317899227142334 | 0.5466 | False |
| SF-EVENT-00 | 72 | -3.544480800628662 | 0.12475765496492386 | 0.8982 | False |
| SF-MACRO-00 | 467 | -1.6009336709976196 | 1.8549613952636719 | 0.2509 | False |
| SF-HYBRID-00 | 670 | -1.2293875217437744 | 0.35271042585372925 | 0.82975 | False |

## 说明

- GPU 仅用于**加速**，不改变任何口径；失败的统计仍如实标注。
- CPU baseline 对同一序列做等量 bootstrap 后按序列数缩放比较。
