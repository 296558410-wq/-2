# MECH-009 — Markout methodology (signed, multi-horizon, with equity)

- SOURCE_REPOS: B1/B4
- TRANSFERABILITY: B
- FXTM_DATA_STATUS: PARTIAL (L1-based)
- STATUS: **READY**

## Mechanism

Per fill: sell -> p - m(t+h); buy -> m(t+h) - p; report markout alongside equity and inventory, never instead.

## Why it matters

equity can look fine while markout is negative (hidden toxicity)

## V3 use

Applicable on the current FXTM L1 feed.
