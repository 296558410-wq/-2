# STRATEGY_FACTORY_REPORT

code_commit `23116019e2a4c47a7e4eec4150d61ac3681b788f`

机制族：11；生成候选策略：17（全部为独立机制，非 V1/V2 规则复制）。

| strategy_id | mechanism | horizon | disc_n | disc_exp | val_exp | oos_n | oos_exp | fdr |
|---|---|---|---|---|---|---|---|---|
| SF-TREND-00 | TREND | 60 | 817 | -0.8885 | -0.9350 | 605 | 0.5675 | n |
| SF-TREND-01 | TREND | 60 | 817 | -0.8885 | -0.9350 | 605 | 0.5675 | n |
| SF-MOMENTUM-00 | MOMENTUM | 20 | 884 | -0.0425 | -0.6384 | 652 | 0.0296 | n |
| SF-MOMENTUM-01 | MOMENTUM | 20 | 1133 | 0.0431 | -0.2822 | 878 | -0.2083 | n |
| SF-REVERSAL-00 | REVERSAL | 20 | 781 | -0.0348 | -0.1527 | 562 | 0.1153 | n |
| SF-REVERSAL-01 | REVERSAL | 20 | 806 | -0.1472 | 0.0390 | 586 | -0.1269 | n |
| SF-RANGE-00 | RANGE | 15 | 10 | 1.8790 | 2.5455 | 8 | 0.4700 | n |
| SF-RANGE-01 | RANGE | 15 | 3 | 2.4550 | nan | 3 | 1.1967 | n |
| SF-BREAKOUT-00 | BREAKOUT | 30 | 0 | nan | nan | 0 | nan | n |
| SF-BREAKOUT-01 | BREAKOUT | 30 | 0 | nan | nan | 0 | nan | n |
| SF-VOL_EXPANSION-00 | VOL_EXPANSION | 15 | 0 | nan | nan | 0 | nan | n |
| SF-VOL_EXPANSION-01 | VOL_EXPANSION | 15 | 0 | nan | nan | 0 | nan | n |
| SF-VOL_CONTRACTION-00 | VOL_CONTRACTION | 30 | 56 | -0.9388 | -1.6350 | 38 | -0.3237 | n |
| SF-MTF_STRUCTURE-00 | MTF_STRUCTURE | 30 | 1136 | -0.1631 | -0.5382 | 909 | -0.0069 | n |
| SF-EVENT-00 | EVENT | 10 | 265 | -0.2536 | 0.0625 | 190 | 0.0836 | n |
| SF-MACRO-00 | MACRO | 60 | 226 | -0.6237 | 0.0478 | 162 | -0.1667 | n |
| SF-HYBRID-00 | HYBRID | 45 | 495 | -0.0601 | -0.8006 | 355 | 0.3432 | n |

每个候选的完整元数据（hypothesis_id/mechanism/feature_set/parameters/expected_horizon/applicable_regime/entry/exit/invalidation/cost_model/PIT/creation commit/dataset hash）见 `STRATEGY_REGISTRY.jsonl`。