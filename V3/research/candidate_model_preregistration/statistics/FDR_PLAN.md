# FDR PLAN (frozen)

`PREREGISTRATION_ID = V3-HFT-PREREG-001` · `STATUS = LOCKED`

## Declared family (fixed NOW, before any result)

```text
PRIMARY FAMILY (m = 20):
    4 levels  x  5 primary horizons  =  20 tests
    levels   : LEVEL-0, LEVEL-1, LEVEL-2, LEVEL-3
    horizons : 5 s, 10 s, 30 s, 60 s, 300 s
EXPLORATORY FAMILY (declared, reported separately, never promoted):
    secondary threshold variant (1), reference-only horizons (2), regime slices (<= 3)
    -> these are counted and reported but are NOT part of the confirmatory family
METHOD : Benjamini-Hochberg
Q      : 0.05
```

## Hard rules

```text
1. The family is defined BEFORE looking at any result.
   ("look at which results are significant, then decide the family" is FORBIDDEN.)
2. Exploratory results can never be upgraded to primary findings.
3. Reference-only horizons (1 s, 2 s) are outside the confirmatory family.
4. An exploratory result must be re-registered as a new experiment before it can be claimed.
```

## Practical consequence

```text
With m = 20, the practical single-test alpha is q/m. The required effective_N multiplier versus the
single-test requirement is approximately x1.82 (computed in the power closure task).
=> the binding power requirement for any POSITIVE claim is the FDR-adjusted one.
```

## Required reporting (separate counts, never merged)

```text
total_tests | valid_tests | insufficient_tests | significant_tests
```
`insufficient != failed`. The correct form is e.g.
"0/12 valid tests survived BH-FDR; 8/20 were statistically insufficient" —
**not** "0/20 alpha".

## Multiplicity beyond FDR

```text
- overlap corrections must be applied before p-values enter the family
- the same statistic must not enter the family twice under different names
- if a sub-analysis is added later, it enters the EXPLORATORY family and is reported as such
```
