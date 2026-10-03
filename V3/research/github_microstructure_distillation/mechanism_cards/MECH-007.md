# MECH-007 — Reversion-ablation maker/taker classifier

- SOURCE_REPOS: C1
- TRANSFERABILITY: B
- FXTM_DATA_STATUS: AVAILABLE
- STATUS: **READY**

## Mechanism

Drop the mean-reversion features; if IC collapses (0.473 -> 0.177), the edge belongs to the quoter, not the taker.

## Why it matters

classifies whether your signal is a taker edge at all

## V3 use

Applicable on the current FXTM L1 feed.
