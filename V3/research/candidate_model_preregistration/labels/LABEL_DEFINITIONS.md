# LABEL DEFINITIONS (frozen)

`PREREGISTRATION_ID = V3-HFT-PREREG-001` · `STATUS = LOCKED`

## Convention

```text
timestamps : integer ms since epoch (unit DECLARED, never inferred)
mid        : (bid + ask) / 2
entry_exec : ask(t + L) for LONG ; bid(t + L) for SHORT   (L = measured latency ~279 ms)
t*         : the FIRST REAL tick at or after t + h INSIDE THE SAME SEGMENT   (never interpolated)
d  ∈ {+1, -1} : trade direction
```

## The four objects (distinct meanings; never conflated)

```text
FUTURE_MARKOUT(t,h)        = d * ( mid(t*) - mid(t) )                      LABEL_ONLY
EXECUTION_MARKOUT(t,h)     = d * ( mid(t*) - entry_exec(t+L) )             LABEL_ONLY
COST_ADJUSTED_MARKOUT(t,h) = FUTURE_MARKOUT(t,h) - cost_bp(t)              LABEL_ONLY
REALIZED_PNL               = the accounting result of an ACTUAL fill       ONLY AFTER EXECUTION
```
`REALIZED_PNL` exists only post-execution and is a diagnostic; it is never a feature.

## Three-way outcome (mandatory reporting form)

```text
FAVOURABLE  markout >  +epsilon
UNCHANGED   |markout| <= epsilon
ADVERSE     markout <  -epsilon
epsilon = 0 bp unless a registered dead-band is added (none is registered in round 1)
```
A binary win/loss summary is insufficient and must be accompanied by this split.

## Censoring (hard)

```text
A sample is HORIZON_CENSORED iff
  - no real tick exists at/after t+h, OR
  - t* lies in a different session segment than t (weekend / gap / discontinuity / snapshot edge)
Censored samples are EXCLUDED. They are never 0, never interpolated, never carried forward.
censored_n must be reported per horizon.
```

## Future information rule

```text
Everything computed from t* is LABEL or DIAGNOSTIC.
Post-fill quantities (realised markout, realised adverse selection, realised slippage, MFE, MAE)
are DIAGNOSTIC_ONLY and may NEVER enter a decision feature.
```

## Self-impact guard (LEVEL-3)

```text
MIN_MARKOUT_HORIZON_MS = 500
Markouts measured closer than 500 ms to a fill may not be used as evidence of adverse selection
(the execution window itself is ~279 ms).
```
