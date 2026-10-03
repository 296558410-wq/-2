# CMP-10 — position

- source_repo: Leotaby/Market-Making-Simulator; diegourda/Statistical-Arb-MM (A-S skew)
- source_commit: HEAD_AT_AUDIT_2026-09-22
- evidence_level: **E2**
- FXTM_compatibility: PARKED (needs fills/intensity)
- parameters: TBD_IN_PRE_REGISTERED_EXPERIMENT

## mechanism

Inventory-aware sizing/reservation price. Included for completeness; NOT usable without a fill model.

## required_data

current position, risk budget, (fill probability)

## formula

```
reservation price r = s - q*gamma*sigma^2*tau ; optimal spread delta = gamma*sigma^2*tau + (2/gamma)*ln(1+gamma/k)
```

## assumption

the A-S form assumes continuous quoting and a calibrated intensity k; FXTM has neither

## failure_mode

importing A-S quoting without an intensity calibration; treating inventory skew as edge

## FXTM note

PARKED: the required input (real queue / fill probability / intensity) is DATA_GAP on FXTM.
