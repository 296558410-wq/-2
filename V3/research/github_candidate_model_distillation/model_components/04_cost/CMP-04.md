# CMP-04 — cost

- source_repo: gelatotrade/implementation-shortfall-hyperliquid; AshJha0/electronic-trading
- source_commit: HEAD_AT_AUDIT_2026-09-22
- evidence_level: **E3**
- FXTM_compatibility: COMPATIBLE (0.914 bp measured)
- parameters: TBD_IN_PRE_REGISTERED_EXPERIMENT

## mechanism

Explicit additive cost decomposition with declared signs; includes the opportunity term on the UNFILLED fraction.

## required_data

spread, commission, (impact), delivered fraction

## formula

```
IS_total = Spread + Impact + Fee + Opportunity ; Opportunity = max(0, adverse post-window drift) * UNFILLED fraction
```

## assumption

each term separately visible; positive = cost; a term that is unknown is DATA_GAP, never 0

## failure_mode

silently booking unfilled size at the arrival price (opportunity cost = 0); netting costs invisibly

## FXTM note

Usable on the current FXTM L1 feed.
