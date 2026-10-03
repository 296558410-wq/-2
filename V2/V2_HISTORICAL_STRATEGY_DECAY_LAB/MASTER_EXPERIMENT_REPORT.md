# MASTER_EXPERIMENT_REPORT

> Consolidated results for **V2_HISTORICAL_STRATEGY_DECAY_LAB** (read-only / shadow).
> Artifacts: registry, episodes, dataset, lifecycle DB, 14 experiments + controls, narrative tree.
> Code commit / hashes: `EXPERIMENT_MANIFEST.json`, `SHA256SUMS.txt`.

## 1. Scope and evidence base

- Entire `C:\AIQuant` scanned → **85** system dirs; **141** real closed trades total.
- Real trade-bearing systems: **V1_OLD** (magic 90002, Hermes LLM candidate, 109 closed) and
  **V1_NEW** (magic 90011, BASELINE control arm, 32 closed).
- **V2: 0 executed trades** (paper/`reference_rules` placeholder). **V3: 0** (gated).
- Everything else is category B/C/D (research / calibration / unverifiable).

## 2. Episodes

44 episodes across V1_OLD / V1_NEW / V2 / V3; 13 conflicts registered. Only one real state reset
(V1_OLD, 2026-09-23T23:39:46Z). Full detail: `SYSTEM_EPISODES.jsonl`, `STRATEGY_DECAY_TIMELINE.md`.

## 3. Experiments 1–14 (+ controls)

| # | experiment | verdict |
|---|---|---|
| 1 | Fresh-start effect (early vs late) V1_OLD / V1_NEW | INCONCLUSIVE (p 0.064 / 0.900) |
| 2 | Cross-system replication | INCONCLUSIVE (only 1 independent system) |
| 3 | Universal decay time | INCONCLUSIVE |
| 4 | Decay-time distribution | INCONCLUSIVE / NOT_ESTABLISHED |
| 5 | Pre-exhaustion signal | INCONCLUSIVE |
| 6 | Reset effect | INCONCLUSIVE (p 0.27) |
| 7 | 48 h hypothesis V1_OLD / V1_NEW | INCONCLUSIVE (p 0.92 / 0.19) |
| 8 | Reverse test | INCONCLUSIVE |
| 9 | Rolling restart | INCONCLUSIVE |
| 10 | Adaptive Evolution (V2) | PRECONDITION_NOT_MET / NOT_EVALUABLE |
| 11 | Market-regime control | INCONCLUSIVE |
| 12 | Time-of-day control | INCONCLUSIVE (descriptive) |
| 13 | Day-of-week control | INCONCLUSIVE (descriptive) |
| 14 | Placebo pseudo-start | INCONCLUSIVE (V1_OLD p 0.19) |

Controls: random strategy p = 0.001 (method valid); time-shuffled p = 0.062 (claim weak);
no-reset structural; synthetic non-edge = random control.

## 4. Decay definitions A–F

| def | meaning | result |
|---|---|---|
| A | performance decay (early vs late) | V1_OLD borderline (p 0.064), V1_NEW no → INCONCLUSIVE |
| B | edge exhaustion w/ CI | both final < 0, but CIs overlap zero-crossing → INCONCLUSIVE |
| C | prediction decay | NOT_EVALUABLE (no per-trade PIT prediction series) |
| D | opportunity/trade-quality decay | win-rate drift present but not significant |
| E | change-point (≥2 methods) | V1_OLD methods DISAGREE → INCONCLUSIVE |
| F | survival / hazard | peak ages 168 h vs 64 h → no shared hazard |

## 5. Confounders

Version-change (V1_OLD vs V1_NEW are different strategies) is fatal to a clean fresh-start claim;
restart/reboot, PIT rotation, selection and design bias are all active. See `CONFOUNDER_REPORT.md`.

## 6. Account mapping

"2026-09-23 V2 ≈ −20 % drawdown" → **UNRESOLVED_ACCOUNT_MAPPING**; cannot be attributed to V2
(0 trades). Nearest real figure is V1_OLD's cumulative net at its 09-23 reset. See
`ACCOUNT_MAPPING_REPORT.md`.

## 7. Replay

V2 reference path reproduces production **120/120 (100 %)** on shadow cycles; V1_OLD NOT_POSSIBLE;
V1_NEW input-hash-only. See `REPLAY_REPORT.md`.

## 8. Bottom line

No statistically supported fresh-start advantage, decay constant, reset effect, or 48 h cycle.
Sample is 2 systems (1 independent), 141 trades, ~24 days. To test the hypothesis properly requires
a **forward, PIT-complete, executed** episode series — which only exists if V2/V3 actually trade.

## 9. Boundaries observed

Read-only / shadow. V2 running, `order_send = 0`, no BROKER_DEMO connect, no historical ledger
edits, nothing written outside the lab dir. **Stopped at RESEARCH_COMPLETE.**
