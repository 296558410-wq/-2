# CMP-09 — uncertainty

- source_repo: snowkings (no CI on clustered events); himagna16 (cluster-robust); Trumplus (per-day AUC, eligibility)
- source_commit: HEAD_AT_AUDIT_2026-09-22
- evidence_level: **E4**
- FXTM_compatibility: COMPATIBLE
- parameters: TBD_IN_PRE_REGISTERED_EXPERIMENT

## mechanism

Every edge estimate carries edge/execution/data uncertainty; overlapping events must not be treated as independent.

## required_data

bootstrap machinery, cluster labels, effective_N

## formula

```
report edge_uncertainty (CI), execution_uncertainty (fill/cost band), data_uncertainty (DATA_GAP list); effective_N = n / max(1,rho)
```

## assumption

no CI is implied from the raw event count when events cluster; unobservable outcomes are excluded, never 0

## failure_mode

quoting a t-stat from overlapping events; reporting a mean without the median/tail

## FXTM note

Usable on the current FXTM L1 feed.
