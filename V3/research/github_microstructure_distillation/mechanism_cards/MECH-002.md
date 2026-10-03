# MECH-002 — Adaptive tick-window lookback

- SOURCE_REPOS: A1
- TRANSFERABILITY: B
- FXTM_DATA_STATUS: AVAILABLE
- STATUS: **READY**

## Mechanism

Start at 30 ticks and EXPAND the window until it spans >= 1 second (cap 250) before computing velocity/acceleration.

## Why it matters

fixes velocity maths that collapse when gold prints 100+ ticks/s at the NY open

## V3 use

Applicable on the current FXTM L1 feed.
