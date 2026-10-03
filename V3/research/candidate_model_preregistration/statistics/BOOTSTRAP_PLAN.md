# BOOTSTRAP PLAN (frozen)

`PREREGISTRATION_ID = V3-HFT-PREREG-001` · `STATUS = LOCKED`

## Method

```text
TYPE            : moving block bootstrap on the NON-OVERLAPPING series
RESAMPLES       : 2000
BLOCK LENGTH    : max(50, round(10 * rho))        rho = h / median_inter_tick_ms
CI              : percentile [2.5, 97.5]
SEED            : 20260922 (fixed; a different seed is a different experiment)
SERIES          : the non-overlapping net-edge series (every round(rho)-th observation)
```

## Why blocking (not iid)

```text
Short-horizon returns are dependent; an iid bootstrap understates the CI.
The block length is derived from the measured dependence, not chosen freely.
```

## Required outputs per (level, horizon)

```text
mean, median, std, p10, p25, p75, p90
bootstrap mean, CI low, CI high, n_eff, block length
```

## Adjacent uncertainty requirements

```text
CLUSTERED EVENTS : when decisions cluster, no CI may be implied from the raw count.
HAC / overlap    : where overlap remains after de-overlapping, an overlap-aware correction is applied.
MULTIPLE SERIES  : intervals from different horizons are NOT independent; they are reported as a
                   family and read together, not cherry-picked.
```

## Interpretation rules (fixed in advance)

```text
A CI that includes 0 is NOT evidence of an edge.
A point estimate without its CI may not be quoted as a finding.
A CI computed on fewer than the registered minimum effective_N is labelled INSUFFICIENT_POWER.
```
