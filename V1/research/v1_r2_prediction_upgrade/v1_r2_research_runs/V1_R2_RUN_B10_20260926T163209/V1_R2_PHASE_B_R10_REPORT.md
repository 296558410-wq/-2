# V1-R2 Phase B-R10｜PRICE_STRUCTURE_BOUNDARY_AUDIT

## 1. Executive Summary
- PRE_REGISTERED，NO_SELECTION_OF_WINNER；加载 B-R9 状态定义（sha `f1c550975409752e`）原样未改。
- TOUCH 事件（band episodes）=424；正式 PENETRATION=647；正式 FIRST_TOUCH=4。
- TOUCH→PENETRATION 自然分离：**INCONCLUSIVE**；0.30 ATR 支持度：**WEAKLY_SUPPORTED**。
- FIRST_TOUCH 稀疏主因：**PENETRATION_BOUNDARY_MASKS_TOUCH**（边界=1.00 ATR 时 FIRST_TOUCH 会变成 347）。
- BREAK persistence 自然断点：**INCONCLUSIVE**；2-bar 结构支持：**INCONCLUSIVE**。
- 诊断 RECLAIM 可达性 = 162（其中 8 bars 内 152）；FORMAL_RECLAIM=0 → **FORMAL_RULE_UNREACHABLE**。
- AMBIGUOUS=56；分类 {"A": 0, "B": 56, "C": 0, "D": 0, "E": 0, "F": 0, "G": 0}。
- REPLAY=PASS / DETERMINISTIC=PASS / NULL=PASS。

## 2. Boundary Definition (pre-registered)
- 见 `V1_R2_B10_BOUNDARY_DEFINITION.json`（hash `7b4ab8fd08ecd5b6`）。
- 参考点 TOUCH: 0.20/0.25/0.30/0.35/0.40/0.50/0.75/1.00；BREAK: 1/2/3/4/5/6/8/10。全部 shadow_only。

## 3. TOUCH→PENETRATION Distribution
- {"n": 424, "min": 0.3696, "p01": 0.5243, "p05": 0.7231, "p10": 0.7987, "p25": 1.0256, "p50": 1.3016, "median": 1.3016, "p75": 1.7565, "p90": 2.4985, "p95": 3.1054, "p99": 5.1928, "max": 6.2535, "mean": 1.5311}
- 分离判据（预注册）: [{"bin_lo": 1.15, "density": 0.0519}, {"bin_lo": 1.25, "density": 0.0542}] peaks / [{"bin_lo": 0.45, "density": 0.0}, {"bin_lo": 0.7, "density": 0.0142}, {"bin_lo": 0.8, "density": 0.0283}, {"bin_lo": 1.0, "density": 0.0307}, {"bin_lo": 1.2, "density": 0.0401}, {"bin_lo": 1.3, "density": 0.0354}, {"bin_lo": 1.45, "density": 0.0307}, {"bin_lo": 1.7, "density": 0.0094}, {"bin_lo": 1.95, "density": 0.0094}, {"bin_lo": 2.15, "density": 0.0024}, {"bin_lo": 2.25, "density": 0.0071}, {"bin_lo": 2.45, "density": 0.0024}, {"bin_lo": 2.65, "density": 0.0024}, {"bin_lo": 2.8, "density": 0.0}, {"bin_lo": 2.95, "density": 0.0024}, {"bin_lo": 3.35, "density": 0.0}, {"bin_lo": 3.45, "density": 0.0}, {"bin_lo": 3.65, "density": 0.0}, {"bin_lo": 4.1, "density": 0.0}, {"bin_lo": 4.3, "density": 0.0}, {"bin_lo": 4.45, "density": 0.0}, {"bin_lo": 4.85, "density": 0.0}, {"bin_lo": 5.0, "density": 0.0}, {"bin_lo": 5.35, "density": 0.0}, {"bin_lo": 5.7, "density": 0.0}, {"bin_lo": 6.0, "density": 0.0}, {"bin_lo": 6.3, "density": 0.0}] valleys

