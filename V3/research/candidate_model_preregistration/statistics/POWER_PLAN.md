# POWER PLAN (frozen)

`PREREGISTRATION_ID = V3-HFT-PREREG-001` · `STATUS = LOCKED`

## Source

Derived from `V3-HFT-L1-STATISTICAL-POWER-CLOSURE-001` (an a-priori power calculation, not a result
peek): required effective_N for a **+0.20 bp** net edge at **80 % power**, α = 0.05 two-sided, using the
σ measured per horizon.

## Frozen thresholds (§三十七 — do NOT choose temporarily)

```text
MINIMUM_RAW_N = 500
MINIMUM_EFFECTIVE_N (per horizon, δ = +0.20 bp, power 80 %):
    5 s   :    274
    10 s  :    494
    30 s  :  1,439
    60 s  :  2,679
    300 s : 13,069
```
These numbers are frozen **before** any experiment. They may not be lowered to obtain a result.

## Effective-N definition

```text
rho         = h / median_inter_tick_ms        (median measured 266 ms)
effective_N = n / max(1, round(rho))
METHOD A (ACF-based) and METHOD B (block-based) are both reported; if they differ by > 2x the result
carries EFFECTIVE_N_UNCERTAIN and the more conservative value is used.
```

## Consequence already known (recorded for honesty)

```text
The snapshot offers effective_N ≈ 148,226 (5 s) down to ≈ 2,220 (300 s).
=> 5 s / 10 s / 30 s / 60 s already exceed their thresholds.
=> 300 s does NOT (2,220 < 13,069)  -> the 300 s horizon will be reported as INSUFFICIENT_POWER
   unless the future test window supplies enough independent samples.
   This is a property of the data, not a licence to lower the bar.
```

## FDR interaction

With the declared family of 20 primary tests, the practical single-test α shrinks; the required N
multiplier is ≈ ×1.82 (see FDR_PLAN.md). The thresholds above are the single-test values; FDR-adjusted
requirements are reported alongside and are the binding ones for any positive claim.

## Rules

```text
1. A horizon below its threshold is INSUFFICIENT_POWER, not "no edge".
2. Thresholds are not re-derived after seeing results.
3. Trade-level sparsity is reported SEPARATELY from sample-level power: a threshold rule that produces
   few trades does not reduce sample-level power, and that distinction must be stated.
```
