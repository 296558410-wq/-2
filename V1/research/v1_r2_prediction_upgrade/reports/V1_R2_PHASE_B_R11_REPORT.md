# V1-R2 Phase B-R11｜PENETRATION_BOUNDARY_JUSTIFICATION_STUDY

## 1. Executive Summary
- 预注册依据 registry hash `aebb69855da547fa`；B-R9 状态定义 `f1c550975409752e` 原样加载。
- TOUCH episodes = 424（全量，无选择偏差）；连续变量保留，未先二值化。
- **PENETRATION_STATE_JUSTIFICATION = INCONCLUSIVE**
- **PENETRATION_THRESHOLD_JUSTIFICATION = INCONCLUSIVE**
- 自然分离：`INCONCLUSIVE` / mixture ΔBIC=9.096 / 分离度=0.4477 ATR → **INCONCLUSIVE**
- P(PENETRATION|NOT_TOUCH) = 0.0（**构造性为 0**）
- 100% touch 的 pen_max ≥ TOUCH_TOL 的比例 = 1.0
- 反证判定 = **INCONCLUSIVE**（YES 计数 2）
- REPLAY=PASS / DETERMINISTIC=PASS / NULL=PASS

## 2. Boundary Definition (pre-registered)
- 见 `V1_R2_B11_BOUNDARY_JUSTIFICATION_REGISTRY.json`（shadow boundaries [0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.75, 1.0]）。
- 无新增边界；无选优；全部 shadow_only / promoted=false。

## 3. Continuous Penetration Distribution
- {"n": 424, "min": 0.3696, "p01": 0.5243, "p05": 0.7231, "p10": 0.7987, "p25": 1.0256, "median": 1.3016, "p75": 1.7565, "p90": 2.4985, "p95": 3.1054, "p99": 5.1928, "max": 6.2535, "mean": 1.5311, "std": 0.8529}
- ECDF: [{"value": 0.25, "share_le": 0.0}, {"value": 0.3, "share_le": 0.0}, {"value": 0.35, "share_le": 0.0}, {"value": 0.4, "share_le": 0.0024}, {"value": 0.5, "share_le": 0.0071}, {"value": 0.75, "share_le": 0.0637}, {"value": 1.0, "share_le": 0.2429}, {"value": 1.5, "share_le": 0.6392}, {"value": 2.0, "share_le": 0.8184}, {"value": 3.0, "share_le": 0.9434}, {"value": 4.0, "share_le": 0.967}, {"value": 6.0, "share_le": 0.9976}]

## 4. Natural Separation
- valley: INCONCLUSIVE
- mixture: {"BIC_1": 548.459, "BIC_2": 539.363, "delta_BIC": 9.096, "component_means_log": [0.18258305658052115, 0.4995454470579221], "component_weights": [0.590365214734879, 0.4096347852651257], "separation_atr": 0.4477, "implied_split_atr": 1.4064, "mixture_rule_met": false}
- 判定: **INCONCLUSIVE**

## 5. Persistence
- per boundary: {"0.20": {"episodes": 424, "median": 2.0, "max": 10}, "0.25": {"episodes": 431, "median": 2, "max": 9}, "0.30": {"episodes": 435, "median": 2, "max": 9}, "0.35": {"episodes": 439, "median": 2, "max": 9}, "0.40": {"episodes": 450, "median": 2.0, "max": 8}, "0.50": {"episodes": 470, "median": 2.0, "max": 7}, "0.75": {"episodes": 469, "median": 1, "max": 5}, "1.00": {"episodes": 357, "median": 1, "max": 5}}
- TOUCH episode duration: {"n": 424, "min": 1, "p01": 1.0, "p05": 1.0, "p10": 1.0, "p25": 1.0, "median": 2.0, "p75": 3.0, "p90": 4.0, "p95": 5.0, "p99": 7.77, "max": 10, "mean": 2.5142, "std": 1.4857}

## 6. Touch Overlap
- {"bar_level": {"bars_in_touch_band": 1066, "bars_total_(bar,level)": 22141, "P_PENETRATION_given_TOUCH": 0.9869, "P_PENETRATION_given_NOT_TOUCH": 0.0, "P_TOUCH_given_PENETRATION": 1.0, "note": "P(PENETRATION|NOT_TOUCH)=0 by CONSTRUCTION: penetration_ratio is only computed inside the band"}, "episode_level": {"touch_episodes": 424, "episodes_with_side_flip": 262, "P_SIDEFLIP_given_TOUCH": 0.6179}, "PEN_DEF_GEOMETRY_ONLY": {"definition": "close crossed to the opposite side of level.price", "observations_outside_touch_band": 74, "P_PEN_given_NOT_TOUCH_geometry_only": 0.0035}, "STATE_DEFINITION_OVERLAP": "PENETRATION is a strict subset of TOUCH under the formal definition"}

