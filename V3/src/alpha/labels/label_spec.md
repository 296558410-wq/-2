# Label spec — V3-HFT-ALPHA-DISCOVERY-001

Frozen in `alpha/freeze/V3_ALPHA_RESEARCH_FREEZE_001.md`
(sha256 `557bcc3c96338c1261f8a5b70371a6a679ff61ec433fbd24234aabf782b8a4d0`).
Implementation: `feature_builder.forward_labels()`.

## Definition

For a decision instant `t` of a sample (the as-of tick time) and horizon `h`:

- `t* = min{ ts_j : ts_j ≥ t + h }` (the first real tick at or after the horizon). **No interpolation.**
- `y_gross_bp(t,h) = ( mid(t*) / mid(t) − 1 ) · 1e4`, `mid = (bid+ask)/2`.
- `y_net_bp(t,h) = y_gross_bp(t,h) − c_bp(t)`, where `c_bp(t) = RT_USD / mid(t) · 1e4`.
- `RT_USD` = the round-trip cost from the frozen tier list (anchor 0.40).

If no tick exists at `≥ t + h`, or `t*` falls in a different segment, the label is **undefined**
and the sample is dropped. Undefined labels are never interpolated, carried forward or fabricated.

## Segment / cleanliness rules (frozen)

- `seg(i)` = maximal run of ticks in which every consecutive gap ≤ `G_MAX(h)`.
- `G_MAX(h) = max(60 s, 10·h)` for `h ≤ 5 min`; `G_MAX(h) = 1 h` for `h ≥ 1 h`.
- **defined** = a forward tick exists; **clean** = defined ∧ same segment ∧ `slack ≤ 0.5`,
  where `slack = (t* − t − h)/h`.
- Purge/embargo: TRAIN samples whose `t*` reaches the VAL window are removed; likewise VAL → TEST.

## Cost model

Two evaluations per frozen design:

1. **Lump-sum stress** (this label): `c_bp = tier_USD / mid(t) · 1e4`;
   tiers `0.40 / 0.50 / 0.60 / 0.80 / 1.00` USD per round-trip.
2. **Simulated execution** (`alpha/backtest/latency_sensitivity.json`): entry at real `ask` (long)
   / `bid` (short) at `t+L`, exit at real `bid` / `ask` at `t+h+L`, minus commission 0.22 USD/RT.

`NET_LABEL_STATUS` is `OK(cost-aware)` when a measured cost is applied, `DATA_GAP` otherwise.
Gap crossings (weekend, registered `21:00–22:59Z` hole, collector outages) are excluded by the
segment rule — they are reported as DATA_GAP, not patched.
