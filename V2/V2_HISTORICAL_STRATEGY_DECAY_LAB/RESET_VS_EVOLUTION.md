# RESET_VS_EVOLUTION

> Source: `data/RESET_VS_EVOLUTION.json`, `data/EXPERIMENTS.json` (Exp 6, 10).

## Reset effect — does a state reset create a fresh-start advantage?

The only real state reset is V1_OLD at **2026-09-23T23:39:46Z** (`V1_RUN_20260924_RESET_01`).
Aligning by age (first 72 h after each epoch):

| window | n | mean after-cost net |
|---|---|---|
| first 72 h, pre-reset epoch | small | see `RESET_VS_EVOLUTION.json` |
| first 72 h, post-reset epoch | small | see `RESET_VS_EVOLUTION.json` |

Permutation p = **0.27** → **INCONCLUSIVE**. The post-reset first-72 h was **not** significantly
different from the pre-reset first-72 h.

Note: the reset zeroed *state/statistics*, not strategy code (`archive … reason: V1 RESET
pre-archive`). It changes the *age clock*, not the decision logic. Any measured difference is small
and not significant.

## Evolution experiment (V2)

Per the brief, an evolution/fast-adaptation experiment is only run **if historical decay evidence
exists**. It does not:

- No system shows a statistically significant fresh-start/decay effect (see `STATISTICAL_EVIDENCE.md`).
- V2 — the intended target — has **0 executed trades**, so an evolution OOS test is **NOT_EVALUABLE**
  regardless.

Verdict: Adaptive Evolution = **PRECONDITION_NOT_MET**. No V2 Evolution mechanism is warranted by
this evidence, and none may be started without explicit authorization.

## Verdict

`RESET_EFFECT = INCONCLUSIVE`. `EVOLUTION = PRECONDITION_NOT_MET` (and NOT_EVALUABLE for V2).
