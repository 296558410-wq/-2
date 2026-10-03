# V1 护城河登记（V1_MOAT_REGISTER）

> 不只产出报告：以下为**可长期复用**的资产，V1/V2/V3 均可引用。状态：BUILT / PARTIAL。

| # | 护城河 | 资产 | 文件 | 状态 |
|---|---|---|---|---|
| 1 | 数据护城河 | 数据源/PIT/coverage/hash registry | `V1_PIT_DATA_REGISTRY.json` | BUILT |
| 2 | 失败知识库 | 已证伪假设 + 根因 + 复现 | `V1_FAILURE_KNOWLEDGE_BASE.md` | BUILT |
| 3 | 缺陷数据库 | 13 条 defect（ID/TYPE/SEVERITY/复现/影响/ROOT/FIX/COMMIT） | `V1_DEFECT_REGISTER.json` | BUILT |
| 4 | Replay 护城河 | 确定重放（同输入同输出）+ 账本 replay + 独立重算 | `V1_LEDGER_REPLAY_AUDIT.json`、`v1up_regression_suite.py` | BUILT |
| 5 | Execution Fingerprint | spread/slippage/RTT/reject/retcode/filling/duration | `V1_EXECUTION_AUDIT.json` | BUILT |
| 6 | RiskGuard Regression Suite | 永久自动回归（14 项） | `v1up_regression_suite.py` | BUILT |
| 7 | Architecture Contract | 职责/状态/数据/恢复/隔离/安全不变量 | `V1_ARCHITECTURE_CONTRACT.md` | BUILT |

## 复用说明

- **数据护城河**：新增数据源必须登记 source/time_range/PIT/coverage/hash；无法证明 PIT 则 `UNKNOWN/DATA_BLOCKED`，不得默认 PASS。
- **回归套件**：`C:\AIQuant\.venv\Scripts\python.exe research\hermes\trader_v1\audit\v1_full_reaudit\v1up_regression_suite.py`，任何非 100% → **CI/AUDIT FAIL**（exit 1）。建议接入每日/每次改动后运行。
- **缺陷库**：新缺陷按既有 schema 追加；修复后填 FIX/VALIDATION/COMMIT，状态置 FIXED。
- **执行指纹**：后续 V1/V2/V3 共用同一执行成本基线（本仓库当前值是 XAUUSD FXTM demo 的实测样本）。
- **契约**：任何新增代码若突破 `V1_ARCHITECTURE_CONTRACT.md` 即 DESIGN_DEFECT。

## 与 V2/V3 的关系

- 本次产物只落在 `research/hermes/trader_v1/audit/v1_full_reaudit/`，**不污染 V2/V3**。
- 隔离已双向核对：V1 代码对 V2/V3 引用 = 0。
- 执行指纹与失败库**建议**被 V2/V3 引用（需各自单独授权）。
