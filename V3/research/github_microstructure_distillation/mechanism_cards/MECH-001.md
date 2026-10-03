# MECH-001 — Cost-multiple entry gate

- SOURCE_REPOS: A4
- TRANSFERABILITY: B
- FXTM_DATA_STATUS: AVAILABLE (spread+commission known)
- STATUS: **READY**

## Mechanism

Take a trade only if StdDev(fuel) >= k1 * roundTripCost AND distanceToTarget >= k2 * roundTripCost (k1=3,k2=4).

## Why it matters

makes marginal trades unprofitable by construction

## V3 use

Applicable on the current FXTM L1 feed.
