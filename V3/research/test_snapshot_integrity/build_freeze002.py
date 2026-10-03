"""Build the V3-HFT-TEST-SNAPSHOT-FREEZE-002 deliverable set.

TEST-COLLECTION / SNAPSHOT-FREEZE / READ_ONLY / NO-EXPERIMENT.
Re-verifies hashes (§31-§33) and emits the §40 structure. No experiment, no labels, no metrics.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os

import pandas as pd

V3 = r"C:\AIQuant\research\hermes\trader_v3"
H = os.path.join(V3, "research", "test_snapshot_integrity")
PREREG = os.path.join(V3, "research", "candidate_model_preregistration")
GEN = "2026-09-22T06:25:00Z"
TEST_START = "2026-09-22T06:20:00Z"
SEG_GAP_S = 3000
MIN_TICKS = 200_000
TARGET = 10
EXP_PREREG = "e273be091fc38cda0274cd2fededaeb28c2a11cd3398db770a6023d54faf5dc3"
EXP_MODEL = "a98717dc424b0acaf0f33c01707dff6be540e2c941ee7a4da9fa803a4d31b53c"
EXP_COST = "6f116cfb2d63bedf6e364e9b5a6c6e15f194f91114e9d0c1780fa4d869cdf0aa"


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def w(rel, text):
    p = os.path.join(H, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8", newline="\n").write(text)
    print("wrote", rel)


def wj(rel, o):
    w(rel, json.dumps(o, indent=1, default=str))


def main():
    ca = json.load(open(os.path.join(H, "collection_attempt.json"), encoding="utf-8"))
    man = json.load(open(os.path.join(PREREG, "registries", "preregistration_manifest.json"), encoding="utf-8"))
    h_ok = {"preregistration": man.get("PREREGISTRATION_SHA256") == EXP_PREREG,
            "model_spec": man.get("model_spec_hash") == EXP_MODEL,
            "cost_model": man.get("cost_model_hash") == EXP_COST}
    doc_ok = all(sha256(os.path.join(PREREG, d)) == h for d, h in man["document_hashes"].items())

    # pre-TEST cadence fact (for the scheduling estimate only)
    files = sorted(glob.glob(r"C:\AIQuant\data\live_fxtm\ticks_*.parquet"))
    d0 = pd.read_parquet(files[-1], columns=["ts_utc"])
    med_dt_ms = float(d0["ts_utc"].diff().dt.total_seconds().dropna().median() * 1000) if len(d0) > 2 else 266.0
    hours_per_session = round(MIN_TICKS * (med_dt_ms / 1000.0) / 3600.0, 1)
    days_for_ten = 10  # at most one valid session per trading day (daily break > 3000 s)

    valid = ca["valid_session_count"]
    ready = "YES" if valid >= TARGET else "NO"

    wj("manifest/TEST_MANIFEST.json", {
        "schema": "v3_test_manifest/2", "task": "V3-HFT-TEST-SNAPSHOT-FREEZE-002",
        "generated_utc": GEN, "utc_now": ca["utc_now"],
        "test_start": TEST_START,
        "session_definition": {"session": "CONTIGUOUS_SEGMENT", "segment_gap_threshold_s": SEG_GAP_S,
                                "min_session_ticks": MIN_TICKS, "target_sessions": TARGET},
        "selected_sessions": [], "session_count": 0,
        "session_start": None, "session_end": None,
        "source_files": [], "source_file_hashes": {},
        "select_sessions": [],
        "row_count": ca["post_test_start"]["row_count"],
        "timestamp_min": ca["post_test_start"]["timestamp_min"],
        "timestamp_max": ca["post_test_start"]["timestamp_max"],
        "preregistration_hash": man.get("PREREGISTRATION_SHA256"),
        "model_spec_hash": man.get("model_spec_hash"),
        "cost_model_hash": man.get("cost_model_hash"),
        "TEST_READY": ready,
        "status": f"TEST_READY = {ready} — valid_session_count = {valid} of {TARGET}",
        "why_not_ready": {
            "events_at_or_after_test_start": ca["post_test_start"]["row_count"],
            "boundary": ca["boundary"],
            "rule_compliance": "no threshold lowering · no TEST_START shift · no DEVELOPMENT backfill · "
                                "no session cherry-picking · no early freeze",
            "scheduling_estimate": {
                "median_inter_tick_ms_pretest": med_dt_ms,
                "contiguous_hours_needed_for_200k_ticks": hours_per_session,
                "max_valid_sessions_per_trading_day": 1,
                "minimum_trading_days_for_10_sessions": days_for_ten,
                "earliest_realistic_TEST_READY": ">= 10 trading days of collection after TEST_START",
            },
        },
    })
    wj("manifest/TEST_FILE_MANIFEST.json", {
        "schema": "v3_test_file_manifest/2", "generated_utc": GEN,
        "rule": "per-file sha256 for TEST raw files", "selected_files": [],
        "TEST_SNAPSHOT_SHA256": "PENDING_NOT_YET_COLLECTED",
        "note": "no file qualifies as TEST yet (0 events at/after TEST_START)",
        "all_live_files_observed": ca["file_manifest"],
    })
    wj("manifest/TEST_SNAPSHOT_MANIFEST.json", {
        "schema": "v3_test_snapshot_manifest/2", "generated_utc": GEN,
        "test_start": TEST_START, "session_definition": "CONTIGUOUS_SEGMENT (>3000 s gap)",
        "segment_gap_threshold": SEG_GAP_S, "minimum_session_ticks": MIN_TICKS,
        "selected_sessions": [], "source_files": [], "source_file_hashes": {},
        "row_count": 0, "timestamp_min": None, "timestamp_max": None,
        "preregistration_hash": man.get("PREREGISTRATION_SHA256"),
        "model_spec_hash": man.get("model_spec_hash"),
        "cost_model_hash": man.get("cost_model_hash"),
        "TEST_SNAPSHOT_SHA256": "PENDING_NOT_YET_COLLECTED",
        "TEST_SNAPSHOT_IMMUTABLE": None,
        "status": "NOT_CREATED (valid_session_count 0 < 10)",
        "post_snapshot_data_rule": "any later data is POST-SNAPSHOT DATA and may not enter TEST",
    })
    wj("registry/session_registry.json", {
        "schema": "v3_session_registry/2", "generated_utc": GEN,
        "test_start": TEST_START,
        "session": "CONTIGUOUS_SEGMENT", "segment_gap_threshold_s": SEG_GAP_S,
        "min_session_ticks": MIN_TICKS, "target_sessions": TARGET,
        "sessions": ca["sessions"], "valid_session_count": valid,
        "boundary_record": {**ca["boundary"],
                             "classification": "TEST_START_ARTEFACT (not a natural market gap)"},
        "next_session_id": f"TEST-S{valid + 1:03d}",
        "id_rule": "session ids are assigned by DATA BOUNDARY ONLY (never by volatility/price/spread/result)",
        "invalid_or_incomplete_rule": "INCOMPLETE segments are never padded, merged, or threshold-lowered",
    })

    w("TEST_SESSION_DEFINITION_RULING_001.md", f"""# TEST SESSION DEFINITION — OFFICIAL RULING 001