## 7. Transition Structure
- {"PENETRATION_next_state_distribution": {"PENETRATION": 315, "BREAK_ATTEMPT": 124, "NO_STRUCTURE": 117, "APPROACH": 80, "REPEATED_TOUCH": 5, "FIRST_TOUCH": 3, "EXHAUSTION": 3}, "CIRCULARITY_GUARD": "descriptive only; PENETRATION->BREAK/* is NOT admissible as proof that PENETRATION is a legitimate state (task 17)", "PENETRATION_to_BREAK_ATTEMPT": 124, "PENETRATION_to_BREAK_CONFIRMED": 0, "PENETRATION_to_EXHAUSTION": 3, "PENETRATION_to_EXIT_out_of_band": 197}

## 8. Continuous Independence
- {"continuous_variables": ["penetration_ratio = distance_inside_level / ATR20 (continuous, never binarised first)", "distance_to_level_atr = |close - level_price| / ATR20", "bars_inside_level (running count inside the band episode)", "max_excursion_inside_level (running max of penetration_ratio within the episode)", "close_position_relative_to_level = (close - level_price) / ATR20", "range_normalised_penetration = penetration_distance / (bar high - bar low)", "atr_normalised_penetration = penetration_ratio"], "penetration_vs_touch_tol": {"formal_TOUCH_TOL_ATR": 0.25, "formal_PENETRATION_ATR": 0.3, "share_of_episodes_with_pen_max_below_tol": 0.0, "min_pen_max": 0.3696}, "is_discretisation_of_one_variable": true, "reason": "pen_ratio = max(high-price, price-low)/ATR computed ONLY inside the touch band; a boundary on it is a threshold on one continuous geometric variable already conditional on TOUCH"}

## 9. Feature Lineage
- {"RAW_SOURCE_COUNT": 1, "chain": "TICK_BID -> OHLC_15M -> (ATR20) + (level price from PIVOT/RANGE fractals) -> penetration_ratio", "PENETRATION_inputs": ["TICK_BID", "OHLC_15M", "ATR20", "LEVEL.price"], "TOUCH_inputs": ["TICK_BID", "OHLC_15M", "ATR20", "LEVEL.price"], "LEVEL_inputs": ["TICK_BID", "OHLC_15M"], "BREAK_inputs": ["LEVEL", "ABSORPTION", "VEL4"], "statement": "PENETRATION / TOUCH / LEVEL / BREAK are different GEOMETRIC TRANSFORMS of the SAME single bid price path; not independent data sources", "independent_data_sources": ["TICK_BID (price)", "TICK_ASK (spread, unused by the state machine)"]}

## 10. Boundary Sensitivity
- {"0.20": {"episode_count": 424, "median_duration": 2.0, "p90_duration": 4.0}, "0.25": {"episode_count": 431, "median_duration": 2, "p90_duration": 4.0}, "0.30": {"episode_count": 435, "median_duration": 2, "p90_duration": 4.0}, "0.35": {"episode_count": 439, "median_duration": 2, "p90_duration": 4.0}, "0.40": {"episode_count": 450, "median_duration": 2.0, "p90_duration": 4.0}, "0.50": {"episode_count": 470, "median_duration": 2.0, "p90_duration": 4.0}, "0.75": {"episode_count": 469, "median_duration": 1, "p90_duration": 3.0}, "1.00": {"episode_count": 357, "median_duration": 1, "p90_duration": 2.0}}

## 11. Temporal Stability
- {"blocks": [{"block": "EARLY", "n": 141, "median": 1.3842, "p25": 0.9684, "p75": 1.929, "p90": 2.9349, "start_ts": null}, {"block": "MIDDLE", "n": 141, "median": 1.2657, "p25": 0.9842, "p75": 1.8133, "p90": 2.5694, "start_ts": null}, {"block": "LATE", "n": 142, "median": 1.3113, "p25": 1.0966, "p75": 1.6153, "p90": 2.0689, "start_ts": null}], "block_medians_delta": 0.1185, "rule": "YES if the 3 blocks have overlapping IQRs and medians within 0.10 ATR; NO if monotone drift or disjoint IQRs; INCONCLUSIVE otherwise", "VERDICT": "DISTRIBUTION_SHIFTING"}

