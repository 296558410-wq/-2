# ROLLING_EVOLUTION

> Source: `data/ROLLING_EVOLUTION.json`, `data/EXPERIMENTS.json` (Exp 9).

## Question

Would a **rolling restart / periodic re-adaptation** (reset age every W trades) recover an edge?

## Test performed (offline, read-only)

Within-block "first half" test: partition each system's trades into contiguous blocks of W = 10 and
measure the mean of the first half of each block (the "just restarted" portion).

| System | n blocks | mean within-block first half |
|---|---|---|
| V1_OLD | 11 | see `ROLLING_EVOLUTION.json` |
| V1_NEW | 4 | see `ROLLING_EVOLUTION.json` |

## Why this is NOT_EVALUABLE

A rolling-restart **recovery** claim requires all three:

1. a real, measured decay to recover from (absent — see `STATISTICAL_EVIDENCE.md`),
2. a live adaptive path whose effect can be measured on real trades (V2 has **0 executed trades**),
3. an out-of-sample test window (none exists; only ~24 days of real trades total).

None is satisfied. Simulating restarts on the same 109/32 trades that already fail the placebo
control would be circular.

## Verdict

`ROLLING_EVOLUTION = NOT_EVALUABLE`.

**Engineering consequence:** a V2 adaptive Evolution mechanism is **not warranted** by the historical
evidence. Per the lab ground rules this is a **NO_CHANGE** outcome; no production change is made and
no next phase is started.
