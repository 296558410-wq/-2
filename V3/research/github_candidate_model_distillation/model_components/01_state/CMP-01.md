# CMP-01 — state

- source_repo: KlishevDA/...L2-Market-Making; siddhantsingh-1/execution-aware-alpha-backtester
- source_commit: HEAD_AT_AUDIT_2026-09-22
- evidence_level: **E3**
- FXTM_compatibility: COMPATIBLE (L1)
- parameters: TBD_IN_PRE_REGISTERED_EXPERIMENT

## mechanism

Point-in-time market state vector built ONLY from information available at t (as-of join, no future).

## required_data

bid, ask, mid, spread, spread percentile, rolling volatility, quote arrival, tick-rule proxy

## formula

```
state(t) = [spread_bp, spread_pctile_n, rv_n, quote_rate, flow_proxy_n, displacement_1s, displacement_5s]
```

## assumption

all terms computed with as-of (backward) joins; anything needing a future window is FORBIDDEN here

## failure_mode

look-ahead via a centred/lagged window computed with a forward shift

## FXTM note

Usable on the current FXTM L1 feed.
