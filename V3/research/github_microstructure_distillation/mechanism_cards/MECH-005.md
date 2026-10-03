# MECH-005 — Perold 4-term implementation shortfall incl. Opportunity on the UNFILLED fraction

- SOURCE_REPOS: C6/C8
- TRANSFERABILITY: B
- FXTM_DATA_STATUS: PARTIAL (fills!)
- STATUS: **READY**

## Mechanism

IS = Spread + Impact + Fee + Opportunity, where Opportunity = max(0, adverse post-window drift) * UNFILLED fraction.

## Why it matters

retail backtests silently book unfilled size at par (opportunity cost = 0)

## V3 use

Applicable on the current FXTM L1 feed.
