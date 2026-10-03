# PLACEBO_NEGATIVE_CONTROL

> Source: `data/PLACEBO_NEGATIVE_CONTROL.json`.

## Controls run

| control | description | result |
|---|---|---|
| Random strategy | 1000 synthetic zero-edge series, same n as V1_OLD | p(≥ real effect) = **0.001** |
| Time-shuffled | V1_OLD outcomes shuffled in time, 1000× | p(≥ real effect) = **0.062** |
| No-reset | V1_NEW is already a single epoch with no reset | n/a (structural) |
| Synthetic non-edge | the random-strategy control IS the non-edge control | see above |
| Placebo pseudo-start | all random split points vs the observed split | V1_OLD p = 0.187 |

## Reading of the controls

- The **method passes its own negative controls**: a truly random strategy almost never produces the
  observed splIT difference (p = 0.001), so the measurement machinery is not trivially broken.
- **However, the time-shuffled control is only borderline (p = 0.062)**. Shuffling the *real*
  outcomes and re-splitting reproduces a difference as large as the observed one 6.2 % of the time.
  That means the observed V1_OLD early-vs-late gap is **largely explainable by the arrangement of
  outcomes, not by an age/decay process**. This is exactly the "placebo pseudo-start" failure:
  a random split of the same data does nearly as well.
- Interpretation: the controls **support the METHOD but undercut the fresh-start/decay claim**. They
  are the main reason Fresh-Start is reported INCONCLUSIVE rather than PASS.

## Verdict

`NEGATIVE_CONTROL = METHOD_VALID`; `FRESH_START_PLACEBO = FAILED` (observed effect not extreme vs
shuffled splits). Overall decay/fresh-start claim stays **INCONCLUSIVE**.
