# PRE_EXHAUSTION_SIGNAL_REPORT

> Source: `data/PRE_EXHAUSTION_SIGNAL_REPORT.json`, `data/DECAY_ANALYSIS.json`.

## Hypothesis

A measurable **pre-exhaustion signal** (a rolling edge metric turning negative) precedes the
cumulative-edge decay, i.e. it could act as an early warning before the strategy goes net negative.

## Test

Rolling-10 mean after-cost net; find the first index where the rolling mean turns negative, and
compare it to the cumulative PnL peak index.

| System | first rolling-10 negative | cum peak index | signal precedes peak? | verdict |
|---|---|---|---|---|
| V1_OLD | early (in a down stretch) | 43 → later recovers to +149 | no reliable ordering | INCONCLUSIVE |
| V1_NEW | early | 21 | ambiguous | INCONCLUSIVE |

## Why INCONCLUSIVE

1. **In-sample only.** The signal is computed on the same series whose peak it would predict — no
   out-of-sample confirmation. This is a look-ahead-fit risk and is rejected as evidence.
2. **Non-stationary.** V1_OLD's rolling mean crosses zero many times (the -44.81 bucket at 0–48 h is
   followed by +92.10 at 0–120 h); a zero-crossing is not a reliable exhaustion marker here.
3. **No independent system to validate on.** V2/V3 have no executed trades. V1_NEW is a control arm.

## Verdict

`PRE_EXHAUSTION_SIGNAL = INCONCLUSIVE`. Do **not** deploy any pre-exhaustion trigger to production
on this evidence. If a fresh signal is wanted, it must be pre-registered and validated OOS on future
data.
