# TIMELINE — CAND-001 (Execution-Aware L1 Markout Gate)

Legend: **AVAILABLE** (usable at that instant) · **NOT_AVAILABLE** (does not exist yet) ·
**LABEL_ONLY** (may be used only to build a training label) · **DIAGNOSTIC_ONLY** (may never enter a decision).

| instant | what exists | status | may enter the decision? |
|---|---|---|---|
| T-Δ (history) | bid/ask/mid/spread history, rolling volatility, spread percentile, quote arrival, tick-rule proxy | **AVAILABLE** | YES |
| **T0 (decision)** | `state(T0)`; `spread_bp(T0)`; `entry_exec(T0) = ask(T0)` for LONG | **AVAILABLE** | YES |
| T0 + execution L | fill at `ask(T0+L)` (measured RTT ≈ 279 ms) | **NOT_AVAILABLE at T0** (it is the outcome of acting) | NO — may only be *modelled* |
| T0 + 100 ms | `mid(T0+100ms)` | NOT_AVAILABLE at T0 | NO (LABEL_ONLY / DIAGNOSTIC_ONLY after the fact) |
| T0 + 250 ms | `mid(…)` | NOT_AVAILABLE at T0 | NO |
| T0 + 500 ms | `mid(…)` | NOT_AVAILABLE at T0 | NO |
| T0 + 1 s | `mid(…)` | NOT_AVAILABLE at T0 | NO |
| T0 + 2 s | `mid(…)` | NOT_AVAILABLE at T0 | NO |
| T0 + 5 s | `mid(…)` | NOT_AVAILABLE at T0 | NO |
| T0 + 30 s | `mid(…)` | NOT_AVAILABLE at T0 | NO |
| any post-fill instant | `EXECUTION_MARKOUT`, realised `AS`, realised slippage | **DIAGNOSTIC_ONLY** | **NO — never** |

## Look-ahead assertions

```text
1. state(T0) uses ONLY ticks with ts <= T0 (backward as-of join). No centred window.
2. The label uses the first REAL tick at or after T0+h inside the SAME segment (censoring rule).
3. Post-fill quantities (markout, AS, slippage) are DIAGNOSTIC_ONLY and may not become features.
4. If the model is evaluated at T0, every input must be reproducible from the data available at T0.
```

## Verdict

CAND-001 has a **clean** information boundary: one decision instant, one label horizon, and an
explicit prohibition on post-fill quantities. The main leak risk is procedural, not structural —
using a `mid`-based label while pretending the trade filled at `mid`.