## 4. FIRST_TOUCH Sparsity
- {"0.2": {"FIRST_TOUCH": 0, "REPEATED_TOUCH": 0, "PENETRATION": 1066, "shadow_only": true, "promoted": false}, "0.25": {"FIRST_TOUCH": 4, "REPEATED_TOUCH": 4, "PENETRATION": 1058, "shadow_only": true, "promoted": false}, "0.3": {"FIRST_TOUCH": 7, "REPEATED_TOUCH": 7, "PENETRATION": 1052, "shadow_only": true, "promoted": false}, "0.35": {"FIRST_TOUCH": 14, "REPEATED_TOUCH": 12, "PENETRATION": 1040, "shadow_only": true, "promoted": false}, "0.4": {"FIRST_TOUCH": 28, "REPEATED_TOUCH": 18, "PENETRATION": 1020, "shadow_only": true, "promoted": false}, "0.5": {"FIRST_TOUCH": 58, "REPEATED_TOUCH": 39, "PENETRATION": 969, "shadow_only": true, "promoted": false}, "0.75": {"FIRST_TOUCH": 212, "REPEATED_TOUCH": 130, "PENETRATION": 724, "shadow_only": true, "promoted": false}, "1.0": {"FIRST_TOUCH": 347, "REPEATED_TOUCH": 221, "PENETRATION": 498, "shadow_only": true, "promoted": false}}

## 5. BREAK Persistence
- {"n": 201, "min": 1, "p01": 1.0, "p05": 1.0, "p10": 1.0, "p25": 2.0, "p50": 6.0, "median": 6, "p75": 22.0, "p90": 94.0, "p95": 154.0, "p99": 378.0, "max": 1028, "mean": 37.1791}
- at_least_k: {"1": 201, "2": 167, "3": 147, "4": 130, "5": 117, "6": 111, "8": 96, "10": 86}

## 6. BREAK Boundary Sensitivity
- {"1": {"BREAK_CONFIRMED_runs": 201, "BREAK_CONFIRMED_state_records_equiv": 7473, "shadow_only": true, "promoted": false}, "2": {"BREAK_CONFIRMED_runs": 167, "BREAK_CONFIRMED_state_records_equiv": 7272, "shadow_only": true, "promoted": false}, "3": {"BREAK_CONFIRMED_runs": 147, "BREAK_CONFIRMED_state_records_equiv": 7105, "shadow_only": true, "promoted": false}, "4": {"BREAK_CONFIRMED_runs": 130, "BREAK_CONFIRMED_state_records_equiv": 6958, "shadow_only": true, "promoted": false}, "5": {"BREAK_CONFIRMED_runs": 117, "BREAK_CONFIRMED_state_records_equiv": 6828, "shadow_only": true, "promoted": false}}
- 语义审计: {"attempt_duration_bars": {"n": 201, "min": 1, "p01": 1.0, "p05": 1.0, "p10": 1.0, "p25": 2.0, "p50": 6.0, "median": 6, "p75": 22.0, "p90": 94.0, "p95": 154.0, "p99": 378.0, "max": 1028, "mean": 37.1791}, "mean_penetration_depth_atr": 3.2367, "momentum_state": {"DECELERATING": 74, "ACCELERATING": 59, "NORMAL": 44, "SLOW": 22, "EXHAUSTING": 2}, "counter_state": {"YES": 161, "NO": 40}, "regime": {"TREND": 73, "UNKNOWN": 29, "EXPANSION": 29, "COMPRESSION": 21, "EVENT_DRIVEN": 18, "RANGE": 17, "REVERSAL": 14}, "note": "descriptive only; BREAK_ATTEMPT is NOT redefined"}
- 确认后重回原侧: {"1": 119, "2": 137, "3": 143, "5": 146, "8": 152}

## 7. RECLAIM Reachability
- {"BREAK_CONFIRMED_RUNS": 167, "DIAGNOSTIC_RECLAIM_REACHABILITY": 162, "DIAGNOSTIC_RECLAIM_WITHIN_8": 152, "FORMAL_RECLAIM": 0, "bars_to_reclaim_distribution": {"n": 162, "min": 1, "p01": 1.0, "p05": 1.0, "p10": 1.0, "p25": 1.0, "p50": 1.0, "median": 1.0, "p75": 2.0, "p90": 5.0, "p95": 13.95, "p99": 74.46, "max": 456, "mean": 6.1296}}

## 8. Ambiguity
- 分类: {"A": 0, "B": 56, "C": 0, "D": 0, "E": 0, "F": 0, "G": 0}
- 候选集合: [{"states": ["FAILED_BREAK", "RECLAIM"], "n": 56}]

## 9. Boundary Sensitivity Matrix
- 见 `V1_R2_B10_STATE_BOUNDARY_MATRIX.json`（全部 shadow_only / promoted=false）。

