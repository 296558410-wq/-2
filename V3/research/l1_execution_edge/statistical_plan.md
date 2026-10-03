# Statistical Plan (frozen before computation)

Task: **V3-HFT-L1-EXECUTION-EDGE-DISCOVERY-001**.

## 1. Splits

```text
TRAIN 2026-08-04..2026-08-21 | VAL 2026-08-24..2026-09-04 | TEST 2026-09-07..2026-09-21
chronological by UTC day; NO random/shuffle split
purge == embargo == horizon h
```

Selection (family/model/threshold) happens on **VALIDATION only**. TEST is evaluated **once**, at the
end, for the selected configurations only.

## 2. Overlap

`rho(h) = h / median_inter_tick_ms`; `effective_n(h) = n // max(1, round(rho))`.
Ordinary iid t-tests are **forbidden as the only evidence**; a **moving block bootstrap** is required.

## 3. Tests

```text
primary   : two-sided t-test on NON-OVERLAPPING net edges
secondary : moving block bootstrap, 2000 resamples, block = max(50, int(10*rho)), CI = [2.5, 97.5]
```

## 4. Mean vs Median (mandatory)

`mean > 0` alone is **never** alpha. Report `mean, median, std, p10, p25, p75, p90` and the
`top 1% / 5% / 10%` contributions to total net PnL. If the edge is concentrated in the extreme tail:

```text
TAIL_DEPENDENT = TRUE
```

## 5. Multiple testing

Benjamini-Hochberg, `q <= 0.05`, over the full screen family
(`feature_family x horizon x model`). Reporting **must** separate:

```text
total_tests | valid_tests | insufficient_tests | significant_tests
```

`insufficient != failed`. The pattern "0/8 valid survived FDR, 22/30 statistically insufficient" is
the correct way to report; `0/30 alpha` is forbidden phrasing.
A test whose `effective_n < 500` is `DATA_INSUFFICIENT`, not a failure.

## 6. Regimes (after the main experiment only)

At most 3 dimensions x 3 states (spread, volatility, quote arrival), each requiring `N >= 500`,
otherwise `INSUFFICIENT_SAMPLE`. No combinatorial regime mining.

## 7. Acceptance (all ten required for SUPPORTED_EXECUTABLE_EDGE)

gross > 0 · net > 0 · OOS net > 0 · bootstrap CI not entirely < 0 · FDR q <= 0.05 ·
effective_N >= 500 · not tail-only · survives 1.25x cost · no future data · direction consistent.

## 8. Partial outcomes

```text
gross>0 net<0            -> PREDICTIVE_BUT_NOT_EXECUTABLE
net>0 OOS<0              -> IN_SAMPLE_ONLY
net>0 OOS>0 q>0.05       -> STATISTICALLY_UNCONFIRMED
median<0 mean>0 tail     -> TAIL_DEPENDENT
effective_N < 500        -> DATA_INSUFFICIENT
none of the above        -> NO_SUPPORTED_L1_EDGE
```
