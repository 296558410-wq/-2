# SNAPSHOT POLICY (frozen)

`PREREGISTRATION_ID = V3-HFT-PREREG-001` · `STATUS = LOCKED`

```text
SNAPSHOT_ID           = V3-SNAP-20260922T025312Z
DATA_MANIFEST_SHA256  = a036a808d5d924a7a99c5941919971ff00ce9e28c804e8e91860b6ffd7fa61b5
FILE_COUNT            = 36            (24 staging + 12 live)
TOTAL_ROWS            = 7,285,000
TS_MIN                = 2026-08-04T01:05:00.093Z
TS_MAX                = 2026-09-22T02:39:05.572Z
TIMEZONE              = UTC
TIMESTAMP_UNIT        = ms (declared)
```

## Rules

```text
1. RESEARCH READS THE SNAPSHOT ONLY. live_fxtm is not a research input.
2. The snapshot is immutable: copy-on-cut + read-only attribute + per-file sha256.
3. A change to any snapshot file's sha256 => SNAPSHOT_INTEGRITY_FAILURE => HALT_AND_REPORT.
4. All experiment artifacts must record DATA_SNAPSHOT_ID and DATA_MANIFEST_SHA256.
5. Data collection continues for the FUTURE test window (see data/TEST_BOUNDARY.md); the collected
   data will form a NEW snapshot with its own manifest hash, which must be registered before use.
```

## Snapshot role under this preregistration

```text
TRAIN       2026-08-04 .. 2026-08-21   (snapshot)
DEVELOPMENT 2026-08-24 .. 2026-09-21   (snapshot; includes the CONTAMINATED window - see TEST_BOUNDARY)
TEST        future, not yet collected  (LOCKED rule; LOCKED hash pending)
```

## Forbidden

```text
- re-using the already-viewed 2026-09-07..09-21 window as the evaluation set
- silently swapping the snapshot after a partial run
- mixing the live feed into a research pipeline
```
