# SCHEMA AUDIT (freeze-002)

`generated_utc = 2026-09-22T06:25:00Z`

```text
columns (live feed) : bid, ask, ts_utc   (plus flags/volume fields that are identically zero)
types              : float64, float64, datetime64[ms, UTC]
timestamp unit     : ms — PROVEN_BY_VALUE
                     proof: interpreting the raw integers as ms yields a 2026 date;
                            us/ns would imply 1970 => ms is PROVEN BY VALUE, not guessed
timezone           : UTC
FEATURE_SCHEMA     : LOCKED (unchanged) — no feature added/removed/renamed/re-semanticised
DATA_CAPABILITY    : NOT UPGRADED (§37) — a live realtime DOM does NOT make HISTORICAL_L2 available
   TRUE_OFI = DATA_GAP · TRADE_FLOW = DATA_GAP · QUEUE = DATA_GAP
   HISTORICAL_L2 = DATA_GAP · FILL_PROBABILITY = DATA_GAP
TEST rows          : 0 (schema divergence not assessable yet)
```
