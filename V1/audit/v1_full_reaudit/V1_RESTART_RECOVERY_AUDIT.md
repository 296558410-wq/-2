# V1 Restart / Recovery 审计（V1_RESTART_RECOVERY_AUDIT）

- 证据：`V1_RESTART_STATE_AUDIT.json`（重启余留状态）、`V1_RESTART_TRADE_TRACE.json`（逐笔）、`V1_DRYRUN_ACCOUNTING.json`、`V1_RISK_RUNTIME_MATRIX.json`（C_restart 路径）。
- 关键实测：主机重启 **2026-10-01 21:52:15 GMT+8 = 13:52:15Z**；python 21:54 起；唯一调度器为 OpenClaw cron（存活）。

## 1. 十种场景 × 结论

| # | 场景 | 应恢复 | 实测结论 |
|---|---|---|---|
| 1 | 正常运行 | — | ✅ 每 15min 一周期，账本链连续 |
| 2 | Python 重启 | 风控计数 | ✅ 修复后由 `rebuild_risk_state` 从账本重建（幂等）；修复前恒为 0（D001） |
| 3 | OpenClaw 重启 | 调度 | ✅ cron 存活；⚠️ 漏 1 拍（14:03Z），无补偿（D008） |
| 4 | Hermes 重启 | （本版无 Hermes） | n/a（信号无状态） |
| 5 | MT5 重启 | 行情/持仓视图 | ✅ 每周期重新 `initialize` + 实时 `positions_get()`；不缓存 |
| 6 | 网络短暂中断 | 对账 | ✅ 下一周期凭 `history_deals_get` 幂等补记（D005 延时） |
| 7 | 数据源中断 | 陈旧判定 | ✅ 修复后 `data_age` 同源；None/超限 → STALE_DATA 拒单 |
| 8 | 中途有持仓 | 持仓视图 | ✅ 取自 MT5 实时；重启瞬间实测**空仓**（无残留） |
| 9 | 中途有 pending state | 待对账 close | ✅ 凭 `position_id` 幂等；重启无 straddle 的 CLOSE |
| 10 | 系统停机期间发生 close | 补记 | ✅ 由下一周期 reconcile 补记（曾达 ~31h 延时，D005） |

## 2. 重启瞬间的真实状态（2026-10-01T13:52Z）

- **持仓/挂单**：空仓、无挂单（broker positions 空）。
- **应有风控状态**（按券商事实重算）：`daily_loss=+38.99`, `consecutive_losses=0` ⇒ **即使正确接线，重启那一刻也不会拦截**。
- **旧逻辑状态**：`0/0`（每轮新建）；与“应有”在**重启点无差异**（当天早段为盈利日）。
- ⇒ **非重启特有缺陷**：`NO_RESTART_STATE_BUG`。重启后连亏是“策略进入亏损段 × 守卫哑火”，不是状态未恢复/被污染。

## 3. 重启后逐笔（7 笔全亏，最长连亏 7）

| # | position_id | 开(UTC) | 平(UTC) | 净额 | 旧逻辑 | 正确接线 |
|---|---|---|---|---|---|---|
| 1 | 2378322488 | 14:33 | 14:39 | −9.51 | 放行 | 放行 |
| 2 | 2378333628 | 15:03 | 15:20 | −8.78 | 放行 | 放行 |
| 3 | 2378343004 | 15:33 | 15:38 | −11.01 | 放行 | 放行 |
| 4 | 2378348994 | 15:48 | 17:30 | −11.81 | 放行 | **应拒**（MAX_CONSECUTIVE_LOSS） |
| 5 | 2378382127 | 18:48 | 10-02 00:21 | −11.77 | 放行 | **应拒** |
| 6 | 2378409328 | 10-02 01:18 | 01:38 | −7.66 | 放行 | 放行（跨 UTC 日重置） |
| 7 | 2378413449 | 10-02 01:48 | 02:05 | −7.21 | 放行 | 放行 |

- 重启后净额 **−67.75**；正确接线反事实 **2 笔应拒而放行**。
- 之后引擎转 `FAMILY_*_NO_TRADE`，未再开仓（故不足 10 笔）。

## 4. 恢复正确性验证（自动化）

`v1up_regression_suite.py`：`restart_rebuild_blocks`（重建后 cons=3 拒单）、`rebuild_idempotent`（同账本同状态）均 PASS。

## 5. 判定

- `NO_RESTART_STATE_BUG`（无重启特有状态缺陷）。
- `RESTART_RECOVERY` 评级 = **PASS**（修复后）；修复前 = FAIL（风控状态不可恢复）。
