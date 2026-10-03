# CMP-02 — signal

- source_repo: siddhantsingh-1/execution-aware-alpha-backtester (OFI+microprice); V3 L1 subset
- source_commit: HEAD_AT_AUDIT_2026-09-22
- evidence_level: **E4**
- FXTM_compatibility: PARTIAL (drop OFI/microprice terms)
- parameters: TBD_IN_PRE_REGISTERED_EXPERIMENT

## mechanism

Directional signal that maps the state to an expected signed move. MUST NOT use post-fill quantities.

## required_data

state vector only (no OFI/microprice on FXTM -> substitute L1 return/reversal terms)

## formula

```
signal(t) = g(state(t)) ; on FXTM g may not use true OFI, microprice, queue or trade flow
```

## assumption

the strongest published L1 signals rely on OFI/microprice; on FXTM those are DATA_GAP, so the signal is degraded

## failure_mode

reusing a post-fill markout as a feature (leakage); renaming a proxy to the real quantity

## FXTM note

Usable only in degraded form; the published inputs include DATA_GAP quantities on FXTM.
