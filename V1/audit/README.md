# V1 重启后连续亏损专项审计 — 产物与复现

只读审计。**未改生产代码/配置/限额/权限；ORDER_SEND=0；未发 order_check；未启动生产周期。**

## 产物
| 文件 | 内容 |
|---|---|
| `V1_RESTART_AUDIT_REPORT.md` | 审计报告（判定/逐笔/根因/修复验证/边界） |
| `V1_RESTART_TRADE_TRACE.json` | 重启前后全量逐笔（券商事实 + 账本交叉引用） |
| `V1_RESTART_STATE_AUDIT.json` | 重启余留状态审计（持仓/pending/数据新鲜度/时间帧/调度/回撤/反事实） |
| `V1_RISKGUARD_FIX_VALIDATION.json` | 暂存修复的独立验证（回归/复现/执行路径/副作用） |

## 脚本（自包含，可重跑）
在 `C:\AIQuant` 下用项目 venv 运行：

```
C:\AIQuant\.venv\Scripts\python.exe research\hermes\trader_v1\audit\v1up_restart_audit_build.py
C:\AIQuant\.venv\Scripts\python.exe research\hermes\trader_v1\audit\v1up_restart_details.py
C:\AIQuant\.venv\Scripts\python.exe research\hermes\trader_v1\audit\v1up_fix_validation.py
```

- `v1up_restart_audit_build.py`：只读 MT5 `history_deals_get`/`history_orders_get` + v1_upgrade 账本 → 生成逐笔与状态审计 JSON。
- `v1up_restart_details.py`：补调度缺口 / 数据新鲜度 / 服务器帧偏移 / 对账延时 / 回撤到状态审计 JSON。
- `v1up_fix_validation.py`：重跑暂存回归测试与故障复现，并核验执行路径与生产指纹未变。

## 关键事实
- 重启：`2026-10-01 21:52:15 GMT+8 = 13:52:15Z`；漏 1 拍（14:03Z）；14:18Z 恢复。
- 重启后 **7 笔全亏**，最长连亏 7；正确接线反事实 **2 笔应拒而放行**。
- 判定：`RUNTIME_GUARD_BUG_CONFIRMED` + `NO_RESTART_STATE_BUG` + `FIX_VALIDATED_NO_PRODUCTION_CHANGE`。
- 暂存修复（未应用）：`research/hermes/trader_v1/v1_upgrade/audit/staged_fix/`。

## Commit
- 产物提交：`df18f6bb769394d6fb4b3d971015b037396d655d`（path-limited，仅 `research/hermes/trader_v1/audit/`；生产代码未提交、未改动）。

## 全量重审（2026-10-02，只读）
- `v1_full_reaudit/`：V1 全量架构审计 + 护城河产物（12 文件 + `V1_ALPHA_STATS.json` + `SHA256SUMS.txt` + regression/replay 工具）。
  - `V1_FINAL_STATUS.md`：ENGINE STATUS = FAIL、ALPHA STATUS = UNKNOWN（含评级表与 11 问答）。
  - `v1up_regression_suite.py`：永久回归套件（14 项，CI_PASS/FAIL）。

## 生产修复（2026-10-02，用户正式授权）
- `V1_RISKGUARD_PATCH_REPORT.md`：修复报告（方案/前后 SHA256/验收/dry-run 副作用/残留）。
- `V1_PATCH_HASHES.json` / `V1_PATCH_DIFF.txt`：生产文件修复前后指纹与 unified diff。
- `V1_ISOLATED_VERIFICATION.json`：隔离验证（副本账本，无 MT5、无生产写入）。
- `V1_DRYRUN_ACCOUNTING.json`：生产 `--dry-run` 的修复前/本次新增事件严格区分。
- 脚本：`v1up_patch_backup.py` / `v1up_isolated_verification.py` / `v1up_dryrun_accounting.py` / `v1up_patch_diff.py`。
- 最终状态：**PATCH_APPLIED_VALIDATED**（12/12 回归、8/32 复现、dry-run 当场拒绝开仓、order_send/order_check=0、链 OK）。
- **PATCH_COMMIT**：`63d5a22109126770efd3ff235a7d32593f25e484`（含 `v1_upgrade/gates.py`+`cycle.py`+本目录）。

## 依赖
- 只读 MT5：`.env.mt5_demo`（`DEMO_MT5_LOGIN/SERVER/PASSWORD`）、终端路径 `V1UP_MT5_PATH`（默认 FXTM Demo）。
- 账本：`research/hermes/trader_v1/v1_upgrade/ledger/v1_upgrade_ledger.jsonl`。
