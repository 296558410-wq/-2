# L1-Only Model Taxonomy (route A)

Question: **without real L2, is there still executable short-horizon information?**

## Inputs available on FXTM L1 (measured)

```text
AVAILABLE : bid, ask, mid, spread, quote change, tick direction, tick velocity, tick acceleration,
            short return, return reversal, spread regime, volatility, quote arrival, markout
DATA_GAP  : microprice (no sizes), TRUE_OFI (no sizes), size imbalance, queue, trade flow,
            fill probability, VPIN, Kyle-lambda, historical DOM
PARTIAL   : OFI_PROXY / FLOW_PROXY (tick-rule only - must never be called OFI)
```

## Mechanisms and their FXTM status

| mechanism | typical form | FXTM status | note |
|---|---|---|---|
| lagged return / momentum | sign of trailing return | AVAILABLE | tested in V3: gross exists, sub-cost |
| short reversal / overshoot | -sign(return), z-scored displacement | AVAILABLE | real mean reversion observed, ~1 order below cost |
| spread state | spread level / percentile | AVAILABLE | predictive of *cost*, not of direction |
| volatility state | rolling σ of returns | AVAILABLE | conditions edge magnitude, not sign |
| quote arrival / intensity | updates per second, time since quote | AVAILABLE | a liquidity/activity proxy |
| tick-rule flow proxy | Σ sign(Δmid)/w | PARTIAL | weak information proxy; not real flow |
| microprice deviation | size-weighted mid | **DATA_GAP** | FXTM sizes are synthetic |
| true OFI → return | Δ(bid·ask-size) style | **DATA_GAP** | needs real sizes |
| queue imbalance | depth-weighted | **DATA_GAP** | needs real depths |
| VPIN / Kyle-λ | volume-bucket toxicity | **DATA_GAP** | needs trade volume |

## What the evidence says about the L1 route

The V3 L1 programme already measured this route end-to-end:

```text
gross, rank-IC -0.179 @1s and -0.142 @5s   -> real short-horizon predictability EXISTS
best gross +0.096 bp vs 0.914 bp cost      -> ~9.5x too small
cost/median-move > 1 for h <= 2s           -> structurally blocked
-> PREDICTIVE_BUT_NOT_EXECUTABLE
```

Therefore the L1-only route is **not blocked by data** (it is computable) but is blocked by **cost**
at taker horizons. Its productive use is as an *input to an execution policy* (when to WAIT, when the
spread regime makes any action uneconomic), not as a standalone directional signal.

## Guardrails

```text
no *_PROXY renamed to the real quantity
no accuracy/AUC as a verdict
always net-of-cost, always OOS, always effective_N
```
