# MODEL LADDER (frozen)

`PREREGISTRATION_ID = V3-HFT-PREREG-001`

## The ladder (increasing complexity; each rung must justify itself)

```text
LEVEL-0   COST-ONLY BASELINE                     cost_to_move map; no predictor
LEVEL-1   CAND-002  Spread-State Execution        economic gate only; no direction
LEVEL-2   CAND-001  Execution-Aware L1 Markout Gate  directional, cost-aware
LEVEL-3   CAND-003  Adverse-Selection Conditional Exit  exit rule on top of an entry
```

## The incremental-information requirement

> **Every rung must demonstrate that it adds information relative to the rung below it, on the same
> instants, same data, same cost tiers.**

```text
LEVEL-1 vs LEVEL-0 : does the spread/cost STATE discriminate realised cost_to_move beyond the plain map?
LEVEL-2 vs LEVEL-1 : does the directional gate add NET edge beyond the LEVEL-1 filter alone?
LEVEL-3 vs LEVEL-2 : does the conditional exit improve the SAME ENTRIES (same-entry comparison)?
```
A rung that cannot show this is reported as "no incremental information" — it is **not** re-labelled,
and it does not license the next rung.

## Round-1 rules (§四十九)

```text
ONE MODEL AT A TIME. No combination optimisation in round 1.
FORBIDDEN: LEVEL-1 filter + LEVEL-2 signal + LEVEL-3 exit -> search for the best combination.
Combination search is a later, separately-registered experiment.
```

## Independence of results (§四十六 / §四十七)

```text
If LEVEL-1 cannot show economic gating, that does NOT imply LEVEL-2 is better; they are reported
separately and neither conclusion substitutes for the other.
LEVEL-3's improvement must come from a SAME-ENTRY comparison (same entries, same data, same cost,
only the exit mechanism differs) — otherwise the improvement cannot be attributed to the exit.
```

## Complexity accounting (§三十三)

For every rung, report: `feature_count, parameter_count, model_class, number_of_decisions,
trade_count, turnover, gross_edge, net_edge, net_pnl, cost_coverage, max_drawdown`.
A complexity increase with no material net improvement is reported as such and **is not an improvement**.

## Promotion ladder (frozen)

```text
CANDIDATE -> EXPERIMENTAL -> OOS_SUPPORTED -> EXECUTION_VALIDATED
```
No rung may skip a step. This task authorises none of the steps.
