# EVOLUTION_ENGINE_REPORT

无固定 48h；触发因素：edge degradation / regime transition / MAE expansion / MFE contraction / confidence drift / cost sensitivity。状态：NO_CHANGE / SHADOW / CANDIDATE_RELEASE / RETIRED。

状态计数：`{"SHADOW": 11, "NO_CHANGE": 5, "CANDIDATE_RELEASE": 1}`

| strategy_id | state | triggers |
|---|---|---|
| SF-TREND-00 | SHADOW | cost_sensitivity |
| SF-TREND-01 | SHADOW | cost_sensitivity |
| SF-MOMENTUM-00 | SHADOW | cost_sensitivity |
| SF-MOMENTUM-01 | SHADOW | edge_degradation, cost_sensitivity |
| SF-REVERSAL-00 | SHADOW | cost_sensitivity |
| SF-REVERSAL-01 | SHADOW | cost_sensitivity |
| SF-RANGE-00 | NO_CHANGE | — |
| SF-RANGE-01 | SHADOW | edge_degradation |
| SF-BREAKOUT-00 | NO_CHANGE | — |
| SF-BREAKOUT-01 | NO_CHANGE | — |
| SF-VOL_EXPANSION-00 | NO_CHANGE | — |
| SF-VOL_EXPANSION-01 | NO_CHANGE | — |
| SF-VOL_CONTRACTION-00 | SHADOW | cost_sensitivity |
| SF-MTF_STRUCTURE-00 | SHADOW | cost_sensitivity |
| SF-EVENT-00 | CANDIDATE_RELEASE | cost_sensitivity |
| SF-MACRO-00 | SHADOW | cost_sensitivity |
| SF-HYBRID-00 | SHADOW | cost_sensitivity |