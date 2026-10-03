# Failure Cases — V3's own measured evidence (§九 / §二十一)

These are **V3-internal** failure cases, already produced and reproducible from the frozen snapshot.
They are the baseline the GitHub distillation is judged against: any imported mechanism must not
re-create one of these.

## FC-001 — SIGNAL_EXISTS_BUT_EXECUTABLE_EDGE = NO

```text
EVIDENCE : alpha/audit/EXECUTION_COST_AUDIT.md ; l1_execution_edge/
FACTS    : real short-horizon predictability exists (rank-IC -0.179 @1s, -0.142 @5s)
           best estimated gross edge +0.096 bp  vs  cost 0.914 bp   (~9.5x short)
           cost / median-move > 1 for h <= 2 s   (1.43x at 1s)
CLASS    : COST_ERASED_ALPHA
LESSON   : a usable predictor is worth nothing if its edge is smaller than the toll.
V3 RULE  : never re-open sub-2s taker alpha without a cost-structure change.
```

## FC-002 — TAIL_DEPENDENT "EDGE"

```text
EVIDENCE : l1_execution_edge/diagnostics.json
FACTS    : candidate showed mean +3.53 bp, median -1.20 bp, win rate 0.31,
           top-10% of trades = ~70% of total PnL
CLASS    : TAIL_DEPENDENCE
LESSON   : means are not evidence; the central tendency and the tail shares must be reported together.
```

## FC-003 — MECHANICAL_SIGNAL_ARTIFACT

```text
EVIDENCE : l1_execution_edge/diagnostics.json
FACTS    : corr(prediction, spread_bp) = -0.9994 ; essentially all trades SHORT ;
           the mechanical predictor '-spread/2' alone produced 0 trades
CLASS    : MECHANICAL_SIGNAL_ARTIFACT
LESSON   : ask "is this a forecast or an accounting identity?" before believing any edge.
```

## FC-004 — LABEL GAP-GUARD BUG

```text
EVIDENCE : l1_execution_edge/experiment_results_v1_no_gapguard.json (preserved)
FACTS    : labels lacked a session/segment guard; forward windows crossed weekend/session gaps
           and manufactured large moves that no order could realise
CLASS    : LABEL_IMPLEMENTATION_BUG
LESSON   : censoring must test "same trading segment", not merely "a later tick exists".
```

## FC-005 — SYNTHETIC DOM MASQUERADING AS DEPTH

```text
EVIDENCE : microstructure_source_audit/evidence/mt5_dom_authenticity_result.json
FACTS    : 60/60 snapshots returned ONE identical mirrored size ladder
           (100/400/500/4000/10000 per side), spread constant 0.18 USD
CLASS    : SYNTHETIC_DATA_DEPENDENCE
LESSON   : a "10-level DOM" can be an aggregated profile with zero queue information.
```

## FC-006 — DATA vs TRADE-SPARSITY CONFUSION

```text
EVIDENCE : l1_statistical_power/sample_dependence.json vs l1_execution_edge/
FACTS    : sample-level effective_N = 2,220-148,226, but the threshold rule produced only
           0-37 effective TRADES -> the earlier "INSUFFICIENT" was a rule artefact
CLASS    : POWER_LIMITATION
LESSON   : report sample-level AND trade-level effective_N; they answer different questions.
```

## Cross-cutting lesson

```text
Every failed case above is a *methodology* failure, not a modelling-capacity failure.
None of them would be fixed by a bigger model, an extra indicator, or a Transformer.
```
