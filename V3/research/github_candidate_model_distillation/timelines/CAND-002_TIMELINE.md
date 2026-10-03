# TIMELINE — CAND-002 (Spread-State Execution)

Legend: **AVAILABLE** · **NOT_AVAILABLE** · **LABEL_ONLY** · **DIAGNOSTIC_ONLY**.

| instant | what exists | status | may enter the decision? |
|---|---|---|---|
| T-Δ (history) | spread history → rolling percentile, p90; volatility; quote arrival | **AVAILABLE** | YES |
| **T0 (policy instant)** | `spread_bp(T0)`, `spread_pctile(T0)`, `rv(T0)`, `cost_bp(T0)` | **AVAILABLE** | YES |
| T0 | `realised_move(T0→T0+h)` | **NOT_AVAILABLE** | NO |
| T0 + 100 ms … +30 s | `|mid(t)-mid(T0)|`, i.e. the realised move that will define `cost_to_move` | **NOT_AVAILABLE at T0** | NO |
| after the horizon | `realised_ratio = cost_bp / |realised move|` | **LABEL_ONLY / DIAGNOSTIC_ONLY** | **NO** |
| T0 + execution L | the actual spread paid | **NOT_AVAILABLE at T0** | NO — *modelled* from the measured cost distribution |

## Look-ahead assertions

```text
1. The regime label at T0 uses only the spread/volatility history up to T0.
2. cost_to_move at T0 uses the EXPECTED move (from history), never the realised move.
3. realised_ratio is a LABEL/DIAGNOSTIC only; feeding it back into the regime is leakage.
```

## Special risk

CAND-002 is the candidate **most exposed to a subtle look-ahead**: the natural summary statistic
(`cost / realised move`) is *definitionally* post-hoc. The spec therefore requires the decision to be
made from `cost / EXPECTED move`, with the expected move estimated from history only. If the expected-move
estimator turns out to be a proxy for the realised one, the candidate is leaking.
