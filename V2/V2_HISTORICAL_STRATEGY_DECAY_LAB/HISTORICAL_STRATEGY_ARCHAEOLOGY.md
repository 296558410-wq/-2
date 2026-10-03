# HISTORICAL_STRATEGY_ARCHAEOLOGY

> Read-only / shadow reconstruction of every historical trading system found in `C:\AIQuant`.
> Evidence-first; prior reports used as index only. Code commit: see `EXPERIMENT_MANIFEST.json`.
> Data: `HISTORICAL_SYSTEM_REGISTRY.json`, `SYSTEM_EPISODES.jsonl`, `STRATEGY_LIFECYCLE_DATABASE.json` (lab root);
> supporting analysis under `data/`.

## 0. Method

Scanned `research/hermes/trader_v1`, `trader_v2`, `trader_v3`, `archive/`, `research/v3_*`,
`research/*_lab`, all `v1_r*` dirs, plus git history/reflog, ledgers, state, audit and archives.
Each candidate directory was auto-classified:

- **A** = real decision/trade data (executed broker trades exist)
- **B** = research only (no execution)
- **C** = calibration / smoke / synthetic (a run exists but no real trades)
- **D** = never a verifiable episode

Never treat B/C/D as real strategy performance.

## 1. Registry result

`HISTORICAL_SYSTEM_REGISTRY.json` registers **85** system directories.

| category | count | meaning |
|---|---|---|
| A | 3 | real executed-trade evidence (V1_OLD, V1_NEW, V1_UPGRADE lineage) |
| A-archive | 2 | immutable pre-reset archive of V1_OLD |
| B | 34 | research-only rounds (`v1_r*`, `v3_*`, `*_lab`, alpha discovery) |
| C | 2 | V2 paper/shadow, V3 calibration (no real trades) |
| D | 44 | scanned dirs with no verifiable episode |

**Real closed trades in the whole repo: 141** — 109 `V1_OLD` (magic 90002) + 32 `V1_NEW`
(magic 90011). No other system has a single executed, closed, broker-confirmed trade.

## 2. What each system actually is

Three systems carry the name "Hermes" but only one is a Hermes candidate:

| System | Decision layer | Hermes alpha? | Trades |
|---|---|---|---|
| **V1_OLD** (magic 90002) | Hermes **LLM plan engine** (decisions carry `model`/`confidence`/`answers_14`/`mtf_agreement`) | **candidate** — but early inputs rotated, PIT-unverifiable | DEMO, 109 closed |
| **V1_NEW** (magic 90011) | `BASELINE_CONTROL` control arm (`signal_type=BASELINE_CONTROL`, `not_hermes_alpha=true`, mechanical map) | **NO** (control) | DEMO, 32 closed |
| **V2** (`V2-PAPER-*`) | `reference_rules` deterministic placeholder (`signal_from_agents=false`) | **NO** | PAPER, **0 executed** |
| **V3** | V3 research / calibration pilot, execution gated OFF | **NO** | **0 executed** |

**Critical identity fact:** the only system that ever ran a real Hermes LLM decision layer is
V1_OLD, and its early inputs are not PIT-recoverable. "Three Hermes systems both profited then
decayed" is **not true at the system-identity level** — two of the three are not Hermes alpha
while trading (V1_NEW = control arm; V2 = deterministic placeholder with zero trades).

## 3. Lifecycle (see `STRATEGY_LIFECYCLE_DATABASE.json`)

| System | first trade | last trade | span | n closed | win rate | net before cost | net after cost |
|---|---|---|---|---|---|---|---|
| V1_OLD | 2026-09-07T16:11Z | 2026-09-28T11:51Z | 491.6 h | 109 | 0.440 | −20.43 | **−42.92** |
| V1_NEW | 2026-09-28T18:35Z | 2026-10-02T04:48Z | 82.2 h | 32 | 0.375 | −11.44 | **−17.86** |
| V2 | — | — | — | 0 | — | — | **0 (no trades)** |
| V3 | — | — | — | 0 | — | — | **0 (no trades)** |

Ledger cross-check: the V1 upgrade ledger contains exactly 32 FILL / 32 CLOSE / 32 PNL events
whose PnL sum is −11.44 — matching the V1_NEW before-cost total. The trade DB is consistent
with the ledger.

## 4. Category B/C/D honesty note

The 34 category-B directories (`v1_r2_* … v1_r8_*`, `trader_v3/alpha`, `research/v3_*`,
`alpha_engine`, `*_lab`, …) contain backtests, mechanism searches and reports — they produced
**no executed trades**. Several are explicitly negative (`NO_VALIDATED_EDGE`,
`COST_INSUFFICIENT`, `ALPHA_EVIDENCE_INSUFFICIENT`). They are recorded for completeness and are
**excluded** from any performance/decay statement.

## 5. Conflicts registered

See `data/SYSTEM_EPISODES.jsonl` (13 conflicts). Notable:

- V1_OLD restart dates (2026-09-09 Windows update, 2026-09-14) are day/local-time precision only.
- V1_NEW `replay_match` field is permanently `null` in the ledger → must not be cited as replay evidence.
- Old-V1 "09-17 snapshot −12.09 vs broker same-day −16.01" → broker facts take precedence.
- The `-20%` V2 drawdown claim does not map to any V2 account (see `ACCOUNT_MAPPING_REPORT.md`).

## 6. Verdict

`ARCHAEOLOGY_COMPLETE`. Real usable episode base = **2 systems** (V1_OLD candidate + V1_NEW control
arm), 141 closed trades, ~24 days total. Everything else is research/calibration/synthetic and is
**NOT_EVALUABLE** as strategy performance.
