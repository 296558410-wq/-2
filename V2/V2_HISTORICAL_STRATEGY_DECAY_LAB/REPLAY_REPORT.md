# REPLAY_REPORT

> Source: `data/REPLAY.json`. Question: does the **reference decision path reproduce production**,
> and on which cycles — or explicitly report it could not.

## Per system

| System | replay status | cycles | detail |
|---|---|---|---|
| **V1_OLD** | **NOT_POSSIBLE** | — | no Hermes input snapshots preserved (pre-reset state rotated to archive; class-E DATA_GAP). Cannot reproduce any V1_OLD decision. |
| **V1_NEW** | **INPUT_HASH_ONLY** | 403 ledger DECISION + 34 truth snapshots | `hermes_input_hash` + per-snapshot sha256 stored, but input **body not stored** → output replay not performed; ledger `replay_match` field permanently `null`. One 2026-09-14 cycle recorded `replay MATCH` (mechanical control-arm map). |
| **V2_PAPER_SHADOW** | **REPRODUCES_PRODUCTION** | **120/120 cycles** | the shadow `reference_rules` side = production `decide_pure(source=reference_rules)`; three-way shadow over the same 120 PIT cycles: reference → production **120/120 = 100.0 %**, discovery `picks_changed = 0`, `order_send = 0`. Phase-3 pre/post code change: ledger sha unchanged (`9b8b51c5dc774454`, 12 lines), outcome engine 360/360 OK. |
| **V3_CALIBRATION** | NOT_EVALUABLE | — | execution disabled. |

## Important qualifier

The V2 reproduction is of the **deterministic `reference_rules` placeholder**, not of a live LLM agent.
The `true_llm_agent` side was `LLM_UNAVAILABLE` on all 120 cycles (no usable endpoint —
`LLM_PROVENANCE.md`). So "reproduces production" means the *mechanical reference* is faithful; it does
**not** mean a Hermes LLM decision path was reproduced.

The G3 provenance replay had `replay_mismatch = []` but overall verdict **FAIL** (one
`provenance_missing = DEC-ctx_4cd398fb0547.json`).

## Conclusion

- Where inputs were preserved (V2 shadow), the reference path reproduces production **100 % on all
  120 cycles**.
- Where inputs were not preserved (V1_OLD), reproduction is **NOT_POSSIBLE** (reported honestly).
- V1_NEW is **input-hash-only**.
- `order_send = 0` throughout; no CLI order calls in any lab script.
