# MARKET_REGIME_CONTROL

> Source: `data/MARKET_REGIME_CONTROL.json`, `data/CONFOUNDER_REPORT.json`.

## Purpose

Rule out that any apparent "decay" is just a market-regime change rather than strategy aging.

## Method

Volatility proxy = per-day range of entry prices; split each system's trades at the **median
daily range** into high-vol and low-vol days, then compare after-cost means.

| System | n high-vol | n low-vol | mean high-vol | mean low-vol | p |
|---|---|---|---|---|---|
| V1_OLD | (see JSON) | (see JSON) | — | — | — |
| V1_NEW | (see JSON) | (see JSON) | — | — | — |

(Exact cells in `MARKET_REGIME_CONTROL.json`; several daily clusters are too small →
`NOT_EVALUABLE`.)

## Time-of-day and day-of-week

Descriptive means by UTC hour and weekday are in `CONFOUNDER_REPORT.json`. Cells are n = 1…several,
**too small for inference**. Used only to confirm there is no obvious single-hour or single-day
artifact dominating the result.

## Interpretation

- A true market-regime confound would show trades clustered in one regime with regime-correlated
  PnL. The prior audit found the V1_OLD **market itself did not change** (spread p50 0.319 → 0.349 bp,
  similar volatility) across the early-late window, which argues **against** a pure regime story —
  but the sample is small.
- Regime tagging is only available on the V2 decision layer (which has no trades), so it cannot be
  used to attribute V1 P&L.

## Verdict

`MARKET_REGIME_CONTROL = INCONCLUSIVE`. No regime effect is demonstrated, and no regime effect is
excluded. Regime is recorded as a standing confounder, not a resolved one.
