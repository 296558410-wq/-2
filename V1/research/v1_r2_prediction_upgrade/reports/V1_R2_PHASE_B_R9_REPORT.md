# V1-R2 Phase B-R9｜PRICE_STRUCTURE_STATE_MODEL 生命周期审计

## 1. Executive Summary
- 诊断状态机（DIAGNOSTIC_ONLY）：10 状态，定义 hash `9588233f1ddbe0e2`，**冻结于全量运行之前**。
- 层级：244 levels，22141 条 (bar, level) 状态记录，1609 个 episode。
- 生命周期可重复性：**YES**；REPLAY=PASS / DETERMINISTIC=PASS。

## 2. State Definition
- 见 `V1_R2_B9_STATE_DEFINITION.json`（entry/exit/persistence/required/forbidden/ambiguity 齐备）。
- 互斥规则：同 (timestamp, level_id) 最多一个 primary；同 phase 多满足 → AMBIGUOUS_STATE（不设优先级）。

## 3. Lifecycle
- episodes=1609；平均时长 13.761 bars；flip_rate=0.0623。

## 4. Transition Matrix
- 共 30 条转换；VALID=24 / INVALID=6 / AMBIGUOUS=56。
- TOP: [{"previous": "NO_STRUCTURE", "next": "NO_STRUCTURE", "count": 19601, "median_duration_bars": 6.0, "ambiguous": 0}, {"previous": "EXHAUSTION", "next": "EXHAUSTION", "count": 388, "median_duration_bars": 2, "ambiguous": 0}, {"previous": "PENETRATION", "next": "PENETRATION", "count": 315, "median_duration_bars": 2.0, "ambiguous": 0}, {"previous": "NO_STRUCTURE", "next": "APPROACH", "count": 247, "median_duration_bars": 1, "ambiguous": 0}, {"previous": "APPROACH", "next": "APPROACH", "count": 199, "median_duration_bars": 1, "ambiguous": 0}]

## 5. Persistence
- {"NO_STRUCTURE": {"episodes": 428, "min": 1, "median": 6.0, "p75": 28.0, "p90": 100.60000000000002, "max": 1224, "mean": 46.8, "duration_seconds_median": 5400.0}, "APPROACH": {"episodes": 391, "min": 1, "median": 1, "p75": 2.0, "p90": 3.0, "max": 7, "mean": 1.51, "duration_seconds_median": 900}, "FIRST_TOUCH": {"episodes": 4, "min": 1, "median": 1.0, "p75": 1.0, "p90": 1.0, "max": 1, "mean": 1.0, "duration_seconds_median": 900.0}, "REPEATED_TOUCH": {"episodes": 5, "min": 1, "median": 1, "p75": 1.0, "p90": 1.6, "max": 2, "mean": 1.2, "duration_seconds_median": 900}, "PENETRATION": {"episodes": 332, "min": 1, "median": 2.0, "p75": 2.0, "p90": 4.0, "max": 8, "mean": 1.95, "duration_seconds_median": 1800.0}, "BREAK_ATTEMPT": {"episodes": 217, "min": 1, "median": 1, "p75": 1.0, "p90": 1.0, "max": 4, "mean": 1.13, "duration_seconds_median": 900}, "BREAK_CONFIRMED": {"episodes": 161, "min": 1, "median": 1, "p75": 1.0, "p90": 1.0, "max": 1, "mean": 1.0, "duration_seconds_median": 900}, "RECLAIM": {"episodes": 0, "min": null, "median": null, "p75": null, "p90": null, "max": null, "mean": null, "duration_seconds_median": null}, "FAILED_BREAK": {"episodes": 0, "min": null, "median": null, "p75": null, "p90": null, "max": null, "mean": null, "duration_seconds_median": null}, "EXHAUSTION": {"episodes": 15, "min": 1, "median": 2, "p75": 8.5, "p90": 79.39999999999998, "max": 224, "mean": 26.87, "duration_seconds_median": 1800}}

## 6. Stability
- {"state_flip_count": 1365, "state_flip_rate": 0.0623, "mean_state_duration_bars": 13.761, "total_consecutive_pairs": 21897, "ambiguous_records": 56}

## 7. Level Identity
- levels=244；POSSIBLE_DUPLICATE_LEVEL=0（仅报告）。

