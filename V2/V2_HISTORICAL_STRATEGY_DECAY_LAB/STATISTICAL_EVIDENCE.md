# STATISTICAL_EVIDENCE

> Source: `data/STATISTICAL_EVIDENCE.json`, `data/EXPERIMENTS.json`, `data/DECAY_ANALYSIS.json`.
> Config: seed 20261003, bootstrap 10 000, permutation 10 000, α = 0.05, BH-FDR.

## Effective sample

| System | effective n (closed trades) | span |
|---|---|---|
| V1_OLD | 109 | 491.6 h |
| V1_NEW | 32 | 82.2 h |
| V2 | **0** | — |
| V3 | **0** | — |

Independent Hermes systems = **1** (V1_OLD). V1_NEW is a control arm.

## Test results

| test | raw p | BH-FDR adj p | survives? |
|---|---|---|---|
| Fresh-start [V1_OLD] | 0.0644 | 0.4282 | no |
| Fresh-start [V1_NEW] | 0.9002 | 0.9668 | no |
| Reset effect | 0.2679 | 0.4822 | no |
| 48 h hypothesis [V1_OLD] | 0.9239 | 0.9668 | no |
| 48 h hypothesis [V1_NEW] | 0.1903 | 0.4282 | no |
| Placebo pseudo-start [V1_OLD] | 0.1874 | 0.4282 | no |
| Placebo pseudo-start [V1_NEW] | 0.9668 | 0.9668 | no |
| Reverse test [V1_OLD] | 0.1137 | 0.4282 | no |
| Reverse test [V1_NEW] | 0.8961 | 0.9668 | no |

**No test survives multiple-comparison correction.** The smallest raw p (0.0644, V1_OLD
fresh-start) becomes 0.43 after FDR.

## Power

With n = 109 (and 32) and daily-scale effect sizes around ±2 USD/trade on 0.01 lot, the detectable
effect is large; small decay constants would be under-powered. The honest statement is not "no
decay exists" but **"the available data cannot measure a decay constant."**

## Bootstrap CIs

Per-system bootstrap CIs for early/late half means and the decay series are in
`data/DECAY_ANALYSIS.json` (`A_performance_decay`). They are wide and overlap.

## Controls

Negative controls: random strategy p = 0.001 (method valid); time-shuffled p = 0.062 (claim weak —
see `PLACEBO_NEGATIVE_CONTROL.md`).

## Verdict

`STATISTICAL_EVIDENCE = INSUFFICIENT`. No statistically supported fresh-start, decay, reset, or 48 h
effect. This replicates the prior `ALPHA_EVIDENCE_INSUFFICIENT` at a larger scope (all systems, not
just alpha).
