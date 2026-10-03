# STRATEGY_DECAY_TIMELINE

> Evidence timeline of every start/restart/switch/reset episode per system.
> Source: `SYSTEM_EPISODES.jsonl` (lab root), `data/DECAY_ANALYSIS.json`. Code commit in manifest.

## 1. V1_OLD (magic 90002, account 160759434, Hermes candidate) — 2026-09-07 → 2026-09-28

| ts (UTC) | episode | evidence |
|---|---|---|
| 2026-09-07T11:46Z | EPOCH_START (first recorded decision) | archive `decisions__20260907T1146Z.json` |
| 2026-09-07T16:11Z | TRADE_START (first roundtrip) | V1 trade DB |
| 2026-09-09 ~06:07 local | RESTART (Windows-update reboot) | prior `RESTART_FACTS.json` (day precision) |
| 2026-09-14 | RESTART (documented, timestamp UNKNOWN) | prior `RESTART_FACTS.json` |
| **2026-09-23T23:37:41Z** | **STATE_RESET** (archive boundary) | `archive/v1_pre_reset_20260923_233741/MANIFEST.json` |
| 2026-09-23T23:39:46Z | RUN_START `V1_RUN_20260924_RESET_01` (state zeroed) | `run_state/RUN_META.json` |
| 2026-09-28T11:51Z | EPOCH_END (last V1_OLD roundtrip) | V1 trade DB |

### Performance path (after cost, cumulative)

- Cumulative after-cost net **peaks at +149.22** about **167.9 h** after the epoch start
  (≈ 2026-09-14), then declines monotonically to **−42.92** at the end.
- Early half mean **+1.84 /trade**, late half mean **−2.59 /trade**, permutation p = **0.064**
  (borderline, does not clear α=0.05 and fails FDR).
- The day-level "profit then decay" shape is **CONFIRMED** descriptively (matches the prior audit),
  but see `STATISTICAL_EVIDENCE.md` for why this is **INCONCLUSIVE** as a decay law.

### Change point

- CUSUM changepoint index 43 (~age 167 h, the cumulative peak); binary-segmentation index 107
  (near the end). **Methods disagree** → change point **INCONCLUSIVE**.
- A second reset-like boundary is the 2026-09-23 state reset, which restarts the *age clock*
  (not the strategy).

## 2. V1_NEW (magic 90011, BASELINE control arm) — 2026-09-28 → 2026-10-02

| ts (UTC) | episode | evidence |
|---|---|---|
| 2026-09-28T12:33:29Z | EPOCH_START (first DECISION, ledger seq1) | upgrade ledger |
| 2026-09-28T12:45Z | CONFIG_SWITCH `signal_source=BASELINE_TRANSITION` | `registry/runtime_config.json` |
| 2026-09-28T15:35Z | BACKEND_ENABLE `order_send_enabled=true` | `runtime_config` |
| 2026-09-28T15:35:14Z | TRADE_START (first FILL) | ledger seq48/49 |
| 2026-09-29T23:38:02Z | FIRST_CLOSE (first CLOSE/PNL) | ledger seq228/229 |
| 2026-10-01T13:52:15Z | RESTART (host restart) | `RESTART_FACTS.json` |
| 2026-10-02T01:48:02Z | last order; 02:18:01Z last close | ledger |
| 2026-10-02T03:51Z / 04:13Z / 04:31Z | CODE_SWITCH (riskguard / hardening / truth) — **all after the last trade** | git 63d5a22 / eceeec2 / ec0907e |

**Decay:** cumulative after-cost net peaks **+54.64** at **64.2 h**, ends **−17.86**.
Early half mean **−0.33**, late half **−0.79**, p = **0.90** → **no decay** (negative throughout);
the apparent "early profit" is only ~2 days and small.

## 3. V2 (paper/shadow, magic 90003) — 2026-09-11 → present

Eleven documented run starts (7a88, 5fe2, 4644, df35, b5e4, 8b9e, …). Every run is PAPER/no-broker
(`reference_rules` placeholder). **Zero executed trades.** Cumulative `v2_run_health` counters:
1333 cycles attempted / 1085 WAIT / 126 TRADE / 25 REJECT, all paper. No P&L to decay — the
"decay" question is **NOT_EVALUABLE** for V2.

## 4. V3 — calibration pilot, execution gated OFF, 0 trades. NOT_EVALUABLE.

## 5. Decay verdicts per system

| System | A (perf decay) | B (edge exhaustion) | E (change point ≥2 methods) | F (peak age) |
|---|---|---|---|---|
| V1_OLD | borderline (p=0.064), INCONCLUSIVE | exhausted (final<0) | DISAGREE → INCONCLUSIVE | 167.9 h |
| V1_NEW | no (p=0.90) | exhausted (final<0) | agree (idx 21/25) | 64.2 h |
| V2 | NOT_EVALUABLE | NOT_EVALUABLE | NOT_EVALUABLE | — |

**No single decay constant** is established: two systems give different peak ages (168 h vs 64 h),
one is a control arm, samples are 109 / 32.
