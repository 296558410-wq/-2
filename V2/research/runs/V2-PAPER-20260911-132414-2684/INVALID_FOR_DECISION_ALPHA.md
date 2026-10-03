# STATUS MARKER — INVALID_FOR_DECISION_ALPHA

REASON: FRESHNESS_INPUT_PATH_DEFECT (context.py ROOT resolved to research/hermes instead of trader_v2;
Hermes gate therefore received agent1/agent2 freshness="unknown" every cycle → structurally WAIT-only).

This run is preserved as a valid DEFECT EXPERIMENT RECORD.
- Original events NOT modified, NOT deleted.
- Valid for: safety/isolation/ledger-integrity/replay evidence.
- NOT valid for: decision alpha (decision path input was defective).

Fixed in commit 933dbd2; superseded by a new run_id (see state/runs/ACTIVE.json).
