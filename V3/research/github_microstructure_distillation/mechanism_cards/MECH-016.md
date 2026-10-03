# MECH-016 — Avoid paying the spread twice: limit exit at the statistical mean

- SOURCE_REPOS: A4
- TRANSFERABILITY: B
- FXTM_DATA_STATUS: AVAILABLE
- STATUS: **READY**

## Mechanism

Enter on the closed bar, exit with a server-side limit at the target so the exit does not cross the spread.

## Why it matters

market-order exits pay the spread on both legs

## V3 use

Applicable on the current FXTM L1 feed.
