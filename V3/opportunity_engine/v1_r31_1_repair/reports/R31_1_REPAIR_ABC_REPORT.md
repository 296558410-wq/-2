# R31.1 Phase A+B+C

```text
PHASE_A_SCANNER_REPAIR = PASS
CONTROL_POSITIVE = PASS
CONTROL_NEGATIVE = PASS
FORBIDDEN_HITS_IN_R30_R301 = 0

PHASE_B_V1_V2_ISOLATION = FAIL
hits_v1_to_v2 = 0
hits_v2_to_v1 = 27
D_E_hits = 9
imports_v1_to_v2 = 0
imports_v2_to_v1 = 0

PHASE_C_R31_GATE = FAIL
fails = ['v1_v2_isolation', 'audit_deterministic', 'audit_replay']

V2_TREE_HASH_BEFORE = 39cb42993f4753d752768ead0fd30bf858a1a6005eedbb2c11cc5e8e8d4f03dc
V2_TREE_HASH_AFTER = 39cb42993f4753d752768ead0fd30bf858a1a6005eedbb2c11cc5e8e8d4f03dc
V2_UNCHANGED = PASS
V2_FILES = 55765

ENGINE_HASH_STABLE = YES
LEDGER_HASH_STABLE = YES
STATISTICS_HASH_STABLE = YES
RUN_META_HASH_STABLE = YES

MT5_ACCESS = 0  ORDER_SEND = 0  POSITION_CLOSE = 0  POSITION_MODIFY = 0  ORDER_CANCEL = 0
NEW_RUN_CREATED = 0  RESET = 0  LEGACY_RUN_CLOSED = 0
V1_START = 0  AUTOMATION_ENABLE = 0
V1_FILES_MODIFIED = 0  V1_STATE_FILES_MODIFIED = 0  V1_LEDGER_MODIFIED = 0  V1_CONFIG_MODIFIED = 0
V2_FILES_MODIFIED = 0  GIT_COMMIT = NONE

R31_1_STATUS = STOPPED_AT_GATE
```

## Isolation questions

```text
{
 "q1_v1_imports_v2": "NO",
 "q2_v2_imports_v1": "NO",
 "q3_v1_runtime_executes_v2": "NO",
 "q4_v2_runtime_executes_v1": "YES",
 "q5_v1_reads_v2_state": "NO",
 "q6_v2_reads_v1_state": "YES",
 "q7_v1_writes_v2": "NO",
 "q8_v2_writes_v1": "NO",
 "q9_v1_automation_points_to_v2": "NO",
 "q10_v2_automation_points_to_v1": "UNKNOWN (no V2 automation inspected read-only)"
}
```

## Per-hit forensics (see R31_1_ISOLATION_FORENSIC.json)

```text
A/B/C allowed with evidence; D/E => FAIL. Full per-hit rows with file/line/context/classification
are in reports/R31_1_ISOLATION_FORENSIC.json.
```