# Feature spec — V3-HFT-ALPHA-DISCOVERY-001

Frozen in `alpha/freeze/V3_ALPHA_RESEARCH_FREEZE_001.md`
(sha256 `557bcc3c96338c1261f8a5b70371a6a679ff61ec433fbd24234aabf782b8a4d0`).
Implementation: `alpha/features/feature_builder.py` (pure numpy, causal, vectorized).
Prices in USD; returns/labels in **bp** (`1e-4`).

## Causality contract

Every feature at tick `i` is a function of ticks `≤ i` only. No future tick, no forward label,
no cross-segment stitching. The sampled decision instant `g` uses the **as-of** tick
(`last tick with ts ≤ g`), dropped if stale by > 5 s. Verified by construction: all rolling
windows end at `i`; all lags are `mid[i]/mid[i-k]`.

## Families (≤ 2 features each, as frozen)

| id | family | feature | definition | window | status |
|---|---|---|---|---|---|
| B0 | lagged returns (baseline) | `r1_bp` | `(mid[i]/mid[i-1] − 1)·1e4` | 1 tick | OK |
| | | `r2_bp` | `(mid[i]/mid[i-2] − 1)·1e4` | 2 ticks | OK |
| B1 | microprice deviation | `micro_dev_bp` | `(microprice − mid)·1e4`, `microprice = (bid·ask_vol + ask·bid_vol)/(ask_vol+bid_vol)` | instant | **DATA_GAP** on FXTM (`volume_real = 0` everywhere) |
| | | `micro_dev_norm` | `(microprice − mid)/spread` | instant | **DATA_GAP** (same) |
| B2 | order-flow imbalance | `ofi_signed_sum` | Σ sign(Δmid) over window | 20 ticks | L1 proxy (no prints on this feed) |
| | | `ofi_proxy` | `ofi_signed_sum / 20` | 20 ticks | L1 proxy |
| B3 | short-term momentum | `mom10_bp` | `(mid[i]/mid[i−10] − 1)·1e4` | 10 ticks | OK |
| | | `mom50_bp` | `(mid[i]/mid[i−50] − 1)·1e4` | 50 ticks | OK |
| B4 | spread / volatility state | `spread_z50` | `(spread − mean₅₀)/std₅₀` | 50 ticks | OK |
| | | `vol50_bp` | `std₅₀(r1_bp)` | 50 ticks | OK |
| B5 | limited reversal | `rev10_clip_bp` | `−clip(mom10_bp, ±1.0 bp)` | 10 ticks | OK |
| | | `rev50_clip_bp` | `−clip(mom50_bp, ±1.0 bp)` | 50 ticks | OK |
| B6 | interaction (minimal) | `mom10_x_spreadz` | `mom10_bp · spread_z50` | — | OK |
| | | `mom10_x_vol` | `mom10_bp · vol50_bp` | — | OK |

Frozen constants: `OFI_WINDOW = 20`, `MOM_WINDOWS = (10, 50)`, `STATE_WINDOW = 50`, `REV_CLIP_BP = 1.0`.

## Data-availability verdicts (measured, not assumed)

- **B1 (microprice)**: not computable on FXTM — `volume`, `volume_real` and `last` are identically
  zero across all 7,239,126 ticks. On DUKA `bid_vol == ask_vol` in 33–85% of ticks, so the size
  signal is degenerate there too. → `B1 = DATA_GAP`; the family is still *run* (its two columns are
  identically 0) to confirm it carries no information.
- **B2 (true OFI)**: no trade prints or sizes → the frozen L1 tick-rule proxy is used instead and
  is labelled as a proxy, never as true OFI.
- **L2 / trade_flow**: `UNKNOWN (L2_DATA_GAP)`, carried from the registry. Not synthesised.

## Standardisation

Raw features are standardised with **TRAIN-fold** mean/σ only; the same μ/σ are applied to VAL/TEST.
Samples with non-finite features for that family are dropped for that family (counted and reported).
