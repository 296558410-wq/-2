# LAB_BRIEF — Historical Strategy Decay Archaeology

> Durable working brief. This lab exists to reconstruct, from raw evidence, the real
> historical trading systems, their start/restart episodes, and whether a
> "fresh-start advantage" / strategy decay exists and replicates across systems.

## 0. Absolute ground rules (READ-ONLY / SHADOW)

- **No production change.** Do not modify V1, V2, or V3 production code, strategy,
  thresholds, cost model, risk, sizing, prompts, discovery, or the current Phase-3 baseline.
- **V2 must stay RUNNING.** Never stop it. `order_send = 0`. Never connect BROKER_DEMO.
- **Historical ledger and outcomes are immutable.** Never edit an existing ledger/state file.
- **All new files go only under this lab directory.** All experiments are offline/shadow.
- **Do not touch** `research/hermes/trader_v1/**` production paths, `trader_v2/state`,
  `trader_v2/ledger`, `trader_v3/state` (read-only reads are fine).
- Do **not** auto-advance to any next phase. Stop at `RESEARCH_COMPLETE` and wait for
  explicit user authorization before any behaviour change.
- Git: create a dedicated branch `research/v2-historical-strategy-decay-lab`; commit only
  the lab directory. Never commit production-state churn.

## 1. Mission (condensed from the user task book)

Do NOT presuppose any decay cycle ("48h", "2 days", ...). Autonomously discover, from
`C:\AIQuant` + git history + ledgers + state + audit + archives + MT5 evidence:

1. Every trading system / strategy version actually run.
2. Every start / restart / switch episode per system.
3. For each: the timeline from start to decay of prediction/trading/statistical edge.
4. Then run controlled experiments on whether "newly started = stronger" is real,
   replicates across independent systems, has a stable decay-time distribution, and
   whether Fresh-Start / periodic re-adaptation recovers an edge under strict OOS.
5. Decide whether a V2 adaptive Evolution mechanism is warranted.

**First hard principle:** do not trust human-stated dates, memory, prior report
conclusions, or current filenames. Rebuild everything from raw evidence. Prior reports are
an *index only*. Priority: raw broker/ledger/decision/execution/state/git/immutable
evidence > audit reports/summaries/README/human description. Register any conflict and
resolve it.

## 2. Recon facts already established (EVIDENCE, verify before trusting)

These were observed directly; re-verify in the archaeology pass and treat any conflict as
a finding.

- Repo `C:\AIQuant`, HEAD `2b6a14d`, current branch `fix/v2-full-system-repair-20260917`,
  367 commits, tags `V2_FULL_AUDIT_BASELINE`, `V2_REPAIRED_RUN_START`, `v2-pricespace-validated-cf31862`.
- Prior read-only forensics already exist and must be used as index (not truth):
  `research/hermes/audit/hermes_alpha_drift_pit/` (contains reconstructed
  `V1_HERMES_TRADE_DATABASE.jsonl`, `V2_HERMES_TRADE_DATABASE.jsonl`, report +
  `SHA256SUMS.txt`). Prior verdict: `ALPHA_EVIDENCE_INSUFFICIENT`.
- **Real executed trades exist only in the V1 lineage:**
  - `V1_OLD` magic **90002**, 110 rows / 109 closed, `entry_ts` 2026-09-07T16:11Z → 2026-09-28T11:51Z.
  - `V1_NEW` magic **90011**, 32 rows / 32 closed, `2026-09-28T18:35Z` → 2026-10-02T04:48Z.
  - (source: `hermes_alpha_drift_pit/V1_HERMES_TRADE_DATABASE.jsonl`, fields: system, trade_id,
    position_id, magic, direction, entry_ts, exit_ts, entry_price, exit_price, commission,
    swap, net, outcome, closed, provenance)
- **V2 = 0 executed trades.** `trader_v2/state/paper_executions.jsonl` = smoke only;
  `hermes_v2_ledger.jsonl` (15 KB, frozen since 2026-09-11) = `demo_calibration` smoke;
  `V2_HERMES_TRADE_DATABASE.jsonl` rows are DECISION contexts with `executed=false` and
  `note="paper ledger has no executed non-smoke trade"`. ⇒ V2 is `NOT_EVALUABLE` for
  fresh-start/decay until it produces real closed trades.
  *Encoding note:* this file has mojibake `reason` fields; read with
  `encoding='utf-8', errors='replace'` and tolerate undecodable lines.
- **V3 = 0 executed trades** (calibration pilot; `V3_EXECUTION_MODE` / ORDER_SEND_ALLOWED
  gated). Trading execution disabled.
