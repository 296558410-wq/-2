# MECH-015 — Init-time invariants, slippage abort, virtual-stop persistence, magic isolation

- SOURCE_REPOS: A2
- TRANSFERABILITY: B
- FXTM_DATA_STATUS: AVAILABLE
- STATUS: **READY**

## Mechanism

Refuse to load on illegal parameter combinations; abort a fill worse than N pips; persist virtual SL/TP; scope every position scan by magic+symbol.

## Why it matters

cheap, machine-checkable safety that killed a whole EA generation

## V3 use

Applicable on the current FXTM L1 feed.
