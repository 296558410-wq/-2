# V1 engine.py 基线溯源 R1

`2026-09-25T14:52:15.580688+00:00`

```text
TASK_STATUS = COMPLETE
CURRENT_ENGINE_SHA256 = e308e9ced4afab35c458068642d2a0f28e56f0582d4e94ea75654beaecfb51fe
MV_R1_BASELINE_SHA256 = 7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d

BASELINE_PROVENANCE        = PARTIAL  (HEAD_is_baseline=False, matches_in_history=0)
CURRENT_VERSION_PROVENANCE = UNKNOWN  (exact matches in history: 0)

GIT_WRITE_EVIDENCE          = REVIEW
MANUAL_EDIT_STATUS          = USER_CONFIRMED_NOT_EDITED
RUNTIME_SELF_WRITE_EVIDENCE = NOT_FOUND

CHANGE_ORIGIN = unknown
CHANGE_COMMIT = None
CHANGE_COMMIT_TIME = None

STRATEGY_LOGIC_CHANGED = YES
ENTRY_LOGIC_CHANGED    = NO
EXIT_LOGIC_CHANGED     = YES
RISK_LOGIC_CHANGED     = NO
PARAMETER_CHANGED      = UNKNOWN
ORDER_LOGIC_CHANGED    = NO

V1_ISOLATION = FAIL
COMMIT_GATE  = FAIL
COMMIT       = NONE

V2_ISOLATION = PASS
V3_RESEARCH_STATUS = UNCHANGED

DECISION_REASON = CASE_C_LOGIC_OR_PARAMETER_CHANGED
```

## diff 事实（逐行）

```text
HUNK: @@ -410,8 +410,8 @@ def main():

-- 旧代码 --
          mht = (plan.get("maximum_holding_time") or "")
          if mht.startswith("M15*") and mht[4:].isdigit():

-- 新代码 --
          mht = plan.get("maximum_holding_time") or ""
          if isinstance(mht, str) and mht.startswith("M15*") and mht[4:].isdigit():
```

## 语义事实

```json
{
 "old": {
  "touches_maximum_holding_time": true,
  "touches_plan": true,
  "touches_order": false,
  "touches_risk": false,
  "touches_entry": false,
  "touches_exit": true,
  "touches_parameter": false,
  "type_guard": true
 },
 "new": {
  "touches_maximum_holding_time": true,
  "touches_plan": true,
  "touches_order": false,
  "touches_risk": false,
  "touches_entry": false,
  "touches_exit": true,
  "touches_parameter": false,
  "type_guard": true
 },
 "area_flags": {
  "PLAN": "YES",
  "MAXIMUM_HOLDING_TIME": "YES",
  "ENTRY": "NO",
  "EXIT": "YES",
  "RISK": "NO",
  "PARAMETER": "NO",
  "ORDER": "NO"
 }
}
```

## Git 版本比对（内容级 sha256）

| commit | date | matches_current | matches_baseline |
|---|---|---|---|
| cf25d5d141 | 2026-09-08 12:27:24 +0800 | False | False |
| 3df3ce9255 | 2026-09-08 07:34:49 +0800 | False | False |
| 10ac735f24 | 2026-09-07 23:22:23 +0800 | False | False |
| df0ce85713 | 2026-09-07 21:14:42 +0800 | False | False |
| 4ec110cc29 | 2026-09-07 20:36:43 +0800 | False | False |
| 291e0dd24d | 2026-09-07 20:24:05 +0800 | False | False |
| f775a4eaff | 2026-09-07 19:55:03 +0800 | False | False |

```text
added lines found in history commits: []
removed lines found in history commits: ['cf25d5d141', '3df3ce9255', '10ac735f24']
reflog entries mentioning engine.py: ['2c28704 HEAD@{2026-09-25 19:23:24 +0800}: commit: feat(v3): market opportunity discovery engine R1 (state engine + 5 detectors + opportunity ledger + hermes review + replay); 11/11 tests PASS; no trading, no forward, no orders']
```

## blame（hunk 区域）

```text
10ac735f (296558410-wq      2026-09-07 23:22:23 +0800 410)         except Exception:  # noqa: BLE001
10ac735f (296558410-wq      2026-09-07 23:22:23 +0800 411)             age_min = 0
10ac735f (296558410-wq      2026-09-07 23:22:23 +0800 412)         max_hold = 120.0  # 默认 2h; 计划可指定
00000000 (Not Committed Yet 2026-09-25 22:52:15 +0800 413)         mht = plan.get("maximum_holding_time") or ""
00000000 (Not Committed Yet 2026-09-25 22:52:15 +0800 414)         if isinstance(mht, str) and mht.startswith("M15*") and mht[4:].isdigit():
10ac735f (296558410-wq      2026-09-07 23:22:23 +0800 415)             max_hold = float(mht[4:]) * 15
10ac735f (296558410-wq      2026-09-07 23:22:23 +0800 416)         ez = plan.get("entry_zone") or {}
10ac735f (296558410-wq      2026-09-07 23:22:23 +0800 417)         ez_hi = ez.get("high")
```

## 研究不可变性

```text
M01 event ca44fd2c02afd867 · R1 ledger d9cd67757e501c3e · M01 audit a3bee5375f318ceb · R2 canonical 20913b986890b1c5
V3_RESEARCH_STATUS = UNCHANGED
```