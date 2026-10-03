# OUT_OF_SAMPLE_REPORT

> Source: `data/OUT_OF_SAMPLE.json`, `data/EXPERIMENTS.json`.

## Design

Time-ordered blocked OOS; no lookahead; frozen config (`EXPERIMENT_CONFIG`, hash in manifest).
Blocks are contiguous halves of the real-trade series.

| System | train (first 50 %) mean | test (last 50 %) mean | test n |
|---|---|---|---|
| V1_OLD | +1.84 | −2.59 | 54 |
| V1_NEW | −0.33 | −0.79 | 16 |

## What OOS can and cannot say here

- There is **no model or edge to validate out-of-sample**. The question "does a fresh-start strategy
  generalize OOS?" presupposes a strategy whose edge is established in-sample — none is.
- The only interpretation of the table is descriptive: both systems' second half is weaker, but this
  is exactly the in-sample split already tested in Exp 1 (V1_OLD p = 0.064 → INCONCLUSIVE) and it
  fails the placebo control.
- **V2 — the target system — has 0 executed trades**, so an OOS test of V2 is impossible.

## Verdict

`OUT_OF_SAMPLE = NOT_EVALUABLE` for a fresh-start/decay strategy. No blocked-OOS claim is made.
