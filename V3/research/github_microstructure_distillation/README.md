# GitHub Microstructure Distillation — V3-HFT-GITHUB-MICROSTRUCTURE-DISTILLATION-003

`DISTILLATION ONLY` · `ALPHA_SEARCH = OFF` · `MODEL_TRAINING = OFF` · `FORWARD = NO` · `LIVE = NO` ·
`ORDER_SEND = 0` · no MT5 connection · no strategy copying.

Goal: distil **mechanisms** (not strategies) from public repos, then form **3–5 candidate HFT model
architectures** that V3 could later verify on frozen data. A result of "no worthwhile mechanism" is a
valid outcome; the evidence bar is never lowered to reach a candidate.

## Inherited V3 facts (must be honoured)

```text
V3_HFT_STATUS       = DATA_INSUFFICIENT / RESEARCH_LIMITED
EXECUTABLE_ALPHA    = NOT_FOUND
5s = CURRENT_NET_NEGATIVE ; 10s / 30s / 60s / 5min = INSUFFICIENT
ROUND_TRIP_COST     = 0.40 USD  ~= 0.914 bp
TRUE_OFI / TRUE_QUEUE / TRADE_FLOW / FILL_PROBABILITY / HISTORICAL_L2 = DATA_GAP
REALTIME_DOM        = AVAILABLE  but  DEPTH_PROFILE = SYNTHETIC_OR_AGGREGATED
```

Consequences enforced here: exchange-grade L2 alpha is **never** assumed to transfer to FXTM XAUUSD;
`DEPTH_PROFILE = SYNTHETIC` means the DOM cannot supply true queue/OFI information.

## Reading rules (§二)

```text
code > README · experiments > marketing · OOS > backtest · real tick > candle
execution > signal · net PnL > gross PnL · failure cases > marketing results
```

## Evidence levels (§十二)

```text
E0 README_CLAIM_ONLY            author asserts, nothing verifiable
E1 CODE_VERIFIED                code exists and implements the method
E2 BACKTEST_VERIFIED            an experiment can be inspected/reproduced
E3 OOS_VERIFIED                 explicit out-of-sample / walk-forward
E4 EXECUTION_AWARE_VERIFIED     real or defensible execution cost included
E5 REAL_EXECUTION_EVIDENCE      real fills / replay / broker execution evidence
```
**An E0 project is never treated as E4/E5.**

## Transferability (§十三)

```text
A DIRECTLY_TRANSFERABLE   usable on FXTM L1 as-is
B METHOD_TRANSFERABLE     method/idea transfers, data must change
C DATA-DEPENDENT          needs data FXTM does not have (real L2/queue/tape)
D AUXILIARY_ONLY          context/benchmark only
E NOT_TRANSFERABLE        different market structure or unverifiable
```

## Directory map (§三十五)

```text
github_search_registry.json          searches performed + results
github_distillation_registry.json    one record per distilled MECHANISM
negative_evidence_registry.json      failure mechanisms (high value)
repository_cards/                    per-repo REPOSITORY_CARD.md (14 items)
mechanism_cards/                     per-mechanism cards
execution_models/ l1_models/ market_making_models/ failure_cases/
candidate_models/ candidate_architectures/
evidence_matrix.csv                  research-fit matrix (facts only, no winners)
final_distillation_report.md         answers Q1–Q12
candidate_model_spec.md              the 3–5 candidate architectures
SHA256SUMS
```

## Three gates before any candidate is "READY_FOR_V3_EXPERIMENT" (§二十四 / §三十八)

```text
Gate 1 RESEARCH    mechanism plausible
Gate 2 DATA        FXTM data can observe the required state
Gate 3 EXECUTION   net edge can survive the actual 0.914 bp cost
```
Failing any gate ⇒ `REJECT` / `PARK`. Nothing here is tested, and nothing here authorises trading.

## Explicit non-goals

```text
no "Best Project" / "Winner" / "Top Strategy" ranking
no copying of a GitHub strategy
no claim that any venue's L2 alpha exists on FXTM XAUUSD
no pre-emptive experiment
```
