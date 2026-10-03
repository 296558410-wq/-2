# Label Definition (frozen before computation)

Task: **V3-HFT-L1-EXECUTION-EDGE-DISCOVERY-001**.
`future_close` alone is **forbidden** as the trade label. Three labels are built per sample and horizon.

## 1. Convention

```text
timestamps : integer milliseconds since epoch (declared unit; never inferred)
mid        : (bid + ask) / 2
entry_exec : LONG enters at ask(t) ; SHORT enters at bid(t)
future_mid : mid of the FIRST REAL tick at or after t + h  (never interpolated)
MARKOUT > 0 => favourable move
```

## 2. Definitions

```text
MID_MARKOUT(h)
    LONG  : future_mid - entry_mid
    SHORT : entry_mid - future_mid

EXECUTION_MARKOUT(h)
    LONG  : future_mid - entry_execution_price   (= future_mid - ask(t))
    SHORT : entry_execution_price - future_mid   (= bid(t) - future_mid)

NET_EDGE(h)
    = EXECUTION_MARKOUT(h) - ROUND_TRIP_COST_BP        (0.914 bp)
```

`entry_execution_price` is the **real** ask/bid at the decision instant — the tradeable side, never mid.

## 3. Direction consistency (acceptance condition 10)

For a LONG, `EXECUTION_MARKOUT > 0` must coincide with a **price rise**; for a SHORT, with a **price
fall**. Verified by unit tests (long-up, long-down, short-up, short-down) before any result is read.

## 4. Censoring

A sample whose forward window has no real tick at/after `t+h` is `HORIZON_CENSORED` and is
**excluded**. It is never recorded as `0`. `censored_n` is reported per horizon.

## 5. Reporting (per horizon, per configuration)

```text
N, effective_N, mean, median, std, p10, p25, p75, p90, win_rate,
gross_edge, net_edge, bootstrap_CI, block_bootstrap_CI, p_value, q_value,
top1pct_share, top5pct_share, top10pct_share
```

**A positive mean alone never establishes alpha** (see statistical_plan.md §4).
