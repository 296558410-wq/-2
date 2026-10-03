# DECAY_TIME_DISTRIBUTION

> Source: `data/DECAY_TIME_DISTRIBUTION.json`, `data/DECAY_ANALYSIS.json`.

## Definition used

"Decay time" = the age (hours since the run/epoch start, PIT) at which the **cumulative
after-cost net PnL peaks** (drawdown onset), with the zero-crossing as a secondary marker.

## Results

| System | peak cum net | peak age (h) | span (h) | final cum net | exhausted? |
|---|---|---|---|---|---|
| V1_OLD | +149.22 | 167.9 | 491.6 | −42.92 | yes |
| V1_NEW | +54.64 | 64.2 | 82.2 | −17.86 | yes |

Age-bucket after-cost net (analysis bins only, continuous age retained in `AGE_ALIGNED_DATASET.jsonl`):

**V1_OLD**

| bucket | n | net (after cost) | win rate |
|---|---|---|---|
| 0–6h | 5 | +7.45 | 0.20 |
| 0–12h | 1 | −5.61 | 0.00 |
| 0–24h | 10 | −9.96 | 0.30 |
| 0–48h | 20 | −44.81 | 0.50 |
| 0–72h | 6 | +29.31 | 0.67 |
| 0–120h | 14 | +92.10 | 0.64 |
| 0–240h | 20 | −58.37 | 0.40 |
| >240h | 33 | −53.03 | 0.39 |

**V1_NEW**

| bucket | n | net (after cost) | win rate |
|---|---|---|---|
| 0–12h | 3 | +15.54 | 0.67 |
| 0–24h | 1 | +8.52 | 1.00 |
| 0–48h | 6 | −8.21 | 0.33 |
| 0–72h | 14 | +21.96 | 0.43 |
| 0–120h | 8 | −55.67 | 0.13 |

## Interpretation

- The two systems **do not share a decay time** (168 h vs 64 h). There is **NO universal decay
  distribution** in the evidence.
- The V1_OLD curve is **not monotone**: it is negative in the first 48 h, positive in 72–120 h,
  then negative after 240 h. A "fresh start is stronger" reading is contradicted by its own
  first 48 h.
- Bucket cells are tiny (n = 1 … 33). These are descriptive, not inferential.

## Verdict

`DECAY_TIME_DISTRIBUTION = NOT_ESTABLISHED`.
Cross-system universal decay time = **NOT_ESTABLISHED** (n_systems_with_trades = 2, one is a
control arm). A single decay constant must **not** be reported from this data.
