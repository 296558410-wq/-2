# Data State Machine (task XX)

Every field is exactly **one** of:

```text
AVAILABLE | PARTIAL | DATA_GAP | UNSUPPORTED
```

**Banned:** `DATA_GAP -> 0`; `DATA_GAP -> proxy` (unless the field name ends in `_PROXY`).

Implemented in `trader_v3/microstructure/data_state.py` (`registry()`, `validate()`).

## FXTM L1-quote-only feed — field states (audited 2026-09-22)

| field | state | note |
|---|---|---|
| bid, ask, ts_utc, flags | AVAILABLE | native UTC `datetime64[ms,UTC]` |
| mid, spread, spread_bp | AVAILABLE | derived exactly |
| volatility_state | AVAILABLE | rolling return vol + tercile labels |
| arrival_rate | AVAILABLE | quotes/s |
| cost_profile | AVAILABLE | measured 0.914 bp/RT |
| latency_profile | PARTIAL | RTT 273–279 ms measured; per-fill breakdown partial |
| markout | PARTIAL | computable for entries we can reconstruct |
| adverse_selection | PARTIAL | markout-based; conditional estimates noisy |
| ofi_proxy | PARTIAL | tick-rule only — **must be named OFI_PROXY** |
| tick_flow_proxy | PARTIAL | tick-rule only |
| microprice | **DATA_GAP** | needs bid/ask sizes (identically 0) |
| true_ofi | **DATA_GAP** | needs price+size evolution |
| size_imbalance | **DATA_GAP** | needs sizes |
| queue_position | **DATA_GAP** | needs L2 |
| trade_flow | **DATA_GAP** | volume/last identically 0 |
| vpin | **DATA_GAP** | needs trade volume buckets |
| kyle_lambda | **DATA_GAP** | needs signed volume |
| fill_probability | **DATA_GAP** | needs L2 queue; interface scaffold only |

Proof that sizes/prints are absent: across all 35 FXTM files the count of rows with
`volume != 0` or `last != 0` is **0** (`alpha/audit/DATA_CAPABILITY_AUDIT.md`).

`UNSUPPORTED` is reserved for concepts the feed can never carry even with more data of this type
(e.g., a venue-level cancellation intensity without order-level feed).
