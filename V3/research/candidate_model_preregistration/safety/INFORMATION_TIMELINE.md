# INFORMATION TIMELINE (frozen)

`PREREGISTRATION_ID = V3-HFT-PREREG-001` · `STATUS = LOCKED`

## The timeline at a decision instant T0

```text
T0
 |
 +-- available L1 : bid, ask, mid, spread, spread history, quote arrival, returns, volatility   AVAILABLE
 |
 +-- model state                                                                                 AVAILABLE
 |
 +-- decision (TAKE / WAIT / EXIT)                                                                AVAILABLE
 |
 +-- execution (modelled; L ~ 279 ms measured RTT)
 |
 +-- T+100 ms   mid, markout                                                                    LABEL_ONLY
 +-- T+250 ms                                                                                   LABEL_ONLY
 +-- T+500 ms   (first horizon usable for adverse-selection evidence)                          LABEL_ONLY
 +-- T+1 s                                                                                      LABEL_ONLY
 +-- T+2 s                                                                                      LABEL_ONLY
 +-- T+5 s                                                                                      LABEL_ONLY
 +-- T+30 s                                                                                     LABEL_ONLY
```
**No future node may flow back to T0.** At a later decision instant `Tk`, the same diagram applies with
`Tk` as the origin (only ticks with `ts <= Tk`).

## What may be seen, when (§五十九)

| information | TRAIN | DEV | TEST |
|---|---:|---:|---:|
| feature distributions | yes | yes | locked |
| parameter estimation | yes | yes | **no** |
| threshold choice | yes | yes | **no** |
| model selection | yes | yes | **no** |
| horizon selection | yes | yes | **no** |
| final performance | **no** | **no** | yes |
| post-hoc / diagnostic analysis | **no** | **no** | yes |

## Field classification (frozen)

```text
PREDICTIVE   : the registered feature list (see data/DATA_SCHEMA.md)
LABEL        : future_markout, execution_markout, cost_adjusted_markout
DIAGNOSTIC   : post-fill markout, realized adverse selection, realized slippage, class attribution
```

## Hermes boundary (§五十四)

In any future authorised experiment, Hermes may receive **only T0-or-earlier** fields:

```text
timestamp, model_id, state, gross_edge, expected_cost, expected_adverse_selection, net_edge,
uncertainty, decision, reason_codes
```
Hermes must **never** receive `future markout`, `future PnL`, `future MFE`, `future MAE`.
