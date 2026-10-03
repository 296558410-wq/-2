# CMP-06 — execution

- source_repo: tfrmma/realistic-mm-backtester; AshJha0/electronic-trading (latency accounting)
- source_commit: HEAD_AT_AUDIT_2026-09-22
- evidence_level: **E3**
- FXTM_compatibility: PARTIAL (taker only; passive PARKED)
- parameters: TBD_IN_PRE_REGISTERED_EXPERIMENT

## mechanism

Execution model: taker crosses the spread at t+latency; exit cost is a SECOND spread crossing.

## required_data

bid, ask, measured latency (FXTM RTT ~279 ms)

## formula

```
fill_price = ask(t+L) for market BUY ; bid(t+L) for market SELL ; exit adds one more spread + commission
```

## assumption

fill is ASSUMED for market orders (no fill model); passive fill is DATA_GAP on FXTM

## failure_mode

assuming mid fills; counting the spread once instead of twice

## FXTM note

Usable only in degraded form; the published inputs include DATA_GAP quantities on FXTM.
