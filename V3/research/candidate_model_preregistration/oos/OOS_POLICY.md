# OOS POLICY (frozen)

`PREREGISTRATION_ID = V3-HFT-PREREG-001` · `STATUS = LOCKED`

## Structure

```text
TRAIN       2026-08-04 .. 2026-08-21     fitting only
DEVELOPMENT 2026-08-24 .. 2026-09-21     selection only; CONTAINS a contaminated window
TEST        future, not yet collected    evaluation only; TEST = LOCKED
```
See `data/TEST_BOUNDARY.md`: the previously viewed 2026-09-07..09-21 window is
`DEVELOPMENT_CONTAMINATED` and may **not** serve as the evaluation set.

## Rules

```text
1. TEST is evaluated ONCE, at the end, for the registered configurations only.
2. After the TEST boundary is materialised and hashed, the following are FORBIDDEN on TEST:
      feature selection, threshold selection, model selection, horizon selection, exit tuning.
3. No parameter may be re-estimated on TEST (including lambda, thresholds and boundaries).
4. TEST_LOCKED_HASH must exist before any TEST evaluation; until then TEST_LOCKED_HASH =
   PENDING_NOT_YET_COLLECTED and no OOS claim may be made.
5. Selection uses VALIDATION (= DEVELOPMENT) only, and only from windows not already viewed.
```

## Promotion ladder (frozen, §四十五)

```text
CANDIDATE -> EXPERIMENTAL -> OOS_SUPPORTED -> EXECUTION_VALIDATED
```
Jumping from "backtest positive" straight to demo trading is forbidden. Each hop requires the
registered evidence for that hop and an explicit audit.

## What each hop requires

```text
CANDIDATE            mechanism + data + label + cost + OOS method all defined (this document)
EXPERIMENTAL         a completed, protocol-compliant run on TRAIN/DEV only, fully reported
OOS_SUPPORTED        a single evaluation on the locked TEST with FDR and power satisfied
EXECUTION_VALIDATED  execution realism confirmed independently (NOT authorised by this task)
```

## Allowed modifications (§四十二)

```text
DATA_CORRUPTION · CODE_BUG · LOOK_AHEAD_DISCOVERY · BROKER_COST_CORRECTION · SNAPSHOT_INTEGRITY_FAILURE
=> STOP -> DOCUMENT -> VERSION_BUMP -> RE-PREREGISTER      (silent repair forbidden)
```

## Explicit non-authorisation

This policy does **not** authorise running the experiment, training, backtesting, paper trading,
demo, forward or live. It defines how such a run would have to be executed if it were authorised.