## 10. Replay
- [{"truncation_bars": 398, "state_hash": "71707decdd797c7fd7f95943bb987b9b", "event_hash": "0521d3869c5ab9627c2987c8d294f7c0", "boundary_hash": "71707decdd797c7fd7f95943bb987b9b", "ambiguity_hash": "5905e163482af8ec79737471a4aca0c2", "state_diffs": 0, "event_diffs": 0, "ambiguity_diffs": 0, "MATCH": true}, {"truncation_bars": 531, "state_hash": "182f155e7ba2aaf516dfb14b1effaf73", "event_hash": "33a658ee7dbc16d4cccdc38917083471", "boundary_hash": "182f155e7ba2aaf516dfb14b1effaf73", "ambiguity_hash": "5dce40e36e29b7c7d94a298ce635cbe3", "state_diffs": 0, "event_diffs": 0, "ambiguity_diffs": 0, "MATCH": true}, {"truncation_bars": 664, "state_hash": "7bf7b940682d226b010cd45b26f48b1f", "event_hash": "bc889c9e4a59ccfa62512ba568bf2515", "boundary_hash": "7bf7b940682d226b010cd45b26f48b1f", "ambiguity_hash": "0043c22f9ecccdbd98d8030f3f227081", "state_diffs": 0, "event_diffs": 0, "ambiguity_diffs": 0, "MATCH": true}, {"truncation_bars": 796, "state_hash": "08e91592f1cfae1ea0101414b3b1ee73", "event_hash": "58442650bb7451ab170ec38b469bed19", "boundary_hash": "08e91592f1cfae1ea0101414b3b1ee73", "ambiguity_hash": "27866254da64ca5292c405850ca9e75d", "state_diffs": 0, "event_diffs": 0, "ambiguity_diffs": 0, "MATCH": true}, {"truncation_bars": 929, "state_hash": "6939fd234f4fc74c2ca1f2d5f90003e3", "event_hash": "e40296b96daa6c6f61a7b9ad97cb17c6", "boundary_hash": "6939fd234f4fc74c2ca1f2d5f90003e3", "ambiguity_hash": "81af3c816815ac88426805c6ba564d61", "state_diffs": 0, "event_diffs": 0, "ambiguity_diffs": 0, "MATCH": true}, {"truncation_bars": 1062, "state_hash": "49af057a5b312d4d878c7b1cec700262", "event_hash": "9e9830a51ed7a159e8b73967185e6d0b", "boundary_hash": "49af057a5b312d4d878c7b1cec700262", "ambiguity_hash": "2af8d4a0e2e277ad8562bd88fa4f406d", "state_diffs": 0, "event_diffs": 0, "ambiguity_diffs": 0, "MATCH": true}, {"truncation_bars": 1195, "state_hash": "151499622e94742c35f802da3832a906", "event_hash": "9f3a8c25ac8cc416600136dadb98075c", "boundary_hash": "151499622e94742c35f802da3832a906", "ambiguity_hash": "99f057d728b1f64414f6198473f91550", "state_diffs": 0, "event_diffs": 0, "ambiguity_diffs": 0, "MATCH": true}, {"truncation_bars": 1261, "state_hash": "a353ca0432a3db53b33de05833e41cca", "event_hash": "f57df6b7d62757be629e36baf398a778", "boundary_hash": "a353ca0432a3db53b33de05833e41cca", "ambiguity_hash": "6001915c1449c532dc687fad910dec39", "state_diffs": 0, "event_diffs": 0, "ambiguity_diffs": 0, "MATCH": true}]

## 11. Determinism
- RUN_A==RUN_B: True

## 12. Null
- {"price_sequence_shuffle": {"states_after_shuffle": {"NO_STRUCTURE": 16022, "EXHAUSTION": 1016, "PENETRATION": 369, "BREAK_ATTEMPT": 359, "AMBIGUOUS_STATE": 301, "APPROACH": 296, "BREAK_CONFIRMED": 55, "FIRST_TOUCH": 19, "REPEATED_TOUCH": 6}, "identical_to_real": false}, "NULL_TEST": "PASS", "note": "sanity only; not used to choose any boundary"}

## 13. Limitations
- 所有 shadow 边界仅为诊断参考点；本轮**不选优、不改正式规则**。
- BREAK persistence 用 beyond-close run 长度近似正式 2-bar 规则；两者已在 `BREAK_CONFIRMED` 计数上交叉核对。
- RECLAIM 的可达性用无界后续路径测量，仅作诊断。

## 14. Next
- **PENETRATION_BOUNDARY_JUSTIFICATION_STUDY**。

## 15. Safety
- ORDER_SEND=0 / ORDER_CHECK=0 / BROKER_WRITE=0；FORWARD=OFF / SHADOW=OFF / LIVE=OFF。
- ENGINE_PY_MODIFIED=0 / REGISTRY_MODIFIED=0 / PARAMETER_MODIFIED=0 / DIRECTION_MAPPING_MODIFIED=0。
- FUTURE_RETURN_USED=NO / PNL_USED=NO / WIN_RATE_USED=NO / TRADE_OUTCOME_USED=NO；GIT_COMMIT=NONE。
