# DATA SCHEMA (frozen)

`PREREGISTRATION_ID = V3-HFT-PREREG-001` · `STATUS = LOCKED`

## Available fields (FXTM L1, measured)

```text
bid, ask                        AVAILABLE   real quotes
ts_utc                          AVAILABLE   datetime64[ms, UTC]  (unit DECLARED = ms, never inferred)
mid = (bid+ask)/2               AVAILABLE   derived, exact
spread = ask - bid              AVAILABLE   derived, exact
spread_bp = spread/mid*1e4      AVAILABLE   derived, exact
quote arrival / time since quote AVAILABLE  derived from the tick stream
recent return / volatility      AVAILABLE   derived (backward windows only)
```

## DATA_GAP fields (must never be proxied, renamed or filled)

```text
TRUE_OFI            = DATA_GAP     (no bid/ask sizes)
TRUE_TRADE_FLOW     = DATA_GAP     (volume / volume_real / last identically 0)
QUEUE               = DATA_GAP     (no real FIFO book)
HISTORICAL_L2       = DATA_GAP     (no historical DOM)
FILL_PROBABILITY    = DATA_GAP     (no queue / order-level data)
L2_DEPTH            = DATA_GAP     (realtime DOM exists but is SYNTHETIC_OR_AGGREGATED)
IMPACT              = DATA_GAP     (no depth/size model)
OPPORTUNITY_COST    = DATA_GAP     (no fill/participation model)
```

## Hard rules

```text
1. A DATA_GAP field may NEVER be renamed to its real name (no microprice from mid, no OFI from
   tick-rule without the _PROXY suffix).
2. A DATA_GAP term may NEVER be written as 0. Required: DATA_GAP / UNMODELED_COMPONENT + a stated
   bias direction.
3. Timestamps enter research only through the declared-unit guard (ms); an unknown unit => DATA_INVALID.
4. Only the immutable snapshot may be read; the live feed may not be read by any experiment.
5. Every field used by a model must be labelled PREDICTIVE / DIAGNOSTIC / LABEL in the model schema.
```

## FEATURE SCHEMA (frozen list)

```text
PREDICTIVE  : spread_bp, spread_change_200t, quote_arrival_1s, recent_return_1s,
              recent_volatility_50t, mid_return_1s, displacement_5s, mom_3t, mom_10t,
              rev_5t, overshoot_z, rv_50t, absret_10t, tick_rule_proxy_20t, tick_rule_proxy_50t
LABEL       : future_markout, execution_markout, cost_adjusted_markout, realized_pnl(after fill)
DIAGNOSTIC  : post-fill markout, realized adverse selection, realized slippage, class attribution
NOT_USABLE  : every DATA_GAP field above
```
`FEATURE_SCHEMA_HASH` is recorded in `registries/preregistration_manifest.json`.
