# Cost Definition (frozen before computation)

Task: **V3-HFT-L1-EXECUTION-EDGE-DISCOVERY-001**.

## Canonical cost (the ONLY cost used)

```text
COST_MODEL                = CALIBRATION_20RT_20260921
ROUND_TRIP_COST_USD       = 0.40   USD per round trip
ROUND_TRIP_COST_BP        = 0.914  bp at ~4,376 USD/oz
components                = spread 0.18 USD + commission 0.22 USD
COST_SOURCE               = trader_v3/state/V3_COST_PROFILE.json + V3_EXECUTION_PROFILE.json (20 measured RTs)
COST_TIMESTAMP            = 2026-09-21T07:06:13Z
COST_ASSUMPTION           = XAUUSD 0.01 lot, FXTM demo, magic 90004
```

## Forbidden

```text
0.314 bp  = HISTORICAL_INVALID_FOR_CURRENT_RESEARCH
```
It must not enter any experiment, threshold, feature selection, markout or gate in this task.
Enforced in code by `execution/cost_model_v2.assert_not_deprecated()`.

## Cost stress (robustness only)

```text
1.00x -> 0.40 USD/RT  (0.9140 bp)   baseline
1.25x -> 0.50 USD/RT  (1.1425 bp)
1.50x -> 0.60 USD/RT  (1.3710 bp)
2.00x -> 0.80 USD/RT  (1.8280 bp)
```

Features are **not** reselected after a stress result. Stress is a robustness statement, never a
selection signal.

## Application

`NET_EDGE = EXECUTION_MARKOUT - cost_bp`, where `cost_bp` is the tier in bp at the sample's own mid:

```text
cost_bp(t) = tier_USD / mid(t) * 1e4
```

## Why EXECUTION_MARKOUT, not MID_MARKOUT

`MID_MARKOUT` ignores the fact that a taker must cross the spread on entry. Only
`EXECUTION_MARKOUT - cost` describes what a real order would have earned. Any positive
`MID_MARKOUT` with negative `NET_EDGE` is exactly the `PREDICTIVE_BUT_NOT_EXECUTABLE` case.
