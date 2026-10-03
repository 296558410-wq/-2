# MECH-013 — Detect whether your microstructure input is real before using it

- SOURCE_REPOS: A6/A1
- TRANSFERABILITY: B
- FXTM_DATA_STATUS: AVAILABLE
- STATUS: **READY**

## Mechanism

Record has_trade_flags; validate DOM non-degeneracy (constant 50/50 or +-90 jitter = unusable) before it earns weight.

## Why it matters

same conclusion reached from both the DOM and the tick side

## V3 use

Applicable on the current FXTM L1 feed.
