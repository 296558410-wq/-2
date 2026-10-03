# R25 Run 生命周期只读取证

```text
TASK_STATUS = RUNNING
R25_GATE = FAIL
STOP_REASON = RUN_LIFECYCLE_NOT_ESTABLISHED

RUN_ID_CREATOR = V1_SOURCE
RUN_META_WRITER = UNKNOWN
STATISTICS_WRITER = V1_SOURCE
STATISTICS_INITIALIZER = UNKNOWN
STATISTICS_RESETTER = UNKNOWN
RUN_SCOPE_MANAGER = UNKNOWN

RUN_CREATION_PATH = NOT_FOUND
STATISTICS_INITIALIZATION_PATH = UNKNOWN
STATISTICS_UPDATE_PATHS = []

PER_RUN_FILE_NAMESPACE = PRESENT:['decisions', 'positions', 'tmp'],[]
PER_RUN_STATISTICS_ISOLATION = UNKNOWN

OLD_COUNTERS_BEHAVIOR = UNKNOWN
OLD_PNL_BEHAVIOR = UNKNOWN

V1_RUN_LIFECYCLE_ROLE = PRESENT
OPENCLAW_RUN_LIFECYCLE_ROLE = UNKNOWN
AUTOMATION_RUN_LIFECYCLE_ROLE = NOT_FOUND
EXTERNAL_SCRIPT_ROLE = UNKNOWN

LEGACY_RUN_END_MECHANISM = NOT_FOUND
NEW_RUN_CREATION_MECHANISM = NOT_FOUND
```

## RUN LIFECYCLE MATRIX

| stage | V1 | OpenClaw/Automation | External | evidence |
|---|---|---|---|---|
| CREATE RUN | NOT_FOUND | NOT_FOUND | NOT_FOUND | no run-creation code found |
| generate run_id | NOT_FOUND | NOT_FOUND | UNKNOWN | V1 source has 0 run_id hits |
| write RUN_META | NOT_FOUND | NOT_FOUND | UNKNOWN | no writer found |
| initialise statistics | NOT_FOUND | NOT_FOUND | UNKNOWN | counters exist but no init path proven |
| update counters | PRESENT(counter code exists) | NOT_FOUND | UNKNOWN | 74 counter hits in V1 code |
| reset counters | NOT_FOUND | NOT_FOUND | NOT_FOUND | no reset code |
| end Run | NOT_FOUND | NOT_FOUND | NOT_FOUND | no end-of-run logic found |
| archive Run | NOT_FOUND | NOT_FOUND | NOT_FOUND | no archive logic found |
| create new Run | NOT_FOUND | NOT_FOUND | NOT_FOUND | no new-run logic found |

## EVIDENCE

```text
SCANNED_FILES = 6002
KEYWORD_HIT_FILES = ["research/hermes/trader_v1/run_state/RUN_META.json", "research/hermes/trader_v1/run_state/statistics.json", "research/hermes/trader_v2/dashboard/datasource.py", "research/hermes/trader_v2/dashboard/static/app.js"]
TRUE_WRITER_CANDIDATES = {"statistics.json": [{"file": "research/hermes/trader_v1/tmp/e2e_driver.py", "target": "statistics.json", "line": 31, "kind": "WRITE", "text": "(rs / \"statistics.json\").write_text(json.dumps({\"counters\": {}, \"waits\": {}}), encoding=\"utf-8\")"}], "plan_ledger.jsonl": [{"file": "research/hermes/trader_v1/tmp/e2e_driver.py", "target": "plan_ledger.jsonl", "line": 30, "kind": "WRITE", "text": "(rs / \"plan_ledger.jsonl\").write_text(\"\", encoding=\"utf-8\")"}]}
AUTOMATION_PAYLOAD_KIND = agentTurn
AUTOMATION_MENTIONS_RUN_LIFECYCLE = []
GIT pickaxe RUNID = 43f9b2f reset(v1): archive pre-reset history and start V1_RUN_20260924_RESET_01 (reset, not an optimization; no strategy/parameter change)
TIMELINE = {"RUN_META": {"mtime": "2026-09-23T23:39:46.691776+00:00", "size": 725}, "STATISTICS": {"mtime": "2026-09-25T15:49:00.047044+00:00", "size": 5472}, "LEDGER": {"mtime": "2026-09-25T14:51:24.870933+00:00", "size": 242825}, "ENGINE": {"mtime": "2026-09-25T15:48:16.903337+00:00", "size": 27143}}
```