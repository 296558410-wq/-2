# R28 - Reset asset and PnL boundary audit

```text
V1_R28_RESET_ASSET_AUDIT = V1_R28_RESET_ASSET_AUDIT_COMPLETE

OLD_LEDGER_SNAPSHOT = NOT_FOUND
OLD_LEDGER_RECORDS_FOUND = 0
OLD_LEDGER_RECORDS_MISSING = 30

OLD_STATISTICS_SNAPSHOT = PARTIAL

OLD_PNL_ISOLATION = PROVEN

NEW_RUN_COUNTER_BOUNDARY = PARTIAL
NEW_RUN_PNL_BOUNDARY = NOT_PROVEN
NEW_RUN_BALANCE_BOUNDARY = NOT_PROVEN

RUN_ACCOUNTING_BOUNDARY = NOT_PROVEN

EXECUTION_ACTOR = UNKNOWN

RESET = 0
NEW_RUN = 0
V1_START = 0
AUTOMATION_ENABLE = 0
MT5_ACCESS = 0

ORDER_SEND = 0
POSITION_CLOSE = 0
POSITION_MODIFY = 0
ORDER_CANCEL = 0

LEDGER_WRITE = 0
STATE_WRITE = 0
SOURCE_WRITE = 0
CONFIG_WRITE = 0
GIT_COMMIT = NONE

V1_ISOLATION = PASS
V2_ISOLATION = PASS
V3_ISOLATION = PASS
BOUNDARY_VIOLATION = 0

ENGINE_HASH_STABLE = YES
LEDGER_HASH_STABLE = YES
STATISTICS_HASH_STABLE = YES
RUN_META_HASH_STABLE = YES

R28_GATE = FAIL
```

## anchors

```text
parent ledger lines = 30
parent ledger file sha256 = 041b08eac62e6996b2e865a7ea54f6781cd836d65bdee042312939920aa182b2
commit ledger file sha256 = 84eb2ee94cef38fe3fd79d8ddb4cb99bc7ed3ab223be1c2e95c8e9c60bf6df5b
parent statistics file sha256 = b7753b2e9e59ba926ed29be7289b1e3782d6f37ce4c15cec8cd444e5488375ec
```

## search scope

```text
scanned_text_files = 9001
ledger snapshot candidates = 2
statistics snapshot candidates = 2
archive-extension files seen = 0
keyword files = 2
```

## ledger snapshot candidates (top)

| path | size | lines | matched_records | mtime |
|---|---:|---:|---:|---|
| `research/hermes/state/opportunity_ledger.jsonl` | 15297 | 39 | 0 | 2026-09-11T13:25:03.944867+00:00 |
| `research/hermes/trader_v1/run_state/plan_ledger.jsonl` | 242825 | 173 | 0 | 2026-09-25T14:51:24.870933+00:00 |

## statistics snapshot candidates (top)

| path | size | exact_parent_match | mtime |
|---|---:|---|---|
| `research/hermes/trader_v1/run_state/RUN_META.json` | 725 | False | 2026-09-23T23:39:46.691776+00:00 |
| `research/hermes/trader_v1/run_state/statistics.json` | 5472 | False | 2026-09-25T15:49:00.047044+00:00 |

## PnL token hits

```text
[{"path": "research/hermes/trader_v1/run_state/plan_ledger.jsonl", "token": "2377449557", "binding": "EXPLICIT"}, {"path": "research/hermes/trader_v1/run_state/trader_summary.txt", "token": "2377449557", "binding": "EXPLICIT"}, {"path": "research/hermes/trader_v1/run_state/positions/POS-20260925T140419.json", "token": "2377449557", "binding": "EXPLICIT"}, {"path": "research/hermes/trader_v2/data_cache/router_cache.json", "token": "4299.03", "binding": "IMPLICIT_ONLY"}]
```

## six requirements

```text
{"OLD_LEDGER_SNAPSHOT": "NOT_FOUND", "OLD_STATISTICS_SNAPSHOT": "PARTIAL", "OLD_PNL_ISOLATION": "PROVEN", "NEW_RUN_COUNTER_BOUNDARY": "PARTIAL", "NEW_RUN_PNL_BOUNDARY": "NOT_PROVEN", "NEW_RUN_BALANCE_BOUNDARY": "NOT_PROVEN"}
```

## Q1-Q8

```text
Q1_old_ledger_external_copy = NO
Q2_old_statistics_snapshot = PARTIAL
Q3_old_pnl_run_binding = PROVEN
Q4_new_run_opening_boundary = PARTIAL
Q5_new_run_may_inherit_counters = UNKNOWN
Q6_new_run_may_inherit_pnl = UNKNOWN
Q7_old_ledger_recoverable = NO
Q8_safe_to_reset = NO
```

## timeline

```text
{"T1_git_parent": "2026-09-22T14:23:16+08:00 [source=git metadata]", "T2_git_commit": "2026-09-24T08:21:58+08:00 [source=git metadata]", "T3_run_meta_start_time_utc": "2026-09-23T23:39:46.457357+00:00 [source=JSON field]", "T4_archive_timestamp": "2026-09-23T23:37:41 (from directory name) [source=filesystem name]", "T5_current_state": "V1 stopped; automation disabled [source=R28 freeze]"}
```

## archive vs git separation

```text
{"GIT_HISTORY": "43f9b2f has 0 files under archive/ (R26); parent also 0", "WORKTREE_ARCHIVE": "archive/v1_pre_reset_20260923_233741 exists in the worktree", "EXTERNAL_SNAPSHOT": "FOUND", "UNKNOWN": "actor/origin of the archive remains unknown"}
```

## core principle

```text
finding one archive is not proof of reset safety; the old ledger, old statistics and old PnL must
each have a complete, explicit, replayable accounting boundary to the new run.
```