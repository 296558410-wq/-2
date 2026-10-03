# CMP-07 — entry_gate

- source_repo: siddhantsingh-1 (cost hurdle, E4); n30dyn4m1c/gold-pro-scalper (cost-multiple gate, E1 corroboration)
- source_commit: HEAD_AT_AUDIT_2026-09-22
- evidence_level: **E4**
- FXTM_compatibility: COMPATIBLE
- parameters: TBD_IN_PRE_REGISTERED_EXPERIMENT

## mechanism

Compare expected edge against the full cost BEFORE trading; abstain when the inequality fails.

## required_data

expected gross edge, full cost, uncertainty band

## formula

```
TAKE iff E[net_edge] - uncertainty_margin > 0 ; cost-multiple variant: edge_fuel >= k1 * RT_cost and target >= k2 * RT_cost
```

## assumption

the gate is a comparison, not a fitted classifier; k1/k2 are NOT set here

## failure_mode

lowering the gate to increase fill rate (destroys the economics)

## FXTM note

Usable on the current FXTM L1 feed.
