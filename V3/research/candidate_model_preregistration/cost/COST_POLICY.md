# COST POLICY (frozen)

`PREREGISTRATION_ID = V3-HFT-PREREG-001` · `STATUS = LOCKED`

## Canonical cost

```text
COST_MODEL               = CALIBRATION_20RT_20260921
ROUND_TRIP_COST_USD      = 0.40 USD per round trip
ROUND_TRIP_COST_BP       = 0.914 bp at ~4,376 USD/oz
COMPONENTS               = spread ~0.18 USD + commission ~0.22 USD
```

## Forbidden

```text
0.1375 USD   FORBIDDEN
0.314 bp     FORBIDDEN
any legacy anchor, or any cost silently re-derived from a different instrument/venue
```

## Cost tiers (frozen, §三十四)

```text
anchor         0.40 USD / RT   ( 0.914 bp )
moderate       0.50 USD / RT   ( 1.143 bp )
elevated       0.60 USD / RT   ( 1.371 bp )
high           0.80 USD / RT   ( 1.828 bp )
extreme        1.00 USD / RT   ( 2.286 bp )
```
All five must be reported for every level. Tier labels may be renamed; the **values may not change**.

## Cost application (per sample)

```text
cost_bp(t) = tier_usd / mid(t) * 1e4
NET_EDGE    = EXPECTED_GROSS_EDGE - cost_bp(t) - E[adverse_selection]
```

## The exit cost is separate and mandatory (LEVEL-3)

```text
TOTAL_COST = ENTRY_COST + EXIT_COST
EXIT_COST  = one further spread crossing + commission
```
Charging the spread once is a `PROTOCOL_VIOLATION`.

## Unmodelled components (must be named, never zeroed)

```text
IMPACT            = DATA_GAP / UNMODELED_COMPONENT   (bias: net edge overstated)
OPPORTUNITY_COST  = DATA_GAP / UNMODELED_COMPONENT   (bias: net edge overstated for unfilled size)
FILL_UNCERTAINTY  = DATA_GAP / UNMODELED_COMPONENT   (bias: assumes certainty of fills)
```

## Statement of direction

Because impact and opportunity cost are omitted (both are costs), the registered net-edge figures are
**upper bounds** on the true executable edge. Any positive result must be read under that bias.

## Sensitivity is robustness only

Cost tiers are reported as a robustness statement. Features, thresholds and models may **not** be
re-selected after a cost-stress result.