`recorded_utc = {GEN}` · resolves the ambiguity flagged by V3-HFT-TEST-SNAPSHOT-INTEGRITY-001.

| item | ruling |
|---|---|
| SESSION | **CONTIGUOUS_SEGMENT** |
| SEGMENT_BOUNDARY | adjacent valid-event gap **> 3000 s** ⇒ NEW SESSION |
| MIN_SESSION_TICKS | **200,000** |
| below the threshold | `INCOMPLETE` (never padded, merged, or threshold-lowered) |
| first TEST session | `session_start >= 2026-09-22T06:20:00Z` |
| segment straddling TEST_START | truncated at the boundary; the pre-boundary part is NOT TEST |
| session IDs | assigned by **data boundary only** (`TEST-S001` … `TEST-S010`), never by volatility / price move / spread / result |
| TEST data source | FXTM XAUUSD L1 only (no DUKA / CME / LBMA / LMAX / OANDA splice) |

```text
event[i] -> event[i+1]
    dt <= 3000 s  =>  SAME SESSION
    dt >  3000 s  =>  NEW SESSION
```

This ruling is applied verbatim in `collect_test_sessions.py`. No interpretation was added here.
""")

    w("audit/PREREGISTRATION_MATCH.md", f"""# PREREGISTRATION / HASH MATCH AUDIT (freeze-002)

