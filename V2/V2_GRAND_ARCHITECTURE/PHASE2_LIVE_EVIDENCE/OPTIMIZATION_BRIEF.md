# OPTIMIZATION_BRIEF — V2 Phase 2 运行优化

> Goal: keep V2 Production and Shadow research *logic* identical, but make the 15-min shadow
> runner **cheap while the market is closed**, **auto-resume full pipeline when it reopens**, and
> stop the periodic no-op churn. End state `OPTIMIZED_CONTINUOUS`.

# A. Hard boundaries (unchanged)

- V2 Production not stopped / not modified. V1 / V3 fully untouched. `order_send = 0`.
- Never enter `BROKER_DEMO` / LIVE. Never rewrite historical ledger/state/evidence. Shadow stays READ-ONLY.
- Do NOT change the 15-minute schedule (leave `\OpenClaw\hermes-v2-shadow-evidence` + its launcher cadence as-is).
- Do NOT change strategies, parameters, RiskGuard, cost assumptions, or any existing research conclusion.
- Shadow must never have execution authority. Shadow failure = FAIL-CLOSED, must not affect production.
- Do NOT auto-reset, auto-evolve, or auto-promote any strategy. No fake decision/outcome/sample.

# B. Current state (recon, verify before editing)

- Scheduler `\OpenClaw\hermes-v2-shadow-evidence` fires every 15 min via
  `C:\Users\surface\.openclaw\launchers\hermes-v2-shadow-evidence-hidden.vbs` → runs
  `...\PHASE2_LIVE_EVIDENCE\runner\build.py --live`. It is firing correctly (0 missed runs).
- `build.py --live` currently runs the FULL pipeline every cycle: `SS.run_live()` → `BF.run_backfill()`
  → `GB.run_gpu()` → `A.main()` → `SC.run_check()` → `_write_live_arch()` / `_write_final()`.
  ⇒ while market is closed this rewrites ~7 timestamped report files and runs GPU/analytics on
  identical state every 15 min (~3 min/run), producing git churn with no new information.
- Market is currently CLOSED (weekend). `trader_v2\state\v2_run_health.json` exposes `market_open`
  (bool), `cycle_result` (e.g. `MARKET_CLOSED_SKIP`), `run_status`, `replay_status`, `blocked`.
  This is the read-only signal to branch on.
- Idempotency keys already exist: stream `(cycle_id, strategy_id)`, outcome
  `(cycle_id, strategy_id, horizon_min)`; run state in `shadow/state.json`.
- Existing files: `runner/{paths,shadow_stack,backfill,gpu_batch,analytics,stability_check,make_manifest,build}.py`.

# C. Required behaviour

## C1. MARKET_CLOSED → light heartbeat only
When `market_open == false` (or `cycle_result` indicates closed), the cycle must ONLY record a small
heartbeat / liveness record and then exit. Heartbeat must include: heartbeat, scheduler liveness,
V2 production status, shadow scheduler status, last successful cycle, next scheduled cycle,
data-source health, replay health, current strategy count. Record the idempotent status
`MARKET_CLOSED_ALREADY_RECORDED` (or equivalent). MUST skip: GPU batch, heavy analytics,
duplicate historical backfill, large scorecard recompute, and any repeated research task that
cannot produce new information. MUST NOT create any new decision / outcome / strategy sample.

## C2. MARKET_OPEN → full pipeline, auto-resume
When a valid open is detected, run the FULL pipeline
(`live → outcome backfill → strategy evaluation → analytics → lifecycle → degradation → competition → replay`)
with NO manual restart. On the first closed→open transition, record `MARKET_REOPEN_RECOVERY` and
confirm: data-time continuity, no error across the closed window, PIT normal, replay PASS, `order_send=0`.

## C3. No-op write suppression
Only update a timestamped/report file when its **content actually changes**. Static heartbeat uses a
small append-only record. Research reports must NOT be rewritten every 15 min when unchanged.

## C4. Git checkpoint policy (policy, not per-cycle action)
The runner must NOT `git commit` (never did, keep it that way). Checkpoints happen only on stage
events: first full live data stage; first full 24h; first full 48h; `STAGE_GATE_READY`; first Candidate;
first Degradation Event; first Evolution Proposal; formal architecture change. At each checkpoint the
parent will: freeze all outputs → generate `SHA256SUMS.txt` LAST → verify manifest → verify replay → commit.

## C5. Preserve existing semantics
Do not change the shadow research logic, the PIT discipline, the 17 strategies, the scorecard
definitions, or any Phase 2 conclusion. This is purely a runtime/liveness optimization.

# D. Acceptance (must be demonstrated with evidence)

1. Weekend still proves scheduler liveness every 15 min.
2. `MARKET_CLOSED` manufactures NO fake activity (no new stream/decision/outcome rows).
3. GPU does NOT run while the market is closed.
4. When the market opens, the full pipeline resumes automatically (prove via a simulated
   `market_open=True` path / injected flag — it is a weekend, so test the branch-into-open logic
   without a live market).
5. No missed cycles; replay PASS; production unchanged; `order_send=0`.
6. Git no longer produces meaningless periodic churn (report files only change on content change).

# E. Deliverables

- Patched `runner/` (build.py + any new `heartbeat.py` / helpers) implementing C1–C4.
- `OPTIMIZATION_REPORT.md` (what changed, why, before/after cycle cost, the acceptance evidence).
- Refreshed `SHA256SUMS.txt` generated LAST; `git show --name-only` scope = only `PHASE2_LIVE_EVIDENCE/`.
- `FINAL_REPORT.md` ending with: `最终状态 = OPTIMIZED_CONTINUOUS`, `Production = UNCHANGED`,
  `Shadow = RUNNING`, `Execution = 0`, and the confirmation block
  (`Production changes=0, order_send=0, V1 touched=0, V3 touched=0, Shadow execution calls=0, Replay=PASS`).
- Commit on branch `research/v2-grand-architecture-phase2`. Do NOT create/modify schedulers.
- Report prose in Chinese; IDs/filenames English. Then STOP (no auto-advance).
