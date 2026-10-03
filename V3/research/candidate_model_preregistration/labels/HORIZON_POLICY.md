# HORIZON POLICY (frozen)

`PREREGISTRATION_ID = V3-HFT-PREREG-001` · `STATUS = LOCKED`

## Registered horizons

```text
PRIMARY        : 5 s (5000 ms), 10 s, 30 s, 60 s, 300 s
REFERENCE_ONLY : 1 s (1000 ms), 2 s (2000 ms)
FORBIDDEN      : 50 ms, 200 ms
```

## Reasons (recorded, not negotiable)

```text
50 / 200 ms  DATA_INSUFFICIENT  (feed resolution 266 ms median inter-tick > 2x50 ms; clean fraction low)
1 s / 2 s    COST_BLOCKED       (cost / median-move > 1)  -> reference only, excluded from selection
5 s .. 300 s RESEARCHABLE       (cost / median-move < 1)  -> the registered test set
```

## Rules

```text
1. ALL FIVE primary horizons must be reported in full. Reporting one horizon only is a
   PROTOCOL_VIOLATION.
2. No horizon may be selected after seeing results.
   (The known failure pattern "results -> notice 30 s looks best -> test only 30 s" is forbidden.)
3. REFERENCE_ONLY horizons appear in every table for continuity but may never enter selection,
   promotion or a conclusion.
4. A horizon that fails its power requirement is reported as INSUFFICIENT_POWER for THAT horizon;
   the others are still reported.
5. The horizon set may not be extended after the test boundary opens.
```

## Per-horizon power requirement (from the frozen power plan)

Reported against `statistics/POWER_PLAN.md`; a horizon below its threshold yields `INSUFFICIENT_POWER`
rather than being dropped silently.

## Horizon-specific analytical notes

```text
5 s / 10 s : shortest registered horizons; the exit-cost and self-impact rules bind hardest here
30 s       : the PRE-CHOSEN primary discrimination horizon for LEVEL-1 (not chosen from results)
60 s       : intermediate
300 s      : longest; fewest independent samples; the power requirement is the most demanding
```
