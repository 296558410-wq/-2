# CMP-05 — adverse_selection

- source_repo: Leotaby/Market-Making-Simulator (convention); snowkings/QIP_adverse_selection (measurement)
- source_commit: HEAD_AT_AUDIT_2026-09-22
- evidence_level: **E4**
- FXTM_compatibility: PARTIAL (L1 diagnostic only)
- parameters: TBD_IN_PRE_REGISTERED_EXPERIMENT

## mechanism

Post-fill adverse drift measured as a three-way classification; diagnostic only, never an entry feature.

## required_data

entry execution price + future mid

## formula

```
AS_h = entry_exec_price - mid(t+h) for LONG ; mid(t+h) - entry_exec_price for SHORT ; AS>0 = adverse
```

## assumption

measured, never injected; at FXTM only L1 markout is available (queue-based AS is DATA_GAP)

## failure_mode

circularity (injecting the adverse move then measuring it); using realised AS inside the entry decision

## FXTM note

Usable only in degraded form; the published inputs include DATA_GAP quantities on FXTM.