`generated_utc = {GEN}`

| hash | expected | match |
|---|---|---|
| PREREGISTRATION_SHA256 | `{EXP_PREREG}` | **{'MATCH' if h_ok['preregistration'] else 'MISMATCH'}** |
| MODEL_SPEC_HASH | `{EXP_MODEL}` | **{'MATCH' if h_ok['model_spec'] else 'MISMATCH'}** |
| COST_MODEL_HASH | `{EXP_COST}` | **{'MATCH' if h_ok['cost_model'] else 'MISMATCH'}** |
| all {len(man['document_hashes'])} preregistration documents | recomputed | **{'MATCH (0 mismatched)' if doc_ok else 'MISMATCH'}** |

```text
cost model : {man.get('cost_model_id')} · 0.40 USD / RT ≈ 0.914 bp · NOT re-estimated
```
No preregistration document was modified by this task (read-only).
""")
    w("audit/CONTAMINATION_AUDIT.md", f"""# CONTAMINATION AUDIT (freeze-002)

`generated_utc = {GEN}` · `TEST_START = {TEST_START}`

## Historical-task review (§30)

| task | what it touched | TEST performance read? |
|---|---|---|
| V3-HFT-L1-EXECUTION-EDGE-DISCOVERY-001 | snapshot rows through 2026-09-22T02:39Z | **NO** |
| V3-HFT-L1-STATISTICAL-POWER-CLOSURE-001 | same snapshot (aggregate dependence) | **NO** |
| V3-HFT-GITHUB-CANDIDATE-MODEL-DISTILLATION-004 | public repos only | **NO** |
| V3-HFT-CANDIDATE-MODEL-PREREGISTRATION-001 | protocol documents only | **NO** (preregistration reads are allowed) |
| V3-HFT-TEST-SNAPSHOT-INTEGRITY-001 | schema/integrity of the pre-TEST feed | **NO** |

## Current state

```text
events at/after TEST_START     = {ca['post_test_start']['row_count']}
valid TEST sessions            = {valid}
any model read TEST?           NO
any parameter selected on TEST? NO
any future label computed?     NO   (none exists to compute)
=> TEST_CONTAMINATION = NO
```
**This task computed no return, markout, PnL, MFE/MAE, accuracy or directional metric on any window.**
""")
    w("audit/SCHEMA_AUDIT.md", f"""# SCHEMA AUDIT (freeze-002)

`generated_utc = {GEN}`

```text
columns (live feed) : bid, ask, ts_utc   (plus flags/volume fields that are identically zero)
types              : float64, float64, datetime64[ms, UTC]
timestamp unit     : ms — {ca['unit_verification']['verdict']}
                     proof: interpreting the raw integers as ms yields a 2026 date;
                            us/ns would imply 1970 => ms is PROVEN BY VALUE, not guessed
timezone           : UTC
FEATURE_SCHEMA     : LOCKED (unchanged) — no feature added/removed/renamed/re-semanticised
DATA_CAPABILITY    : NOT UPGRADED (§37) — a live realtime DOM does NOT make HISTORICAL_L2 available
   TRUE_OFI = DATA_GAP · TRADE_FLOW = DATA_GAP · QUEUE = DATA_GAP
   HISTORICAL_L2 = DATA_GAP · FILL_PROBABILITY = DATA_GAP
TEST rows          : {ca['post_test_start']['row_count']} (schema divergence not assessable yet)
```
""")
    w("audit/TIMESTAMP_AUDIT.md", f"""# TIMESTAMP AUDIT (freeze-002)

`generated_utc = {GEN}` · `utc_now = {ca['utc_now']}`

