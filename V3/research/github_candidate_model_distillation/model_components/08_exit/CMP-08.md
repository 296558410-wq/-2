# CMP-08 — exit

- source_repo: AshJha0/electronic-trading (IS/opportunity); snowkings (remaining-hold accounting); KlishevDA (markout curves)
- source_commit: HEAD_AT_AUDIT_2026-09-22
- evidence_level: **E4**
- FXTM_compatibility: COMPATIBLE (L1)
- parameters: TBD_IN_PRE_REGISTERED_EXPERIMENT

## mechanism

Exit when the expected REMAINING edge falls below the expected exit cost; four failure classes kept separate.

## required_data

current state, position, elapsed time, cost of a second crossing

## formula

```
EXIT iff E[remaining_edge(t)] < E[exit_cost] ; E[t] functional form = TBD (see EDGE_DECAY_MODEL)
```

## assumption

exit cost must count the second spread crossing + commission; remaining_hold = horizon - elapsed (nonpositive -> unavailable)

## failure_mode

fixed TP/SL that ignores decay; exiting on realised PnL instead of expected remaining edge

## FXTM note

Usable on the current FXTM L1 feed.
