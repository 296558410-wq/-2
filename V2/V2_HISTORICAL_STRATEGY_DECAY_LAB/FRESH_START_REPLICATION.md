# FRESH_START_REPLICATION

> Source: `data/FRESH_START_REPLICATION.json`, `data/EXPERIMENTS.json` (Exp 1, 2, 14).

## Claim under test

"Newly started = stronger" — i.e. a **fresh-start advantage** that replicates across independent
systems.

## Experiment 1 — within-system fresh-start effect (early half vs late half, after cost)

| System | early mean | late mean | effect (early−late) | perm p | bootstrap CI early / late |
|---|---|---|---|---|---|
| V1_OLD | +1.84 | −2.59 | +4.43 | 0.064 | see `DECAY_ANALYSIS.json` |
| V1_NEW | −0.33 | −0.79 | +0.46 | 0.900 | — |

Neither system clears α = 0.05; V1_OLD is borderline but fails FDR. Both are **INCONCLUSIVE**.

## Experiment 2 — cross-system replication

| System | effect sign |
|---|---|
| V1_OLD (Hermes candidate) | + (early > late) |
| V1_NEW (BASELINE control arm) | + (early > late) |

Same sign → **necessary but not sufficient**. V1_NEW is a *control arm* (mechanical baseline map,
`not_hermes_alpha=true`), not an independent Hermes strategy. **Independent Hermes systems = 1.**

Verdict: **INCONCLUSIVE** (cannot claim replication from n = 1 independent system).

## Experiment 14 — placebo pseudo-start (all split points)

A real fresh-start effect must beat the best random split, not just the median split.

| System | observed early−late | p(any split) |
|---|---|---|
| V1_OLD | +4.43 | 0.187 |
| V1_NEW | +0.46 | 0.967 |

V1_OLD's observed split is **not** extreme relative to random splits (p = 0.19) → the "fresh start"
reading of its early profit is **not distinguishable from noise**.

## Verdict

`FRESH_START_EFFECT = INCONCLUSIVE`. `CROSS_SYSTEM_REPLICATION = NOT_ESTABLISHED`.
The "newly started = stronger" hypothesis is **not supported** by the real-trade evidence.
