# MECH-011 — Intensity calibration + overfit ratio

- SOURCE_REPOS: B2
- TRANSFERABILITY: C
- FXTM_DATA_STATUS: DATA_GAP (needs fills)
- STATUS: **PARKED**

## Mechanism

Fit log(fillRate) = logA - k*spread by OLS; gate every parameter set on OOS_Sharpe / IS_Sharpe.

## Why it matters

turns a free parameter into a measured one; flags overfitting

## V3 use

PARKED: the required input is DATA_GAP on FXTM (no real L2 queue / no fills), so the mechanism cannot be tested here.
