# VERSION_INTEGRITY — 任务 D：版本完整性

## 1. 最终状态
| 项 | 值 |
|---|---|
| Git HEAD | **`226fb524048c9f041e7dcf29e2630259708a7fcc`** |
| 提交信息 | `feat(v2-phase3): discovery rank/select shadow + outcome engine + execution-mode unify to PAPER_LOCAL + version integrity (order_send=0)` |
| `research/hermes/trader_v2` 提交前 dirty | **204** 项 |
| 提交后 dirty | **0（clean）** |
| 纳入 Git 的未跟踪件 | `execution/execution_guard.py` 等（含 `runtime/atomic_io.py`、`state/FORWARD_VALIDATION_ALLOWED`、`state/SHADOW_ALLOWED`、research 审计文档、`observations/`、`tests/*` 新测试 等） |
| 代码 SHA256 清单 | **`V2_CODE_MANIFEST.json`**（**6140** 个代码/文档文件；排除 `state/`、`data_cache/`、`observations/` 运行期输出） |

## 2. 可追溯性
- 当前生产运行代码（`agents/`、`hermes/`、`execution/`、`data_sources/`、`runtime/`、`ledger/`、`config/`、`dashboard/`、`tools/`、`tests/`）**全部由 commit `226fb52` 唯一确定**。
- 每个文件的 SHA256 见 `V2_CODE_MANIFEST.json`（`manifest` 映射）。
- 未跟踪件 `execution/execution_guard.py` 已纳入。

## 3. 说明（诚实）
- `state/*.jsonl`（`opportunity_ledger`、`hermes_memory`、`evidence_registry` 等）为**运行期追加输出**，正常每 15 分钟变动；本提交包含提交时刻快照 ⇒ **"clean" 是提交时刻状态**，其后 V2 继续运行会再次出现 dirty（预期，非缺陷）。
- 未删除/重写任何历史 ledger；`state/decision_contexts/` 为冻结上下文（只增不改）。
