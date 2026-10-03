# GitHub Candidate-Model Distillation — V3-HFT-GITHUB-CANDIDATE-MODEL-DISTILLATION-004

`DISTILLATION_ONLY / READ_ONLY` · `MODEL_TRAINING = OFF` · `ALPHA_SEARCH = OFF` ·
`FEATURE_MINING = OFF` · `HYPERPARAMETER_SEARCH = OFF` · `FORWARD = NO` · `LIVE = NO` · `ORDER_SEND = 0`
· no MT5 connection · no backtest of any candidate.

## Goal

Turn three research ideas into **explicitly computable model specifications**:

```text
GitHub Evidence -> Mechanism -> Model Component -> Mathematical Specification
                -> FXTM Data Compatibility -> Execution Compatibility -> Candidate Model
```

Only if the whole chain is walked does a candidate reach `READY_FOR_PRE_REGISTRATION`.
**It never means "profitable".**

## Deliverables

```text
README.md                          this file
candidate_models/CAND-001.md       Execution-Aware L1 Markout Gate       (PRIMARY)
candidate_models/CAND-002.md       Spread-State Execution                (SECONDARY)
candidate_models/CAND-003.md       Adverse-Selection Conditional Exit    (EXPLORATORY)
model_components/01_state .. 10_position   component library (10 components, CMP-01..CMP-10)
timelines/CAND-00{1,2,3}_TIMELINE.md       information-timing diagrams
repository_cards/index.md          source-repo index with evidence levels
model_component_registry.json      one record per component
candidate_model_registry.json      one record per candidate
github_search_registry.json        searches dispatched + delegation
evidence_matrix.csv                repo-level facts only
failure_matrix.csv                 10 failure classes and their mitigations
candidate_model_comparison.md      structural comparison (no ranking)
final_model_distillation_report.md answers Q1–Q14
parts/                             the two gap-search audits
SHA256SUMS
```

## The interface every candidate must satisfy (§三十二)

```text
ModelState -> GrossEdge -> ExecutionCost -> AdverseSelectionRisk -> NetEdge -> Decision
Decision ∈ { TAKE, WAIT, EXIT }        (WAIT is a legitimate, successful output)
```

## Evidence rule (§十九)

```text
E0 README claim · E1 code verified · E2 backtest verified · E3 OOS verified ·
E4 execution-aware verified · E5 real execution evidence
Components and candidates need E2+ ; E0/E1 -> PARK
```

## FXTM inherited reality (binding on every spec)

```text
FXTM L1 = AVAILABLE            TRUE OFI = DATA_GAP        TRUE TRADE FLOW = DATA_GAP
TRUE QUEUE = DATA_GAP          HISTORICAL L2 = DATA_GAP   FILL PROBABILITY = DATA_GAP
realtime DOM = AVAILABLE but SYNTHETIC_OR_AGGREGATED  -> may NOT be treated as real FIFO L2
ROUND_TRIP_COST = 0.40 USD ~= 0.914 bp (CALIBRATION_20RT_20260921) ; 0.314 bp is FORBIDDEN
```

## Hard rules applied throughout

```text
PARAMETERS = TBD_IN_PRE_REGISTERED_EXPERIMENT      (no threshold invented here)
no component stitching into a strategy without mechanistic justification
prediction vs diagnostic separated in every spec
post-fill quantities = DIAGNOSTIC_ONLY, never inputs
WAIT is not a failure
no "best/winner/most profitable"
```

## Status

```text
CANDIDATE_MODEL = UNTESTED                     (all of them)
CAND-001/002/003 = READY_FOR_PRE_REGISTRATION  (documentation state only)
CAND-004/005     = PARKED                      (data-blocked)
```

## Final state (§四十)

```text
WAIT_FOR_CHATGPT_FINAL_AUDIT
```
No automatic entry into L1 replication, model training, paper, demo, forward or live.
