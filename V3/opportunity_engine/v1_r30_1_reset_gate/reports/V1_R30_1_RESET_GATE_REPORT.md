# R30.1 - Reset Gate Positive Path Verification

STATUS: GATE LOGIC ONLY - NO REAL RESET

## Positive path

```text
POSITIVE_PATH = PASS
OLD_RUN_CLOSED = PASS
OLD_RUN_CLOSEOUT_VERIFIED = PASS
OLD_LEDGER_VERIFIED = PASS
OLD_STATISTICS_VERIFIED = PASS
OLD_PNL_VERIFIED = PASS
NO_OPEN_POSITION = PASS
NO_PENDING_ORDER = PASS
NEW_RUN_MANIFEST_CREATED = PASS
NEW_RUN_OPENING_SNAPSHOT_VERIFIED = PASS
RESET_ALLOWED = YES
```

## Negative matrix (each broken on a copy)

| Case | Target condition | Value | RESET_ALLOWED |
|---|---|---|---|
| CASE_A | OLD_RUN_CLOSED | False | NO |
| CASE_B | OLD_RUN_CLOSEOUT_VERIFIED | False | NO |
| CASE_C | OLD_LEDGER_VERIFIED | False | NO |
| CASE_D | OLD_STATISTICS_VERIFIED | False | NO |
| CASE_E | OLD_PNL_VERIFIED | False | NO |
| CASE_F | NO_OPEN_POSITION | False | NO |
| CASE_G | NO_PENDING_ORDER | False | NO |
| CASE_H | NEW_RUN_MANIFEST_CREATED | False | NO |
| CASE_I | NEW_RUN_OPENING_SNAPSHOT_VERIFIED | False | NO |

## Truth table

```text
{"all_true": "YES", "any_false_cases": {"CASE_A": "NO", "CASE_B": "NO", "CASE_C": "NO", "CASE_D": "NO", "CASE_E": "NO", "CASE_F": "NO", "CASE_G": "NO", "CASE_H": "NO", "CASE_I": "NO"}, "AND_GATE": "VERIFIED", "rule": "AND only; no majority vote, no weighted score, no LLM judgement"}
```

## Deterministic repeat

```text
[{"run": 1, "RESET_ALLOWED": "YES", "verification_hash": "f0b22838fe5904d5aeea7afff94eb3eba147a01a872b1c62154ae8023ff8ff3b", "decision_hash": "8ae8b968e37535d0f92be77140115ef40221b6b5a65042dc35f26552a9e5cdf1"}, {"run": 2, "RESET_ALLOWED": "YES", "verification_hash": "f0b22838fe5904d5aeea7afff94eb3eba147a01a872b1c62154ae8023ff8ff3b", "decision_hash": "8ae8b968e37535d0f92be77140115ef40221b6b5a65042dc35f26552a9e5cdf1"}, {"run": 3, "RESET_ALLOWED": "YES", "verification_hash": "f0b22838fe5904d5aeea7afff94eb3eba147a01a872b1c62154ae8023ff8ff3b", "decision_hash": "8ae8b968e37535d0f92be77140115ef40221b
input_hash stable = YES
```

## Tamper recovery

```text
{"TAMPER_CLEAN_YES": "PASS", "TAMPERED_NO": "PASS", "RESTORED_YES": "PASS"}
```

## Safety

```text
{"RESET": 0, "NEW_RUN": 0, "V1_START": 0, "AUTOMATION_ENABLE": 0, "MT5_ACCESS": 0, "ORDER_SEND": 0, "POSITION_CLOSE": 0, "POSITION_MODIFY": 0, "ORDER_CANCEL": 0, "V1_RUNTIME_WRITE": 0, "V1_STATE_WRITE": 0, "V1_LEDGER_WRITE": 0, "V1_CONFIG_WRITE": 0, "GIT_COMMIT": "NONE", "MT5_SOURCE_HITS": 0}
```

## Hashes

```text
before = {"ENGINE_SHA256": "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d", "LEGACY_LEDGER_SHA256": "0b90493cae0cdf7b73056bc72b1e5752f35c3eb20f9306c098d26f4bec819261", "STATISTICS_SHA256": "ca42f624fde50df375dc877750e121e8d2d313986ea6d953766d5247ab76ee84", "RUN_META_SHA256": "597bd76970412c107c96475dfe8d5093ff7840aba73cb4ab65318f2b0f358950"}
after  = {"ENGINE_SHA256": "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d", "LEGACY_LEDGER_SHA256": "0b90493cae0cdf7b73056bc72b1e5752f35c3eb20f9306c098d26f4bec819261", "STATISTICS_SHA256": "ca42f624fde50df375dc877750e121e8d2d313986ea6d953766d5247ab76ee84", "RUN_META_SHA256": "597bd76970412c107c96475dfe8d5093ff7840aba73cb4ab65318f2b0f358950"}
stable = {"ENGINE_SHA256": "YES", "LEGACY_LEDGER_SHA256": "YES", "STATISTICS_SHA256": "YES", "RUN_META_SHA256": "YES"}
V1_ISOLATION=PASS V2_ISOLATION=PASS V3_ISOLATION=PASS
```

## Counters

```text
RESET=0 NEW_RUN=0 V1_START=0 AUTOMATION_ENABLE=0 MT5_ACCESS=0
ORDER_SEND=0 POSITION_CLOSE=0 POSITION_MODIFY=0 ORDER_CANCEL=0
V1_RUNTIME_WRITE=0 V1_STATE_WRITE=0 V1_LEDGER_WRITE=0 V1_CONFIG_WRITE=0 GIT_COMMIT=NONE
```

## Final principle

```text
The Gate allows only when all nine conditions are TRUE, and refuses when any one is FALSE.
This proves the logic only; it grants no Reset / New Run / V1 Start / Automation authority.
```