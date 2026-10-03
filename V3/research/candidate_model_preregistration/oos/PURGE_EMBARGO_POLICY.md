# PURGE / EMBARGO POLICY (frozen)

`PREREGISTRATION_ID = V3-HFT-PREREG-001` · `STATUS = LOCKED`

## Values

```text
SPLIT            : chronological by UTC day; NO shuffling, NO random split
MAX_LABEL_HORIZON = 300 s (the longest registered horizon)
PURGE            >= MAX_LABEL_HORIZON        =>  300 s
EMBARGO          >= REGISTERED_EMBARGO       =>  300 s   (same value; no separate constant registered)
```

## Mechanism

```text
A TRAIN sample is removed if its forward label window reaches into the DEVELOPMENT window.
A DEVELOPMENT sample is removed if its forward label window reaches into the TEST window.
The purge is applied per horizon; the VALUE above is the upper bound used for all horizons.
```

## Why the value is the maximum horizon

```text
Overlapping labels leak information across the split. Purging at the maximum horizon is the
conservative choice and cannot be adjusted downward to increase the sample after seeing results.
```

## Immutability

```text
PURGE and EMBARGO are frozen BEFORE the first run and may not be adjusted afterwards.
Any change requires: STOP -> DOCUMENT -> VERSION_BUMP -> RE-PREREGISTER.
Adjusting purge/embargo to obtain a larger sample or a different result is a PROTOCOL_VIOLATION.
```

## Interaction with the segment rule

```text
The segment rule (labels/LABEL_DEFINITIONS.md) removes crossings of weekends/gaps/discontinuities.
Purge/embargo removes split-adjacency leakage.
Both are required; neither substitutes for the other.
```

## Reporting

```text
Report, per horizon: n_before_purge, n_purged, n_after_purge, n_censored_by_segment, n_final.
A run that does not report these counts is incomplete.
```