## 12. Level Type Stability
- {"PIVOT_n": 385, "RANGE_n": 39, "median_delta_atr": -0.167, "rule": "YES if PIVOT and RANGE medians differ by < 0.15 ATR; NO if >= 0.15 ATR; INCONCLUSIVE if either n < 30", "VERDICT": "NO"}

## 13. Direction Symmetry
- {"UP_n": 195, "DN_n": 229, "median_delta_atr": 0.1036, "rule": "same rule on UP_LEVEL vs DN_LEVEL", "DIRECTIONAL_ASYMMETRY": "NONE_DETECTED", "VERDICT": "YES"}

## 14. Counter Evidence
- {"A_all_touch_show_clear_penetration": {"value": 1.0, "answer": "YES", "meaning": "if ~100% of touches exceed the penetration boundary, the state distinguishes almost nothing"}, "B_penetration_is_the_continuous_tail_of_touch_geometry": {"answer": "YES", "evidence": "P(PEN|NOT_TOUCH)=0 by construction; single continuous variable"}, "C_no_transition_difference_between_depths": {"answer": "INCONCLUSIVE", "evidence": "transition frequencies vary smoothly with the boundary (see BOUNDARY_SENSITIVITY) but the chain is circular"}, "D_penetration_not_stably_repeatable": {"answer": "NO", "evidence": {"blocks": [{"block": "EARLY", "n": 141, "median": 1.3842, "p25": 0.9684, "p75": 1.929, "p90": 2.9349, "start_ts": null}, {"block": "MIDDLE", "n": 141, "median": 1.2657, "p25": 0.9842, "p75": 1.8133, "p90": 2.5694, "start_ts": null}, {"block": "LATE", "n": 142, "median": 1.3113, "p25": 1.0966, "p75": 1.6153, "p90": 2.0689, "start_ts": null}], "block_medians_delta": 0.1185, "rule": "YES if the 3 blocks have overlapping IQRs and medians within 0.10 ATR; NO if monotone drift or disjoint IQRs; INCONCLUSIVE otherwise", "VERDICT": "DISTRIBUTION_SHIFTING"}}, "E_time_blocks_differ_completely": {"answer": "NO", "evidence": {"blocks": [{"block": "EARLY", "n": 141, "median": 1.3842, "p25": 0.9684, "p75": 1.929, "p90": 2.9349, "start_ts": null}, {"block": "MIDDLE", "n": 141, "median": 1.2657, "p25": 0.9842, "p75": 1.8133, "p90": 2.5694, "start_ts": null}, {"block": "LATE", "n": 142, "median": 1.3113, "p25": 1.0966, "p75": 1.6153, "p90": 2.0689, "start_ts": null}], "block_medians_delta": 0.1185, "rule": "YES if the 3 blocks have overlapping IQRs and medians within 0.10 ATR; NO if monotone drift or disjoint IQRs; INCONCLUSIVE otherwise", "VERDICT": "DISTRIBUTION_SHIFTING"}}, "counter_evidence_verdict": "INCONCLUSIVE"}

## 15. Replay / Determinism / Null
- REPLAY=PASS（8 个截断点，4 组 hash）; DETERMINISTIC=PASS; NULL=PASS

## 16. Limitations
- 所有 shadow 边界仅作诊断；本轮**未修改**任何正式参数。
- PENETRATION→BREAK 的转移频率属**循环证据**，不作为 PENETRATION 合法性的证明。
- 样本 3 个日历日（09-23…09-25），时间稳定性结论受限于此。

## 17. Next
- **STUDY_ALTERNATIVE_DEFINITION**（正式 State Machine 任何修改留待下一独立任务）。

## 18. Safety
- ORDER_SEND=0 / ORDER_CHECK=0 / BROKER_WRITE=0；FORWARD=OFF / SHADOW=OFF / LIVE=OFF。
- ENGINE_PY_MODIFIED=0 / REGISTRY_MODIFIED=0 / PARAMETER_MODIFIED=0 / DIRECTION_MAPPING_MODIFIED=0。
- FUTURE_RETURN_USED=NO / PNL_USED=NO / WIN_RATE_USED=NO / TRADE_OUTCOME_USED=NO；GIT_COMMIT=NONE。