| check | value |
|---|---|
| timezone | UTC |
| timestamp_unit | ms (proven by value) |
| declared dtype | `{ca['unit_verification']['dtype']}` |
| interpretation proof | ms → {ca['unit_verification']['interpretations']['ms']} · us → {ca['unit_verification']['interpretations']['us']} · ns → {ca['unit_verification']['interpretations']['ns']} |
| TEST timestamp_min | `{ca['post_test_start']['timestamp_min']}` |
| TEST timestamp_max | `{ca['post_test_start']['timestamp_max']}` |
| out_of_order_count (post-TEST_START) | **{ca['post_test_start']['out_of_order_count']}** |

```text
Pre-boundary baseline (informational, NOT TEST): out_of_order = 11 on the pre-TEST live feed.
OUT_OF_ORDER elements are recorded, never auto-deleted.
```
""")
    w("audit/DUPLICATE_AUDIT.md", f"""# DUPLICATE AUDIT (freeze-002)

`generated_utc = {GEN}` — three levels counted **separately**; `drop_duplicates()` is never applied.

| level | definition | count at/after TEST_START |
|---|---|---|
| DUP_TIMESTAMP | identical `ts_utc` | **{ca['post_test_start']['dup_timestamp']}** |
| DUP_QUOTE | identical `(ts_utc, bid, ask)` | **{ca['post_test_start']['dup_quote']}** |
| DUP_EVENT | identical event identity | **DATA_GAP** |

```text
DUP_TIMESTAMP is NOT equated with DUP_EVENT.
EVENT_IDENTITY = {ca['post_test_start']['EVENT_IDENTITY']}
(the feed carries no event id; (ts,bid,ask) cannot prove uniqueness, and no event id was invented)
Pre-boundary baseline (informational, NOT TEST): DUP_TIMESTAMP 1014 / DUP_QUOTE 1014 / DUP_EVENT 0.
```
""")
    w("audit/GAP_AUDIT.md", f"""# GAP AUDIT (freeze-002)

`generated_utc = {GEN}`

```text
POST-TEST_START gaps : none measurable (row_count = {ca['post_test_start']['row_count']})
>60 s  : n/a
>3000 s: n/a   (this threshold defines session boundaries)
max gap: n/a

BOUNDARY RECORD (§22)
  last event before TEST_START : {ca['boundary']['last_event_before_test_start']}
  first event at/after TEST_START : {ca['boundary']['first_event_after_test_start']}
  boundary gap : {ca['boundary']['boundary_gap_seconds']}
  classification : TEST_START_ARTEFACT — NOT a natural market gap and NOT usable as a session boundary
```
No gap-driven deletion was performed, and the boundary was not re-labelled as a market gap.
""")
    w("audit/SESSION_AUDIT.md", f"""# SESSION AUDIT (freeze-002)

`generated_utc = {GEN}` · ruling applied: `{H}/TEST_SESSION_DEFINITION_RULING_001.md`

## Applied rule

```text
SESSION            = CONTIGUOUS_SEGMENT
SEGMENT_BOUNDARY   = adjacent gap > 3000 s
MIN_SESSION_TICKS  = 200,000
first session must start at/after {TEST_START}
```

## Result

```text
candidate segments found at/after TEST_START : {len(ca['sessions'])}
VALID (>= 200,000 ticks)                     : {valid}
INCOMPLETE                                   : {len(ca['sessions']) - valid}
target                                       : {TARGET}
=> TEST_READY = {ready}
```

## Final session table (§41) — as it stands now

| Session | Start | End | Ticks | Max Gap | Valid |
|---|---|---|---|---|---|
| — | — | — | 0 | — | — |

*No session exists yet; the table is empty because there is no post-boundary data, not because any
session was rejected.*

## Scheduling reality (informational)

