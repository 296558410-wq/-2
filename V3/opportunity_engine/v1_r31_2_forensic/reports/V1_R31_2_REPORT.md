# R31.2 forensic + determinism

```text
V1_V2_TOTAL_HITS = 27
histogram = {"A": 17, "B": 9, "C": 1}
V1_V2_ISOLATION = PASS
blocking = 0
ENGINE_CHANGE_REQUIRED = NO
DETERMINISTIC_TEST = PASS
REPLAY_TEST = PASS
V2_UNCHANGED = PASS
R31_GATE = PASS
```

## re-adjudication of previous 9 D/E

| prev_file | line | prev | new | sub | disposition |
|---|---:|---|---|---|---|
| `research/hermes/trader_v2/tests/test_dashboard_fullchain.py` | 81 | D | B |  |  |
| `research/hermes/trader_v2/tests/test_data_sources.py` | 179 | D | B |  |  |
| `research/hermes/trader_v2/tests/test_module4_loop.py` | 173 | D | B |  |  |
| `research/hermes/trader_v2/tests/test_module5_paths.py` | 94 | D | B |  |  |
| `research/hermes/trader_v2/tests/test_paper_final_validation.py` | 176 | D | B |  |  |
| `research/hermes/trader_v2/tests/test_research_compute.py` | 151 | D | B |  |  |
| `research/hermes/trader_v2/tests/test_research_compute.py` | 152 | D | B |  |  |
| `research/hermes/trader_v2/tests/test_v2_repair.py` | 145 | D | B |  |  |
| `research/hermes/trader_v2/tests/test_v2_repair.py` | 149 | D | B |  |  |

## blocking items

```text
[]
```

## warnings

```text
[{"file": "run_state/tmp/active_1932Z.py", "parse": "SYNTAX_ERROR"}, {"file": "run_state/tmp/append_summary_0032.py", "parse": "SYNTAX_ERROR"}, {"file": "run_state/tmp/append_summary_0547.py", "parse": "SYNTAX_ERROR"}, {"file": "run_state/tmp/append_summary_0617.py", "parse": "SYNTAX_ERROR"}, {"file": "run_state/tmp/append_summary_1017Z.py", "parse": "SYNTAX_ERROR"}, {"file": "run_state/tmp/append_summary_1932Z.py", "parse": "SYNTAX_ERROR"}, {"file": "run_state/tmp/append_summary_2017.py", "parse": "SYNTAX_ERROR"}, {"file": "run_state/tmp/baserate_0247Z.py", "parse": "SYNTAX_ERROR"}, {"file": "run_state/tmp/baserate_0302Z.py", "parse": "SYNTAX_ERROR"}, {"file": "run_state/tmp/baserate_0317Z.py", "parse": "SYNTAX_ERROR"}]
```