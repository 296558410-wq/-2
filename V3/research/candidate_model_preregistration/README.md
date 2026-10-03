# Candidate Model Pre-Registration — V3-HFT-CANDIDATE-MODEL-PREREGISTRATION-001

`PREREGISTRATION_ONLY / READ_ONLY` · `PREREGISTRATION_ID = V3-HFT-PREREG-001`
`MODEL_TRAINING = OFF` · `ALPHA_SEARCH = OFF` · `FEATURE_MINING = OFF`
`ORDER_SEND = 0` · no MT5 connection · no backtest · no parameter search

## Sole objective

Freeze, **before any result exists**, how the three distilled candidates will be proven effective or
ineffective:

```text
CAND-001 Execution-Aware L1 Markout Gate        -> LEVEL-2
CAND-002 Spread-State Execution                 -> LEVEL-1
CAND-003 Adverse-Selection Conditional Exit     -> LEVEL-3
+ LEVEL-0 Cost-Only Baseline
```

This task produces **`PREREGISTRATION_READY`** — never `ALPHA_FOUND`, `PROFITABLE` or `TRADING_READY`.

## Registered ladder

```text
LEVEL-0  cost-to-move baseline                        (no predictor)
LEVEL-1  CAND-002  economic gate, no direction
LEVEL-2  CAND-001  directional, cost-aware gate
LEVEL-3  CAND-003  conditional exit (same-entry comparison)
```
Every rung must show **incremental information** over the rung below it, on the same instants, data and
cost tiers. Round 1 isolates mechanisms: **one model at a time, no combination tuning.**

## Frozen core constants

```text
HORIZONS_PRESENT     2 s
FEATURES             15 registered (list frozen)
LABELS               4 objects; future outcomes are LABEL_ONLY
COST                 0.914 bp / 0.40 USD ; tiers 0.40/0.50/0.60/0.80/1.00 USD
PURGE / EMBARGO      >= 300 s (max label horizon)
MIN_RAW_N            500
MIN_EFFECTIVE_N      per horizon (274 / 494 / 1,439 / 2,679 / 13,069)
FDR                  BH q = 0.05 over a family of 20 primary tests
BOOTSTRAP            moving block, 2000 resamples, block = max(50, 10*rho), seed 20260922
DECISION             TAKE / WAIT / EXIT        (WAIT is a legitimate outcome)
```

## Test boundary (honest state)

```text
The window 2026-09-07 .. 2026-09-21 has ALREADY BEEN VIEWED by an earlier V3 task
=> it is DEMOTED to DEVELOPMENT_CONTAMINATED and may NOT be the evaluation set.
TEST = a FUTURE, not-yet-collected window (rule frozen; 10 usable sessions after the preregistration).
TEST_BOUNDARY = RULE_LOCKED ; TEST_LOCKED_HASH = PENDING_NOT_YET_COLLECTED.
```
Round 1 therefore **cannot** produce a verdict now — by design.

## Layout

```text
protocol/   LEVEL_0_COST_BASELINE.md  CAND-001_PROTOCOL.md  CAND-002_PROTOCOL.md  CAND-003_PROTOCOL.md
data/       DATA_SCHEMA.md  SNAPSHOT_POLICY.md  TEST_BOUNDARY.md
labels/     LABEL_DEFINITIONS.md  HORIZON_POLICY.md
cost/       COST_POLICY.md
statistics/ STATISTICAL_PLAN.md  POWER_PLAN.md  FDR_PLAN.md  BOOTSTRAP_PLAN.md
oos/        OOS_POLICY.md  PURGE_EMBARGO_POLICY.md
safety/     LOOKAHEAD_POLICY.md  INFORMATION_TIMELINE.md
comparison/ MODEL_LADDER.md  BASELINE_POLICY.md
registries/ preregistration_manifest.json  model_registry.json  parameter_registry.json
final_preregistration_report.md
SHA256SUMS
```

## What this task does NOT do

```text
no training · no backtest · no alpha discovery · no parameter or grid search · no feature mining
no MT5 connection · no data collection · no calibration · no paper/demo/forward/live
no modification of V1/V2/OpenClaw, execution, cost model, or the immutable snapshot
```

## Final state

```text
WAIT_FOR_CHATGPT_FINAL_AUDIT
```
