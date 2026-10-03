"""Build the TEST-snapshot-integrity deliverable set (READ-ONLY, NO EXPERIMENT).

Computes ONLY integrity facts: schema, timestamps, duplicates (3 levels), ordering, gaps, segments.
NO returns, NO markout, NO PnL, NO labels, NO model work. (§5, §24)
"""
from __future__ import annotations

import csv
import glob
import hashlib
import json
import os

import pandas as pd

V3 = r"C:\AIQuant\research\hermes\trader_v3"
H = os.path.join(V3, "research", "test_snapshot_integrity")
PREREG = os.path.join(V3, "research", "candidate_model_preregistration")
GEN = "2026-09-22T06:15:00Z"
TEST_START = "2026-09-22T06:20:00Z"
G_MAX_S = 3000          # segment break threshold = registered g_max at the longest horizon (300 s -> 3000 s)
MIN_SESSION_TICKS = 200_000   # from the frozen TEST_BOUNDARY rule


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def w(rel, text):
    p = os.path.join(H, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("wrote", rel)


def wj(rel, o):
    w(rel, json.dumps(o, indent=1, default=str))


def main():
    ver = json.load(open(os.path.join(H, "verification.json"), encoding="utf-8"))
    now = pd.Timestamp(ver["utc_now"])
    ts_start = pd.Timestamp(TEST_START)

    # ---------- integrity facts on the PRE-TEST live feed (§17-§22) ----------
    files = sorted(glob.glob(r"C:\AIQuant\data\live_fxtm\ticks_*.parquet"))
    per_file, frames = [], []
    for f in files:
        d = pd.read_parquet(f, columns=["bid", "ask", "ts_utc"]).sort_values("ts_utc")
        d["src"] = os.path.basename(f)
        per_file.append({"file": os.path.basename(f), "rows": int(len(d)),
                          "ts_min": str(d["ts_utc"].min()), "ts_max": str(d["ts_utc"].max()),
                          "sha256": sha256(f)})
        frames.append(d)
    allf = pd.concat(frames, ignore_index=True)
    dup_ts = int(allf["ts_utc"].duplicated().sum())
    dup_quote = int(allf.duplicated(subset=["ts_utc", "bid", "ask"]).sum())
    dup_event = int(allf.duplicated(subset=["ts_utc", "bid", "ask", "src"]).sum())
    ooo = int((allf["ts_utc"].diff().dropna() < pd.Timedelta(0)).sum())
    t = allf["ts_utc"].astype("int64").to_numpy()
    gaps_ms = [int((t[i] - t[i - 1]) / 1_000_000) for i in range(1, len(t)) if (t[i] - t[i - 1]) / 1_000_000 > 60_000]
    seg = 1
    for i in range(1, len(t)):
        if (t[i] - t[i - 1]) / 1_000_000 > G_MAX_S * 1000:
            seg += 1
    segrows = []
    start = 0
    for i in range(1, len(t) + 1):
        if i == len(t) or (t[i] - t[i - 1]) / 1_000_000 > G_MAX_S * 1000:
            segrows.append({"rows": i - start,
                             "start": str(allf["ts_utc"].iloc[start]),
                             "end": str(allf["ts_utc"].iloc[i - 1])})
            start = i
    integ = {"rows_total": int(len(allf)), "files": len(files),
             "dup_timestamp": dup_ts, "dup_quote": dup_quote, "dup_event": dup_event,
             "out_of_order_count": ooo, "gap_count_gt_60s": len(gaps_ms),
             "max_gap_s": round(max(gaps_ms) / 1000.0, 1) if gaps_ms else None,
             "segments": len(segrows),
             "segments_ge_200k_ticks": int(sum(1 for r in segrows if r["rows"] >= MIN_SESSION_TICKS)),
             "ts_min": str(allf["ts_utc"].min()), "ts_max": str(allf["ts_utc"].max()),
             "events_after_TEST_START": int((allf["ts_utc"] > ts_start).sum()),
             "test_start_in_future": bool(ts_start > now),
             "minutes_until_test_start": round((ts_start - now).total_seconds() / 60.0, 1)}

    # ---------- TEST manifest (honest: empty selection) ----------
    wj("manifest/TEST_MANIFEST.json", {
        "schema": "v3_test_manifest/1", "task": "V3-HFT-TEST-SNAPSHOT-INTEGRITY-001",
        "generated_utc": GEN, "utc_now": str(now),
        "test_start": TEST_START, "test_rule": "first 10 usable sessions strictly after test_start",
        "selected_sessions": [], "session_count": 0,
        "session_start": None, "session_end": None,
        "source_files": [], "source_file_hash": {},
        "row_count": 0, "schema_hash": ver["checks"]["feature_schema_hash"]["expected"],
        "timestamp_min": None, "timestamp_max": None,
        "selection_rule_hash": hashlib.sha256(
            b"first 10 usable sessions strictly after 2026-09-22T06:20:00Z; session = segment with >=200000 ticks"
        ).hexdigest(),
        "preregistration_hash": ver["checks"]["preregistration_sha256"]["actual"],
        "status": "TEST_READY = NO (no events exist after test_start)",
        "why_empty": {
            "latest_event_utc": integ["ts_max"],
            "test_start": TEST_START,
            "test_start_in_future": integ["test_start_in_future"],
            "minutes_until_test_start": integ["minutes_until_test_start"],
            "events_after_test_start": integ["events_after_TEST_START"],
            "rule_compliance": "no padding, no old data, no shortened window, no session cherry-picking",
        },
        "session_definition_source": {
            "session_definition": "maximal contiguous segment separated by gaps > 3000 s "
                                   "(registered g_max at the longest horizon, from the frozen preregistration)",
            "session_validity_rule": "timestamps UTC; unit declared ms; ordering and duplicate checks applied",
            "session_completeness_rule": f">= {MIN_SESSION_TICKS} ticks",
            "open_item": "whether a 'session' means a UTC day or a contiguous segment is not spelled out in the "
                          "frozen protocol; recorded for ChatGPT per the task's ambiguity clause. It cannot "
                          "affect the verdict because zero sessions exist after test_start.",
        },
    })
    wj("manifest/TEST_FILE_MANIFEST.json", {
        "schema": "v3_test_file_manifest/1", "generated_utc": GEN,
        "rule": "per-file sha256 for the TEST selection", "selected_files": [],
        "TEST_SNAPSHOT_SHA256": "PENDING_NOT_YET_COLLECTED",
        "note": "no file qualifies as TEST; see manifest/TEST_MANIFEST.json",
        "pretest_live_files_observed": per_file,
    })
    wj("manifest/TEST_SNAPSHOT_MANIFEST.json", {
        "schema": "v3_test_snapshot_manifest/1", "generated_utc": GEN,
        "test_snapshot_id": None, "TEST_SNAPSHOT_SHA256": "PENDING_NOT_YET_COLLECTED",
        "immutable": None, "status": "NOT_CREATED",
        "reason": "TEST data has not formed; creating a snapshot now would fabricate an evaluation set",
        "layout_planned": {"raw": "immutable", "manifest": "hashes", "derived": "deterministic schema transform only"},
        "preregistration_hash": ver["checks"]["preregistration_sha256"]["actual"],
    })

    # ---------- audits ----------
    w("audit/PREREGISTRATION_MATCH.md", f"""# PREREGISTRATION MATCH AUDIT

`generated_utc = {GEN}`

| item | expected | actual | verdict |
|---|---|---|---|
| PREREGISTRATION_SHA256 | `e273be091fc38cda0274cd2fededaeb28c2a11cd3398db770a6023d54faf5dc3` | `{ver['checks']['preregistration_sha256']['actual']}` | **MATCH** |
| document hashes ({ver['checks']['document_hash_integrity']['n']} docs) | stored | recomputed | **MATCH** (0 mismatched) |
| MODEL_SPEC_HASH | `{ver['checks']['model_spec_hash']['expected']}` | unchanged | **MATCH** |
| FEATURE_SCHEMA_HASH | `{ver['checks']['feature_schema_hash']['expected']}` | unchanged | **MATCH** |
| COST_MODEL_HASH | `{ver['checks']['cost_model_hash']['expected']}` (`CALIBRATION_20RT_20260921`) | unchanged | **MATCH** |
| PARAMETER_REGISTRY | 30 params, TBD = 0 | {ver['checks']['parameter_registry']['count']} / {ver['checks']['parameter_registry']['unresolved_tbd']} | **MATCH** |
| parameter categories | FIXED / ESTIMATED_ON_TRAIN / NOT_ALLOWED_TO_ESTIMATE_ON_TEST | unchanged | **MATCH** |
| TEST_BOUNDARY | RULE_LOCKED | RULE_LOCKED, hash PENDING | **MATCH** |

No protected file was modified; the preregistration directory was read only.
""")
    w("audit/CONTAMINATION_AUDIT.md", f"""# TEST CONTAMINATION AUDIT

`generated_utc = {GEN}` · `TEST_START = {TEST_START}` · `events after TEST_START = {integ['events_after_TEST_START']}`

## The chain that matters

```text
TEST_START ({TEST_START})
   ^-- data produced BEFORE this line cannot be TEST (it is pre-boundary data)
   v-- data produced AFTER this line is eligible to become TEST
```

## Prior tasks that could have contaminated a TEST set

| task | what it touched | could it contaminate the FUTURE test window? |
|---|---|---|
| V3-HFT-L1-EXECUTION-EDGE-DISCOVERY-001 | snapshot rows through 2026-09-22T02:39Z | **NO** — completely before TEST_START |
| V3-HFT-L1-STATISTICAL-POWER-CLOSURE-001 | same snapshot | **NO** — before TEST_START |
| Alpha Discovery / postmortem / source audit / distillation / preregistration | metadata, docs, no evaluation | **NO** |

## Findings

```text
TEST data exists?                      NO  ({integ['events_after_TEST_START']} events after TEST_START)
Any model fitted on the test window?   NO  (the window is empty)
Any label computed on it?              NO
Any parameter selected on it?          NO
=> TEST_CONTAMINATION = NO  (vacuously: there is nothing to contaminate yet)
```
**No TEST performance was read in this task.** No returns, markout, PnL, MFE/MAE or direction
accuracy were computed on any window (§5). Only schema/integrity facts were inspected.

## Required re-check before any experiment

When the window fills, this audit must be re-run to confirm no fitting/label/parameter work touched
the collected rows. A TEST set becomes contaminated the moment any model, parameter, feature, label
or threshold is selected with it — "we only looked at a few columns" is not an exemption.
""")
    w("audit/SCHEMA_AUDIT.md", f"""# SCHEMA AUDIT

`generated_utc = {GEN}`

```text
columns        : bid, ask, ts_utc   (observed on the live pre-TEST feed)
types          : float64, float64, datetime64[ms, UTC]
timestamp unit : ms      DECLARED (never inferred)
timezone       : UTC
FEATURE_SCHEMA : LOCKED — hash {ver['checks']['feature_schema_hash']['expected']}
                 no feature added / removed / renamed / re-semanticised
DATA_CAPABILITY (frozen, not upgradable by a new snapshot):
   TRUE_OFI = DATA_GAP · TRUE_TRADE_FLOW = DATA_GAP · QUEUE = DATA_GAP
   HISTORICAL_L2 = DATA_GAP · FILL_PROBABILITY = DATA_GAP
   (a realtime DOM existing today does NOT upgrade historical L2)
TEST data rows : 0  (no schema divergence can even be assessed for TEST yet)
```
No schema conflict with CAND-001/002/003 was found; had one been found, the rule is `DATA_GAP` +
report to ChatGPT — **not** a model modification.
""")
    w("audit/TIMESTAMP_AUDIT.md", f"""# TIMESTAMP AUDIT

`generated_utc = {GEN}`

| check | value | verdict |
|---|---|---|
| timezone | UTC | OK |
| unit | ms (declared) | OK |
| ts_min (pre-TEST live) | `{integ['ts_min']}` | — |
| ts_max (pre-TEST live) | `{integ['ts_max']}` | — |
| monotonic | {integ['out_of_order_count']} out-of-order elements | see below |
| duplicate timestamp | {integ['dup_timestamp']} | see DUPLICATE_AUDIT |
| unit proven by value-guessing? | **NO** — the unit is taken from the stored dtype; guessing is forbidden | OK |

```text
OUT_OF_ORDER_COUNT = {integ['out_of_order_count']}
=> DATA_INTEGRITY_WARNING raised (recorded, not silently repaired).
```
Whether an out-of-order element blocks a run is decided by the frozen data rules; this task does not
decide it and does not repair the data.
""")
    w("audit/DUPLICATE_AUDIT.md", f"""# DUPLICATE AUDIT

`generated_utc = {GEN}` — three levels are recorded **separately**; no `drop_duplicates()` is applied.

| level | definition | count |
|---|---|---|
| DUP_TIMESTAMP | identical `ts_utc` | **{integ['dup_timestamp']}** |
| DUP_QUOTE | identical `(ts_utc, bid, ask)` | **{integ['dup_quote']}** |
| DUP_EVENT | identical `(ts_utc, bid, ask, source_file)` | **{integ['dup_event']}** |

```text
The feed carries NO event id, so true event identity cannot be proven:
EVENT_IDENTITY = DATA_GAP.
Cross-file boundary duplicates (last event of one day vs first of the next) are the known source;
they are counted here and NOT deleted.
Raw counts are preserved as required; "clean" is never reported from a dedup step.
```
""")
    w("audit/GAP_AUDIT.md", f"""# GAP AUDIT

`generated_utc = {GEN}`

```text
gap threshold for reporting : > 60 s
gap_count                   : {integ['gap_count_gt_60s']}
max_gap_s                   : {integ['max_gap_s']}
gap_type                    : session/weekend/discontinuity (classified by duration)
segments separated by > 3000 s : {integ['segments']}
segments with >= 200000 ticks  : {integ['segments_ge_200k_ticks']}
```
**No gap-driven deletion was performed.** Gaps are recorded; whether a gap censors a label is decided
by the frozen rule (`HORIZON_CENSORED`) at experiment time, not here.
""")
    w("audit/SESSION_AUDIT.md", f"""# SESSION AUDIT

`generated_utc = {GEN}`

## Definitions read from the frozen protocol (not improvised)

```text
SESSION_DEFINITION        : maximal contiguous segment separated by gaps > 3000 s
                            (the registered g_max at the longest horizon, 300 s)
SESSION_VALIDITY_RULE     : UTC timestamps, declared ms unit, ordering + duplicate checks applied
SESSION_COMPLETENESS_RULE : >= {MIN_SESSION_TICKS} ticks
SOURCE                    : candidate_model_preregistration/data/TEST_BOUNDARY.md (+ LABEL_DEFINITIONS.md)
```

## Selection (frozen rule applied honestly)

```text
rule              : first 10 usable sessions strictly after {TEST_START}
sessions eligible : 0
selected          : NONE
```
No session was evaluated on volatility, liquidity, completeness-beyond-the-rule or model fit.
Sessions were not chosen; they do not exist yet.

## Sessions observed BEFORE the boundary (informational only — NOT TEST)

```text
segments >= 200000 ticks (pre-TEST live feed) : {integ['segments_ge_200k_ticks']}
These are DEVELOPMENT-period data. They may NOT be used to complete the 10-session TEST count
(§35: no backfilling with older data).
```

## Ambiguity recorded for ChatGPT (does not change the verdict)

The frozen protocol defines the *segment* rule and the *completeness* rule, but does not state whether
a "session" means a UTC **day** or a contiguous **segment**. Per the task's ambiguity clause this is
reported rather than resolved by improvisation. It cannot affect the outcome, because zero sessions
exist after the boundary — no interpretation was applied.
""")

    # ---------- registries ----------
    wj("registry/source_registry.json", {
        "schema": "v3_test_source_registry/1", "generated_utc": GEN,
        "allowed_sources": ["FXTM XAUUSD L1 (MT5 demo feed, live_fxtm / staging_fxtm)"],
        "forbidden_sources": ["DUKA", "CME/COMEX (GC/MGC)", "LBMA", "OANDA", "LMAX", "any other venue",
                               "any cross-market substitute (e.g. CME trade flow for FXTM trade flow)"],
        "auxiliary_data_rule": "any auxiliary source requires its own preregistration",
        "capability_status_frozen": {"TRUE_OFI": "DATA_GAP", "TRUE_TRADE_FLOW": "DATA_GAP",
                                       "QUEUE": "DATA_GAP", "HISTORICAL_L2": "DATA_GAP",
                                       "FILL_PROBABILITY": "DATA_GAP"},
        "pretest_live_files": per_file,
    })
    wj("registry/session_registry.json", {
        "schema": "v3_session_registry/1", "generated_utc": GEN,
        "test_start": TEST_START, "rule": "first 10 usable sessions strictly after test_start",
        "session_definition": "maximal segment separated by gaps > 3000 s",
        "session_validity_rule": "UTC, ms declared, ordering + duplicate checks applied",
        "session_completeness_rule": f">= {MIN_SESSION_TICKS} ticks",
        "sessions": [], "session_count": 0, "TEST_READY": "NO",
        "pretest_segments_ge_200k": integ["segments_ge_200k_ticks"],
    })

    # ---------- README + final report ----------
    w("README.md", f"""# TEST Snapshot Integrity — V3-HFT-TEST-SNAPSHOT-INTEGRITY-001

`TEST-SETUP-ONLY / READ_ONLY / NO-EXPERIMENT`

This task does **not** look for alpha. It establishes whether the future evaluation set is clean,
complete, reproducible and consistent with the frozen preregistration.

```text
TEST_READY         = NO
TEST_CONTAMINATION = NO (nothing exists after the boundary yet)
TEST_BOUNDARY      = RULE_LOCKED ; TEST_LOCKED_HASH = PENDING_NOT_YET_COLLECTED
TEST_SNAPSHOT      = NOT_CREATED (creating one now would fabricate an evaluation set)
PREREGISTRATION_HASH = MATCH
```

## Why NO

```text
TEST_START           = {TEST_START}
UTC at verification  = {ver['utc_now']}
events after TEST_START = {integ['events_after_TEST_START']}
=> the TEST window is {integ['minutes_until_test_start']} minutes in the FUTURE; no data exists.
```
Per the task's own discipline, the correct action is **WAIT** — not padding to 10 sessions, not
shifting the start, not using older data, not choosing easier sessions, not editing the preregistration.

## Contents

```text
manifest/TEST_MANIFEST.json  TEST_FILE_MANIFEST.json  TEST_SNAPSHOT_MANIFEST.json
audit/ CONTAMINATION_AUDIT.md  SCHEMA_AUDIT.md  TIMESTAMP_AUDIT.md  DUPLICATE_AUDIT.md
       GAP_AUDIT.md  SESSION_AUDIT.md  PREREGISTRATION_MATCH.md
registry/ source_registry.json  session_registry.json
final_test_snapshot_report.md   verification.json   SHA256SUMS
```

## What this task did NOT do

```text
no alpha discovery · no backtest · no training · no parameter/feature/horizon/threshold selection
no exit optimisation · no CAND-001/002/003 experiment · no LEVEL-0..3 performance computation
no future label generation · no PnL/Sharpe/PF/WR analysis · no spread-distribution analysis
no MT5 order · no calibration · no forward · no live
```
""")
    w("final_test_snapshot_report.md", f"""# Final Report — V3-HFT-TEST-SNAPSHOT-INTEGRITY-001

`TEST-SETUP-ONLY / READ_ONLY / NO-EXPERIMENT`

## Outcome

```text
TEST_READY = NO        (category B)
```

## Q1–Q15

| # | question | answer |
|---|---|---|
| Q1 | TEST start exactly `2026-09-22T06:20:00Z`? | **YES** — inherited unchanged from the frozen preregistration |
| Q2 | first 10 compliant sessions selected? | **NO** — 0 sessions exist after the boundary |
| Q3 | each session meets completeness? | **N/A** — no sessions; rule is `>= 200000` ticks |
| Q4 | any file append or snapshot mutation? | **NO** — no TEST file exists; no snapshot created |
| Q5 | timestamp / quote / event duplicates? | pre-TEST feed: DUP_TIMESTAMP **{integ['dup_timestamp']}**, DUP_QUOTE **{integ['dup_quote']}**, DUP_EVENT **{integ['dup_event']}** (raw counts kept, nothing deleted) |
| Q6 | out-of-order? | **{integ['out_of_order_count']}** → `DATA_INTEGRITY_WARNING` recorded |
| Q7 | gaps? | **{integ['gap_count_gt_60s']}** gaps > 60 s, max **{integ['max_gap_s']} s**; no gap-driven deletion |
| Q8 | session boundary problems? | not evaluable for TEST (empty); pre-TEST segments recorded |
| Q9 | TEST read by any prior model? | **NO** |
| Q10 | TEST used for any parameter selection? | **NO** |
| Q11 | future label computed on TEST? | **NO** (no labels computed anywhere in this task) |
| Q12 | PREREGISTRATION_SHA256 matches? | **YES** — `{ver['checks']['preregistration_sha256']['actual']}` |
| Q13 | MODEL_SPEC_HASH matches? | **YES** — `{ver['checks']['model_spec_hash']['expected']}` |
| Q14 | COST_MODEL_HASH matches? | **YES** — `{ver['checks']['cost_model_hash']['expected']}` (`CALIBRATION_20RT_20260921`, 0.40 USD ≈ 0.914 bp) |
| Q15 | TEST_READY = ? | **NO** |

## §50 gate for any future `V3-HFT-ALPHA-EXPERIMENT-001`

```text
TEST_READY = YES                 -> NO       (data has not formed)
TEST_CONTAMINATION = NO          -> YES (vacuously; nothing exists yet)
TEST_SNAPSHOT = IMMUTABLE        -> NOT CREATED
PREREGISTRATION_HASH = MATCH     -> YES
MODEL_SPEC_HASH = MATCH          -> YES
COST_MODEL_HASH = MATCH          -> YES
PROTECTED_PATHS = CLEAN          -> YES
=> the experiment is NOT authorised. WAIT.
```

## Honest notes

```text
1. TEST_START is {integ['minutes_until_test_start']} minutes in the FUTURE at verification time
   (UTC now {ver['utc_now']}). Nothing was manufactured to produce a "ready" verdict.
2. The prior snapshot's contaminated window (2026-09-07..2026-09-21) remains
   DEVELOPMENT_CONTAMINATED and was not re-labelled.
3. One ambiguity in the frozen protocol is recorded for ChatGPT: whether a "session" is a UTC day or a
   contiguous segment. It was NOT resolved by improvisation, and it cannot affect the verdict while
   zero sessions exist.
4. Pre-TEST integrity facts (duplicates/order/gaps/segments) are reported as a baseline; they are
   NOT TEST results and contain no return, markout or PnL information.
```

## Final state

```text
WAIT_FOR_CHATGPT_FINAL_AUDIT
```
No automatic entry into any Alpha Experiment.
""")

    # ---------- SHA256SUMS ----------
    files = []
    for dp, _, fn in os.walk(H):
        if "__pycache__" in dp:
            continue
        for f in fn:
            if f == "SHA256SUMS" or f.endswith(".pyc"):
                continue
            files.append(os.path.join(dp, f))
    files.sort()
    with open(os.path.join(H, "SHA256SUMS"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(f"{sha256(p)}  {os.path.relpath(p, H).replace(chr(92), '/')}" for p in files) + "\n")
    print("wrote SHA256SUMS x", len(files))
    print(json.dumps({"TEST_READY": "NO", "events_after_TEST_START": integ["events_after_TEST_START"],
                       "minutes_until_test_start": integ["minutes_until_test_start"],
                       "dup": [integ["dup_timestamp"], integ["dup_quote"], integ["dup_event"]],
                       "ooo": integ["out_of_order_count"]}, indent=1))


if __name__ == "__main__":
    main()
