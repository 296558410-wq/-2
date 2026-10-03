# V1 engine.py 精确基线恢复 R1

`2026-09-25T14:54:54.652179+00:00`

```text
TASK_STATUS = STAGE_1_3_COMPLETE
PRE_RESTORE_SHA256 = e308e9ced4afab35c458068642d2a0f28e56f0582d4e94ea75654beaecfb51fe
BASELINE_SHA256 = 7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d
POST_RESTORE_SHA256 = None
BASELINE_ARTIFACT_FOUND = YES
BASELINE_HASH_MATCH = PASS
CONTROLLED_RESTART = NO
V1_PID_BEFORE = 14376
V1_PID_AFTER = NOT_RESTARTED
COMPILE = NOT_RUN
IMPORT = NOT_RUN
SELF_TEST = NOT_RUN
RUNTIME_HEALTH = NOT_RUN
V1_ISOLATION = FAIL（尚未替换/复验）
V2_ISOLATION = PASS
V3_RESEARCH_STATUS = UNCHANGED
STRATEGY_CHANGED = NO
PARAMETER_CHANGED = NO
ENTRY_CHANGED = NO
EXIT_CHANGED = NO
RISK_CHANGED = NO
ORDER_CHANGED = NO
COMMIT = NONE
```

## 说明

```text
STOP_REASON = baseline artifact found; controlled V1 stop/restore deferred to the next window (trading engine stop is safety-sensitive)
BASELINE_SOURCE = archive/v1_pre_reset_20260923_233741/v1_root/engine.py
searched_paths = 1162
git_reconstruction_used = NO（按 §四 禁止）
V1_touched = NO（未停止/未重启/未替换）
```

## 报告要点

```json
{
 "STOP_REASON": "baseline artifact found; controlled V1 stop/restore deferred to the next window (trading engine stop is safety-sensitive)",
 "LIVE_CONTENT_MATCHES": [
  "research/v3_opportunity_engine/m01_v1_engine_baseline_restore_r1/pre_restore_engine.py"
 ],
 "PLACEHOLDER_MATCHES": [
  "research/v3_opportunity_engine/m01_v1_engine_attribution_r1/_v1_engine_attribution.py",
  "research/v3_opportunity_engine/m01_v1_engine_baseline_provenance_r1/V1_ENGINE_BASELINE_PROVENANCE_R1.json",
  "research/v3_opportunity_engine/m01_v1_engine_baseline_provenance_r1/V1_ENGINE_BASELINE_PROVENANCE_R1.md",
  "research/v3_opportunity_engine/m01_v1_engine_baseline_provenance_r1/_v1_engine_provenance.py",
  "research/v3_opportunity_engine/m01_v1_engine_baseline_restore_r1/_v1_baseline_restore.py",
  "research/v3_opportunity_engine/m01_v1_engine_writer_forensics_r1/_v1_writer_forensics.py"
 ],
 "research_immutability": {
  "M01_event": "ca44fd2c02afd867b9c66cb5da463eb0283fef6c31ba4e7c20fc988a1c9e2621",
  "R1_ledger": "d9cd67757e501c3e550338da4228d67c0132ea293f28bce031b1cf010790f4ed",
  "M01_audit": "a3bee5375f318ceb8bdd3144a0ac2639b88e2c5932a3e33c563c72b2c0c9f17d",
  "R2_canonical": "20913b986890b1c593a63d1dfa7d6e1d90ad0b71db7b5134132f3ecfd7e72624"
 },
 "v1_process_state": {
  "processes_matching_trader_v1": "{\"ProcessId\":14376,\"Name\":\"powershell.exe\",\"CreationDate\":\"\\/Date(1790348095154)\\/\"}",
  "v1_related_tasks": [
   "������:                             \\OpenClaw\\hermes-tick-collect",
   "������:                             \\OpenClaw\\hermes-v2-cycle",
   "Ҫ���е�����:                       C:\\AIQuant\\.venv\\Scripts\\python.exe C:\\AIQuant\\research\\hermes\\trader_v2\\runtime\\v2_scheduled_cycle.py",
   "������:                             \\OpenClaw\\hermes-v2-observer",
   "Ҫ���е�����:                       C:\\AIQuant\\.venv\\Scripts\\python.exe C:\\AIQuant\\research\\hermes\\trader_v2\\tools\\v2_observer.py --quiet",
   "Ҫ���е�����:                       C:\\AIQuant\\research\\hermes\\trader_v3\\run_calibration_pilot.cmd "
  ],
  "PID": 14376,
  "OPEN_POSITIONS": "NOT_EVALUATED",
  "PENDING_ORDERS": "NOT_EVALUATED",
  "note": "read-only snapshot; no stop/restart attempted"
 },
 "git_status": "M research/hermes/trader_v1/engine.py",
 "git_diff_stat": "research/hermes/trader_v1/engine.py | 4 ++--\n 1 file changed, 2 insertions(+), 2 deletions(-)\nwarning: in the working copy of 'research/hermes/trader_v1/engine.py', LF will be replaced by CRLF the next time Git touches it"
}
```