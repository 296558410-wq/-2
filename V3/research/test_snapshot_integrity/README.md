# TEST Snapshot Integrity — V3-HFT-TEST-SNAPSHOT-INTEGRITY-001

`TEST-SETUP-ONLY / READ_ONLY / NO-EXPERIMENT`

This task does **not** look for alpha. It establishes whether the future evaluation set is clean,
complete, reproducible and consistent with the frozen preregistration.

```text
TEST_READY         = NO
TEST_CONTAMINATION = NO (nothing exists after the boundary yet)
TEST_BOUNDARY      = RULE_LOCKED ; TEST_LOCKED_HASH = PENDING_NOT_YET_COLLECTED
TEST_SNAPSHOT      = NOT_CREATED (creating one now would fabricate an evaluation set)
PREREGISTRATION_HASH = MATCH
```

## Why NO

```text
TEST_START           = 2026-09-22T06:20:00Z
UTC at verification  = 2026-09-22 06:13:30.592109+00:00
events after TEST_START = 0
=> the TEST window is 6.5 minutes in the FUTURE; no data exists.
```
Per the task's own discipline, the correct action is **WAIT** — not padding to 10 sessions, not
shifting the start, not using older data, not choosing easier sessions, not editing the preregistration.

## Contents

```text
manifest/TEST_MANIFEST.json  TEST_FILE_MANIFEST.json  TEST_SNAPSHOT_MANIFEST.json
audit/ CONTAMINATION_AUDIT.md  SCHEMA_AUDIT.md  TIMESTAMP_AUDIT.md  DUPLICATE_AUDIT.md
       GAP_AUDIT.md  SESSION_AUDIT.md  PREREGISTRATION_MATCH.md
registry/ source_registry.json  session_registry.json
final_test_snapshot_report.md   verification.json   SHA256SUMS
```

## What this task did NOT do

```text
no alpha discovery · no backtest · no training · no parameter/feature/horizon/threshold selection
no exit optimisation · no CAND-001/002/003 experiment · no LEVEL-0..3 performance computation
no future label generation · no PnL/Sharpe/PF/WR analysis · no spread-distribution analysis
no MT5 order · no calibration · no forward · no live
```
