# V1 Incident 知识库（V1_INCIDENT_KNOWLEDGE_BASE）

> 规则：Incident 一律确定性 ID（同一事实恒同 ID）、只增不覆盖（状态更新以追加记录表达，**最新记录生效**）；`root_cause` 允许 `UNKNOWN`，**禁止伪造**。合成夹具必须显式标注 `synthetic: true`。

## 1. 监测类型（自动生成）

| type | 触发条件 | severity | 关联 |
|---|---|---|---|
| `LEDGER_MISMATCH` | 链校验失败 / 序号缺口 / 行不可解析 | CRITICAL | seq, event_id |
| `SCHEDULE_GAP` | 相邻 DECISION 间隔 >25min（重启/停机/漏拍） | MEDIUM | 前后事件 |
| `RISK_BLOCK` | `WAIT_RISK:*`（按周期作用域） | LOW | decision_id |
| `KILL_SWITCH` | risk_reasons 含 KILL_SWITCH | HIGH | decision_id |
| `DUPLICATE_BLOCKED` | risk_reasons 含 DUPLICATE_ORDER | MEDIUM | dedup_key |
| `STALE_DATA` | risk_reasons 含 STALE_DATA | MEDIUM | decision_id |
| `MISSING_DATA` | `*_UNKNOWN`（输入不可确定，fail-closed） | MEDIUM | decision_id |
| `MT5_REJECT` | ORDER_SEND ok=false | MEDIUM | retcode |
| `ORDER_FILL_MISMATCH` | ok=True 但无对应 FILL | HIGH | order_id |
| `POSITION_MISMATCH` | 未平仓集合 ≠ 券商实时 | HIGH | ticket 集合 |
| `RECONCILIATION_MISMATCH` | 已平集合 ≠ 券商成交事实 | HIGH | position_id 差集 |
| `PNL_MISMATCH` | 账本 PnL ≠ 券商 profit 分量 | HIGH | 两个数值 |
| `UNKNOWN_EXCEPTION` | HALT / WAIT_TRUTH / 未知异常 | HIGH | 原因 |

## 2. 已入库事实（真实，非合成）

- `V1I-SCHEDULE_G-FB1B39B4` **SCHEDULE_GAP** MEDIUM：重启缺口 30.0min（2026-10-01T13:48Z→14:18Z）。
- `V1I-UNKNOWN_EX-ACF0BD58` **UNKNOWN_EXCEPTION** HIGH：历史 HALT（`name 'chk_rc' is not defined`）。
- `V1I-UNKNOWN_EX-44DFE2C1 / F1B6DA30`：历史 `MT5_INIT_FAILED` HALTs。
- `V1I-MT5_REJECT-*` ×10：历史拒单（retcode None ×5 IPC / 10018 ×5 休市，早于授权/休市，无越权）。
- `V1I-RISK_BLOCK-93E45412 / 03C4B119 / 70DC8557`：近三个周期的风控阻断（CLOSED，BY_DESIGN）。

## 3. 合成夹具（**明确标注**，用于演示“制造异常→自动 Incident→CLI 还原”）

| incident_id | type | 说明 |
|---|---|---|
| `V1I-RECONCILIA-7FAD46F6` | RECONCILIATION_MISMATCH | fault injection：券商有账本没有的已平仓（SYNTH-001）——**synthetic**，ACKNOWLEDGED |
| `V1I-PNL_MISMAT-E884A812` | PNL_MISMATCH | 同一注入的派生不匹配——**synthetic**，ACKNOWLEDGED |

> 这三类演示覆盖任务要求：①风控阻断（真实 RISK_BLOCK）②broker/ledger 不一致（合成注入）③restart/schedule gap（真实 30min 缺口）。均可由 CLI 一键还原。

## 4. 复现与验证

- 生成：`v1up_truth_regression.py`（16 场景，`TRUTH_SYSTEM_REGRESSION_PASS`）。
- 还原：`v1_forensic.py --incident <incident_id>`。
- 状态语义：`OPEN → ACKNOWLEDGED → CLOSED`（以追加记录更新；`forensic_incident` 返回最新态）。
