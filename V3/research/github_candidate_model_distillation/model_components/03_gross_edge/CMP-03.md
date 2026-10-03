# CMP-03 — gross_edge

- source_repo: snowkings/QIP_adverse_selection; siddhantsingh-1/...
- source_commit: HEAD_AT_AUDIT_2026-09-22
- evidence_level: **E4**
- FXTM_compatibility: COMPATIBLE (L1)
- parameters: TBD_IN_PRE_REGISTERED_EXPERIMENT

## mechanism

Expected GROSS markout per horizon, measured mid-to-mid, never mixed with cost.

## required_data

mid series + decision instants

## formula

```
gross_edge(t,h) = E[ d * (mid(t+h) - mid(t)) ] ; signed midpoint movement, three-way (favourable/unchanged/adverse)
```

## assumption

mid-based labels avoid bid-ask bounce inflation; forward windows must be segment-guarded

## failure_mode

mid label used as if it were an executable price (ignores the spread you must cross)

## FXTM note

Usable on the current FXTM L1 feed.
