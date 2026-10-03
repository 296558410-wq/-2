# Opportunity Gate (task XXII)

Every future opportunity must pass **all** layers or be rejected with an explicit `BLOCK_REASON`.

```text
DATA_VALID
   -> FEATURE_VALID
   -> PREDICTION_VALID
   -> GROSS_EDGE_VALID
   -> COST_VALID
   -> EXECUTION_VALID
   -> ADVERSE_SELECTION_ACCEPTABLE
   -> NET_EDGE > threshold
   -> HERMES DECISION
```

Failure at any layer => `WAIT` + record `BLOCK_REASON`.

| layer | pass condition | today's status |
|---|---|---|
| DATA_VALID | required fields not DATA_GAP for the hypothesis | microprice/OFI/queue hypotheses: **FAIL (DATA_GAP)** |
| FEATURE_VALID | feature is PIT-causal, out-of-sample stable | PASS for L1 price features |
| PREDICTION_VALID | predictive metric significant after multiple-testing control | prior study: **FAIL (0/30 FDR)** |
| GROSS_EDGE_VALID | gross edge > 0 with a CI excluding 0 | marginal / not established |
| COST_VALID | gross edge > total cost + margin | **FAIL (0.096 bp << 0.914 bp)** |
| EXECUTION_VALID | fill + latency + slippage modelled, not assumed | **FAIL (fill DATA_GAP)** |
| ADVERSE_SELECTION_ACCEPTABLE | post-fill drift not systematically adverse | PARTIAL (markout ≈ 0 median, fat tail) |
| NET_EDGE > threshold | net > +0.10 USD/RT | **FAIL (net negative)** |

Decision vocabulary handed to Hermes: `TAKE` / `PASSIVE` / `WAIT` / `EXIT`.
Not: "predict the next candle".

Hermes input shape (target) — `MARKET_STATE` with `directional_edge`, `microstructure_edge`,
`expected_return`, `spread`, `spread_state`, `volatility_state`, `markout_profile`,
`adverse_selection_probability`, `expected_slippage`, `expected_latency_cost`,
`expected_total_cost`, `fill_probability`, `net_executable_edge`, `confidence`, `data_quality`.

Any field that is DATA_GAP must be passed through as `DATA_GAP` (Hermes must not treat it as 0).