## 8. Range Boundary
- {"RANGE_BOUNDARY_LEVELS": 17, "RANGE_BOUNDARY_BAR_RECORDS": 4709, "BAND_ENTER_events": 39, "BREAK_ATTEMPT": 16, "BREAK_CONFIRMED": 13, "RECLAIM": 0, "FAILED_BREAK": 0, "median_episodes_per_range_level": 6, "note": "range boundaries are re-created by rolling extremes; repeated events / false breaks reported, not fixed"}

## 9. HOLD_QUIET 15
- {"PENETRATION": 8, "BREAK_CONFIRMED": 1, "EXHAUSTION": 1, "NO_STRUCTURE": 2, "BREAK_ATTEMPT": 2, "AMBIGUOUS_STATE": 1}（n=15）

## 10. BREAK_PASSTHROUGH
- {"BREAK_ATTEMPT": 3, "PENETRATION": 4}（n=7）

## 11. REVERSION
- {"PENETRATION": 8, "EXHAUSTION": 5, "NO_STRUCTURE": 5, "AMBIGUOUS_STATE": 1, "BREAK_CONFIRMED": 1}（n=20）

## 12. Overlay
- 见 `V1_R2_B9_STATE_OVERLAY.jsonl`（描述用，不合成正式规则）。

## 13. Replay
- [{"truncation_bars": 398, "compared_states": 3007, "differences": 0, "PASS": true, "sample_diffs": []}, {"truncation_bars": 531, "compared_states": 4730, "differences": 0, "PASS": true, "sample_diffs": []}, {"truncation_bars": 664, "compared_states": 6946, "differences": 0, "PASS": true, "sample_diffs": []}, {"truncation_bars": 796, "compared_states": 9136, "differences": 0, "PASS": true, "sample_diffs": []}, {"truncation_bars": 929, "compared_states": 11779, "differences": 0, "PASS": true, "sample_diffs": []}, {"truncation_bars": 1062, "compared_states": 14735, "differences": 0, "PASS": true, "sample_diffs": []}, {"truncation_bars": 1195, "compared_states": 18093, "differences": 0, "PASS": true, "sample_diffs": []}, {"truncation_bars": 1261, "compared_states": 19699, "differences": 0, "PASS": true, "sample_diffs": []}]

## 14. Determinism
- {"run_a_hash": "8036bdbe7bc300abd21415005dd9527dfd9f512b2664faf0ebca2699ac5b6109", "run_b_hash": "8036bdbe7bc300abd21415005dd9527dfd9f512b2664faf0ebca2699ac5b6109", "DETERMINISTIC_TEST": "PASS"}

## 15. Null
- {"price_sequence_shuffle": {"states_after_shuffle": {"NO_STRUCTURE": 16022, "EXHAUSTION": 1016, "PENETRATION": 369, "BREAK_ATTEMPT": 359, "AMBIGUOUS_STATE": 301, "APPROACH": 296, "BREAK_CONFIRMED": 55, "FIRST_TOUCH": 19, "REPEATED_TOUCH": 6}, "identical_to_real": false, "note": "sanity only; never used to search a best state sequence or tune anything"}, "NULL_TEST": "PASS"}

## 16. Limitations
- 诊断状态由本脚本从 RAW BID OHLC 重建（未复用 break_risk）；`break_risk` 不参与 BREAK_ATTEMPT 判定。
- EXHAUSTION 仅为 SUBSTATE，不等价 REVERSION。
- 参数未做敏感性扫描；报告分布，不设“好/坏”阈值。
- 样本 3 个日历日（09-23…09-25）。

## 17. Next
- **PERSISTENCE_AND_AMBIGUITY_RESOLUTION_MODEL**（先把持久性与歧义消解做实）。

## 18. Safety
- ORDER_SEND=0 / ORDER_CHECK=0 / BROKER_WRITE=0；FORWARD=OFF / SHADOW=OFF / LIVE=OFF。
- ENGINE_PY_MODIFIED=0 / REGISTRY_MODIFIED=0 / PARAMETER_MODIFIED=0 / DIRECTION_MAPPING_MODIFIED=0。
- FUTURE_RETURN_USED=NO / PNL_USED=NO / WIN_RATE_USED=NO；GIT_COMMIT=NONE。
