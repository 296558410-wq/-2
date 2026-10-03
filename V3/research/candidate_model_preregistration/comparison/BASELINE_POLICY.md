# BASELINE POLICY (frozen)

`PREREGISTRATION_ID = V3-HFT-PREREG-001` · `STATUS = LOCKED`

## Purpose

> Prove that a candidate does not manufacture a surface advantage out of complexity.

Every level is compared against simple controls on the **same instants, same horizons, same cost
tiers, same segments**.

## Registered baselines (per level)

| baseline | LEVEL-0 | LEVEL-1 | LEVEL-2 | LEVEL-3 |
|---|---:|---:|---:|---:|
| `NO_SIGNAL` (always WAIT) | — | ✓ | ✓ | ✓ |
| `COST_ONLY` (the LEVEL-0 map) | — | ✓ | ✓ | ✓ |
| `MOMENTUM_BASELINE` (sign of trailing 1 s return) | — | — | ✓ | ✓ |
| `RANDOMIZED_CONTROL` (seeded 20260922, same TAKE rate) | — | ✓ | ✓ | ✓ |
| `FIXED_EXIT` (no conditional exit) | — | — | — | ✓ |

## Rules

```text
1. The baseline set is frozen here; no baseline may be added after seeing results
   (adding a weak baseline to look better is a PROTOCOL_VIOLATION).
2. RANDOMIZED_CONTROL uses the fixed seed 20260922 and matches the candidate's decision rate, so the
   comparison is not confounded by trade frequency.
3. A candidate that does not beat COST_ONLY and RANDOMIZED_CONTROL is reported as not beating them.
4. For LEVEL-3 the binding baseline is FIXED_EXIT on the SAME entries (same-entry comparison).
5. Baselines are reported with the same metric set as the candidates (statistics/STATISTICAL_PLAN.md).
```

## What "beating a baseline" means (frozen)

```text
PRIMARY comparison metric  : NET_EDGE_PER_TRADE (after the full cost chain)
SECONDARY                  : COST_COVERAGE, MAX_DRAWDOWN, TURNOVER, TRADE_COUNT
NOT sufficient alone       : win rate, profit factor, gross return
```
A candidate "beats" a baseline only if the primary metric improves while the secondary metrics do not
deteriorate materially, and the improvement survives the bootstrap CI and FDR correction.
