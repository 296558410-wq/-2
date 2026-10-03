# MECH-010 — FIFO qty_in_front + cancel model + size-aware fill label

- SOURCE_REPOS: B3/B5
- TRANSFERABILITY: C
- FXTM_DATA_STATUS: DATA_GAP (no real queue on FXTM)
- STATUS: **PARKED**

## Mechanism

queue_ahead tracked per order; label 'filled' iff cumulative volume at/through price >= queue_ahead + order_size.

## Why it matters

the correct passive-fill formulation

## V3 use

PARKED: the required input is DATA_GAP on FXTM (no real L2 queue / no fills), so the mechanism cannot be tested here.
