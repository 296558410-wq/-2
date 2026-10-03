# CONFOUNDER_REPORT

> Source: `data/CONFOUNDER_REPORT.json`.

## 1. Version / strategy-change confound (the critical one)

V1_OLD and V1_NEW are **different strategies**, not two ages of the same one:

- V1_OLD = Hermes LLM plan engine (`answers_14`, `mtf_agreement`, `model`, `confidence`).
- V1_NEW = `BASELINE_CONTROL` mechanical map (`not_hermes_alpha=true`).

Mean after-cost net: V1_OLD = −0.39/trade, V1_NEW = −0.56/trade (diff p from `CONFOUNDER_REPORT.json`).
Any "new is better/worse" statement **confounds strategy identity with freshness**. The V1_NEW
"fresh start" is the *same one-time epoch* as its whole life, so it cannot separate fresh-start
from strategy.

## 2. Restart / reboot confound (V1_NEW)

Host restart 2026-10-01T13:52Z. Pre-restart vs post-restart after-cost means and permutation p are
in `CONFOUNDER_REPORT.json`. The prior restart audit recorded **no code change to the decision/exec
paths** in the restart window and verdict `NO_EVIDENCE_OF_RESTART_CAUSALITY`. The 7 post-restart
losses were already attributed to a risk-guard wiring gap, not to restart.

## 3. Time-of-day / day-of-week

Descriptive by-hour and by-weekday tables in `CONFOUNDER_REPORT.json`. Cells too small for
inference; no single hour/day dominates.

## 4. Version-change commits after the last trade

All V1_NEW code changes (riskguard fix 10-02T03:51Z, hardening 04:13Z, truth 04:31Z) occurred
**after** the last V1_NEW trade (last close 10-02T02:18Z). They cannot explain any V1_NEW P&L.

## 5. PIT / data confound

- V1_OLD early inputs **rotated** → `UNKNOWN` (cannot be re-verified point-in-time).
- V1_NEW has decision snapshots with `PIT_OK` but `replay_match` permanently null.
- V2 evidence `point_in_time_valid` is `unknown` on the whole registry.

## 6. Selection / design bias

- Windows were chosen **after** the fact (prior audit flagged `RESEARCH_SELECTION_BIAS`).
- Non-alpha decision layers wear the "Hermes" name (V1_NEW control arm; V2 placeholder) →
  `COMMON_DESIGN_BIAS`.

## Verdict

`CONFOUNDERS = ACTIVE`. The version-change confound alone is fatal to any clean
"fresh-start advantage" claim from the V1_OLD → V1_NEW comparison.
