# LOOK-AHEAD POLICY (frozen)

`PREREGISTRATION_ID = V3-HFT-PREREG-001` · `STATUS = LOCKED`

## The single rule

> **At any decision instant `t`, a model may use only data whose timestamp is `<= t`.**

Everything computed from a later tick is `LABEL` or `DIAGNOSTIC`, never a feature.

## Mandatory verifications before any run is accepted

```text
1. AS-OF JOIN      : every feature is produced by a backward (as-of) join; no centred window,
                     no forward shift, no `.shift(-n)`, no interpolation across t.
2. SEGMENT RULE    : the label window must lie in the same valid session segment as t.
3. POST-FILL BAN   : realized markout / realized adverse selection / MFE / MAE / realized slippage
                     are DIAGNOSTIC_ONLY and must not appear in a feature matrix.
4. PURGE/EMBARGO   : applied at >= the maximum label horizon (see oos/PURGE_EMBARGO_POLICY.md).
5. TIMESTAMP UNIT  : declared (ms); unknown unit => DATA_INVALID, never inferred.
6. SELF-IMPACT     : markouts closer than MIN_MARKOUT_HORIZON_MS (500 ms) to a fill may not be used
                     as evidence of adverse selection.
```

## Automated checks (must exist in the future implementation)

```text
A. lag_assertion      : for each feature, assert max(source_ts) <= decision_ts
B. label_only_assert  : assert no label column appears in the feature matrix
C. purge_assertion    : assert max(train label end) < dev start  and  max(dev label end) < test start
D. unit_assertion     : assert the timestamp unit was explicitly supplied
E. price_shift_invariance : a cost/PnL decomposition must be invariant to shifting all prices by a
                            constant (a decomposition that changes is wrong)
```
A run that cannot demonstrate A–E is `NOT_ACCEPTED`.

## Violation handling

```text
LOOK_AHEAD_DISCOVERY  ->  HALT_AND_REPORT  ->  STOP -> DOCUMENT -> VERSION_BUMP -> RE-PREREGISTER
```
Silent repair and continuation is forbidden.

## Known traps (recorded so they are not repeated)

```text
- a mid-based label reported as if the trade filled at mid
- a fitted decay curve estimated on the same trades it times
- realized_ratio = cost / REALIZED move used as a decision input
- "minHorizon" omitted, so a fill's own impact is counted as market adverse selection
```