- V1 live ledger: `trader_v1/v1_upgrade/ledger/v1_upgrade_ledger.jsonl` (700 events;
  event types DECISION 446, ORDER_CHECK 42, ORDER_SEND 42, ORDER_REQUEST 42, CLOSE 32,
  PNL 32, FILL 32, POSITION 32; first ts 2026-09-28T12:33:29Z). Recent decisions carry
  `signal_source=BASELINE_TRANSITION`, `not_hermes_alpha=true` ⇒ V1_NEW is a **baseline
  control**, not Hermes alpha. This is a critical confound for "new = better".
- V1 truth layer: `trader_v1/v1_upgrade/truth/evidence/{broker_facts.json,
  decision_snapshots.jsonl, incidents.jsonl}`.
- V1 pre-reset archive: `archive/v1_pre_reset_20260923_233741/` (code, run_state, MANIFEST.json,
  SHA256SUMS) ⇒ a real **state-reset boundary ~2026-09-23 23:37**.
- Research-only systems (category B/C/D): all `research/hermes/trader_v1/v1_r*` dirs
  (r1..r8, forecast/prediction/market-reading rounds), `research/v3_*`, `research/*_lab`,
  `research/alpha_engine`, etc. These are NOT real execution history.
- Account mapping claim to resolve: "2026-09-23 V2 drawdown near −20%". Since V2 has 0
  executed trades, this must be traced to its true account/magic/ledger or declared
  `UNRESOLVED_ACCOUNT_MAPPING`.

## 3. Required deliverable tree (under this lab dir)

```
HISTORICAL_SYSTEM_REGISTRY.json
SYSTEM_EPISODES.jsonl
AGE_ALIGNED_DATASET.jsonl
STRATEGY_LIFECYCLE_DATABASE.json

HISTORICAL_STRATEGY_ARCHAEOLOGY.md
STRATEGY_DECAY_TIMELINE.md
DECAY_TIME_DISTRIBUTION.md
PRE_EXHAUSTION_SIGNAL_REPORT.md

FRESH_START_REPLICATION.md
RESET_VS_EVOLUTION.md
MARKET_REGIME_CONTROL.md
PLACEBO_NEGATIVE_CONTROL.md
ROLLING_EVOLUTION.md

ACCOUNT_MAPPING_REPORT.md
CONFOUNDER_REPORT.md
OUT_OF_SAMPLE_REPORT.md
STATISTICAL_EVIDENCE.md

MASTER_EXPERIMENT_REPORT.md
FINAL_CONCLUSION.md

REPLAY_REPORT.md
EXPERIMENT_MANIFEST.json
SHA256SUMS.txt
```

Plus reproducible scripts under `scripts/` (git-managed, each printing input hashes,
code commit, data sources, experiment-config hash). Intermediate parquet/csv allowed under
`data/`; must not pollute production state/ledger.

## 4. Method requirements

- Registry classification: A = real decision/trade data; B = research only; C = calibration/
  smoke/synthetic; D = never a verifiable episode. Never treat B/C/D as real strategy performance.
- Episodes: derive start/restart/switch boundaries from evidence (magic change, commit
  change, config_hash change, state-reset boundary, gaps, backend change), not assumption.
- Age buckets are analysis bins only — keep continuous time too.
- Recompute performance from raw evidence (never only summaries): prediction, opportunity,
  trade, risk, data layers; before-cost and after-cost; do not alter historical cost
  assumptions.
- Decay definitions A–F as in the task book (performance decay, edge exhaustion w/ CI,
  prediction decay, opportunity-quality decay, change-point via ≥2 methods, survival/hazard).
- Experiments 1–14, controls for market regime, time-of-day, day-of-week, restart/reboot,
  version change, placebo pseudo-start, reverse test, rolling restart, adaptive evolution
  (only after historical decay evidence exists).
- Statistics: PIT, no lookahead, frozen hypotheses/metrics/cost, effective_n, bootstrap CI,
  permutation tests where applicable, FDR / multiple-comparison correction, blocked OOS,
  time-series-aware validation, explicit missing-data reporting. Never redefine a metric
  because a result is unattractive.
- Negative controls: random strategy, random reset, time-shuffled, no-reset, synthetic non-edge.

## 5. Final answer format (in FINAL_CONCLUSION.md)

Must emit the exact block from the task book (历史系统数量, 真实可用 episode 数,
Fresh-Start Effect PASS/FAIL/INCONCLUSIVE, Cross-System Replication, Universal Decay Time,
Estimated Decay Distribution, Pre-Exhaustion Signal, Reset Effect, 48h Hypothesis,
Evolution OOS, V2 当前状态 NO_CHANGE/SHADOW_CANDIDATE, 生产修改 0, order_send 0), then one
clear sentence answering: are we finding a fixed strategy, or a strategy-lifecycle
management / fast market-adaptation mechanism?

Then **STOP**. Do not modify V2. Do not start any next phase.
