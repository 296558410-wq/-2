# Trading Rule (declared BEFORE the first computation)

Task: **V3-HFT-L1-EXECUTION-EDGE-DISCOVERY-001**.
Companion to the immutable `experiment_plan.json`; it states the frozen order rule so the
plan itself never needs editing.

## Rule (frozen)

```text
target      : y = LONG EXECUTION_MARKOUT(h) in bp   (the signed forward executable return)
prediction  : pred = model(features at t)           (TRAIN fit only)
threshold   : THRESH = cost_bp(t) = round_trip_usd / mid(t) * 1e4      (NOT tuned)

position    : pos = +1   if pred >  THRESH
                    -1   if pred < -THRESH
                     0   otherwise  (no trade)

per-trade net (bp) :
    pos = +1 : net = LONG_EXECUTION_MARKOUT  - cost_bp
    pos = -1 : net = SHORT_EXECUTION_MARKOUT - cost_bp
    pos =  0 : not a trade (excluded)
```

## Why this threshold

It is the **break-even** rule implied by the canonical cost model: only trade when the predicted
executable move exceeds the cost of executing it. It is **not** optimised on VAL or TEST and is not
stressed for selection (stress is robustness only).

## Models (no deep models)

```text
naive_momentum : pos = sign(mom_3t)                      (no fit)
ridge          : linear, closed form, trained on TRAIN
logistic       : sign model on TRAIN
tree_depth3    : DecisionTree depth 3, trained on TRAIN
```

Feature standardisation uses **TRAIN statistics only**.

## Forbidden

```text
Transformer / LSTM / large MLP / RL
threshold tuning on VAL or TEST
feature reselection after cost stress
```
