# TIMELINE — CAND-003 (Adverse-Selection Conditional Exit)

Legend: **AVAILABLE** · **NOT_AVAILABLE** · **LABEL_ONLY** · **DIAGNOSTIC_ONLY**.

This candidate has **more than one decision instant** (entry, then a sequence of hold/exit decisions),
so the boundary must be re-drawn at every instant.

| instant | what exists | status | may enter the decision? |
|---|---|---|---|
| T-Δ | pre-entry history | **AVAILABLE** | YES (entry decision) |
| **T0 entry** | `state(T0)`, `entry_exec` | **AVAILABLE** | YES |
| T0+L (fill) | `fill_price` | outcome of acting | only *modelled* |
| **T1 = T0+100 ms** | `state(T1)` = new history **up to T1** | **AVAILABLE** | YES (hold/exit at T1) |
| T1 | `mid(T0+1s)`, future path | **NOT_AVAILABLE at T1** | NO |
| T2 = T0+250 ms … T5 = T0+30 s | as T1, each with its own as-of window | **AVAILABLE at that instant** | YES |
| post-exit | realised path, `EDGE_DECAY` / `ADVERSE` / `COST_EROSION` class attribution | **DIAGNOSTIC_ONLY** | **NO** |

## Look-ahead assertions

```text
1. At every decision instant Tk, only ticks with ts <= Tk may be used.
2. E[remaining edge] must be an FORECAST from data up to Tk — never the realised remaining path.
3. The decay FUNCTION (exponential/linear/hazard/empirical) must be frozen before the OOS window.
4. Class attribution (ENTRY_WRONG / EDGE_DECAY / ADVERSE_SELECTION / COST_EROSION) is a POST-TRADE
   diagnostic; it may never be an input to the exit rule.
```

## Why this candidate is the most leak-prone

A multi-instant decision tree is exactly where a fitted decay curve silently becomes a look-ahead
device: if the curve is estimated on the same trades it times, the exit rule "knows" the future.
The only safe protocol is a **pre-registered, frozen** decay form evaluated on an untouched window.