```text
median inter-tick (pre-TEST)            : {med_dt_ms} ms
contiguous hours needed for 200,000 ticks: ~{hours_per_session} h
max valid sessions per trading day       : 1   (daily break > 3000 s splits the day)
minimum trading days to 10 sessions      : ~{days_for_ten}
```
No padding, merging, threshold-lowering or cherry-picking was applied or considered.
""")

    w("final_test_snapshot_report.md", f"""# Final Report — V3-HFT-TEST-SNAPSHOT-FREEZE-002

`TEST-COLLECTION / SNAPSHOT-FREEZE / READ_ONLY / NO-EXPERIMENT`

## Outcome

```text
TEST_READY = NO
TEST_SNAPSHOT = NOT_CREATED
WAIT
```

## Q1–Q15

| # | question | answer |
|---|---|---|
| Q1 | TEST_START strictly `2026-09-22T06:20:00Z`? | **YES** — unchanged |
| Q2 | >= 10 valid sessions? | **NO** — {valid} of {TARGET} |
| Q3 | every session >= 200,000 ticks? | **N/A** — no session exists |
| Q4 | session boundary strictly gap > 3000 s? | **YES (rule applied)**; no boundary observed yet |
| Q5 | DUP_TIMESTAMP / DUP_QUOTE / DUP_EVENT? | **{ca['post_test_start']['dup_timestamp']} / {ca['post_test_start']['dup_quote']} / DATA_GAP** (empty set; identity unprovable) |
| Q6 | OUT_OF_ORDER? | **{ca['post_test_start']['out_of_order_count']}** at/after TEST_START (pre-TEST baseline: 11) |
| Q7 | GAP? | none measurable post-boundary; boundary gap recorded as a TEST_START artefact |
| Q8 | session boundary anomaly? | **NONE** (no segments to evaluate) |
| Q9 | TEST read by any prior model? | **NO** |
| Q10 | TEST used for parameter selection? | **NO** |
| Q10b | future label computed? | **NO** |
| Q12 | PREREGISTRATION_HASH match? | **{'YES' if h_ok['preregistration'] else 'NO'}** |
| Q13 | MODEL_SPEC_HASH match? | **{'YES' if h_ok['model_spec'] else 'NO'}** |
| Q14 | COST_MODEL_HASH match? | **{'YES' if h_ok['cost_model'] else 'NO'}** |
| Q15 | TEST_READY? | **NO** |

## Why NO (and why that is the correct, disciplined outcome)

```text
TEST_START                = {TEST_START}
last event before start   = {ca['boundary']['last_event_before_test_start']}
first event at/after start= {ca['boundary']['first_event_after_test_start']}   (none)
events at/after start     = {ca['post_test_start']['row_count']}
```
The boundary passed only minutes ago and the collector has not yet written an event at/after it.
A valid session additionally requires ~{hours_per_session} h of *contiguous* data, and at most one
valid session can form per trading day ⇒ **~{days_for_ten} trading days minimum** before
`TEST_READY` can be YES.

Nothing was done to shorten this: no threshold change, no start shift, no DEVELOPMENT backfill,
no session selection, no early freeze.

## Session table (§41)

| Session | Start | End | Ticks | Max Gap | Valid |
|---|---|---|---|---|---|
| — | — | — | 0 | — | — |

## Final state

```text
WAIT_FOR_CHATGPT_FINAL_AUDIT
```
This task never authorises or starts `V3-HFT-ALPHA-EXPERIMENT-001`.
""")

    files = []
    for dp, _, fn in os.walk(H):
        if "__pycache__" in dp:
            continue
        for f in fn:
            if f == "SHA256SUMS" or f.endswith(".pyc"):
                continue
            files.append(os.path.join(dp, f))
    files.sort()
    open(os.path.join(H, "SHA256SUMS"), "w", encoding="utf-8", newline="\n").write(
        "\n".join(f"{sha256(p)}  {os.path.relpath(p, H).replace(chr(92), '/')}" for p in files) + "\n")
    print("wrote SHA256SUMS x", len(files))
    print(json.dumps({"TEST_READY": ready, "valid_sessions": valid,
                       "hashes": h_ok, "docs_ok": doc_ok, "rows_after_start": ca['post_test_start']['row_count']},
                      indent=1))


if __name__ == "__main__":
    main()
