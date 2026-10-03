# Power Plan (FROZEN before computation)

Task **V3-HFT-L1-STATISTICAL-POWER-CLOSURE-001** — `AUDIT_ONLY / READ_ONLY / OFFLINE`.
Machine twin: `power_plan.json` (hashed; immutable). No alpha search, no model search, no feature mining.

## Question

For the real FXTM L1 snapshot, **how much data does each horizon (5 s–5 min) need** so that a
future independent alpha replication reaches the pre-registered power?

## Frozen parameters

```text
horizons            : 5s, 10s, 30s, 60s, 5min          (50ms/200ms/1s/2s are COST_BLOCKED, out of scope)
alpha               : 0.05 two-sided
power targets       : 80%, 90%, 95%
effect sizes (net)  : +0.10, +0.20, +0.30, +0.50, +1.00 bp   <-- PREDEFINED hypothesis only
cost                : 0.914 bp / 0.40 USD RT (CALIBRATION_20RT_20260921); 0.314bp forbidden
N definitions       : raw_N, eligible_N, label_valid_N, non_overlapping_N, effective_N, INDEPENDENT_EVENT_N
method A            : ACF-based effective_N
method B            : block-based effective_N (independent blocks)
block length        : estimated once from the data, then FROZEN (no per-horizon cherry-picking)
simulation          : block bootstrap on the EMPIRICAL non-overlapping net series (not normal)
multiple testing    : BH-FDR q=0.05 (per-horizon and the inherited 140-test family)
metric of interest  : `effective_N` (never raw ticks)
stop at             : WAIT_FOR_CHATGPT_FINAL_AUDIT
```

## Two guardrails carried forward

```text
LABEL_GAP_GUARD_BUG = FIXED_IN_PREVIOUS_TASK
MECHANICAL_SIGNAL   = REJECTED
TAIL_DEPENDENCE     = OBSERVED
```

* The observed positive means (e.g. +7.99 bp @30 s) are **never** used as an effect size (§二十六).
* `effective_N >= 500` is treated as a *minimum operational gate*, and the report states whether it
  is statistically adequate (§二十四) — it is **not** assumed to be.

## Decision vocabulary

```text
A POWER_CLOSED                          need is known and a reasonable collection horizon suffices
B POWER_NOT_YET_CLOSED                  more real FXTM L1 data is required
C POWER_NOT_ECONOMICALLY_REACHABLE      the data/time cost is disproportionate to the research value
D POWER_STRUCTUREALLY_LIMITED           overlap/dependence make effective_N grow far too slowly
```
