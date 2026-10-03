# Runtime Reference Map — V1 (旧 V1 engine + 新 V1 v1_upgrade)

> 目标：逐条说明 V1 runtime path 的入口、被引用的数据/配置/状态工件，以及**本次唯一删除操作**所涉文件的引用关系。
> 只读；引用证据均为 `文件:行` 直读。

## 1. 旧 V1 runtime（`research/hermes/trader_v1/*.py`，19 个 tracked .py）
入口链（每 M15 一轮）：`engine.py` → `trader_core.py` → `position.py` / `trigger.py` / `position_decision.py` / `invariants.py` / `review.py`；行情/执行：`broker_mt5_demo.py`；数据：`candlestick.py`、`state_package.py`；报表：`metrics.py`、`opportunity.py`；研究：`replay_study.py`、`stop_authority.py`。

| 运行时消费者 | 引用的工件 | 证据 | 是否交易路径 |
|---|---|---|---|
| `engine.py` | `run_state/decisions/`（每轮写决策 JSON） | `engine.py:31 DEC_DIR = RUN / "decisions"` | 写（非决策依赖） |
| `engine.py` | `run_state/state_package_latest.json` | `engine.py:37 STATE_PKG_P = RUN / "state_package_latest.json"` | 数据入状态包 |
| `metrics.py` | `run_state/decisions/*.json` | `metrics.py:130-133 decisions_recent()` | **只读报表** |
| `metrics.py` | `run_state/positions/` | `metrics.py:14 POS_DIR = RUN / "positions"` | 只读报表 |
| `metrics.py` | `run_state/state_package_latest.json` | `metrics.py:146` | 只读报表 |
| `opportunity.py` | `run_state/decisions/` | `opportunity.py:17 DEC_DIR = RUN / "decisions"` | 只读研究 |
| `position.py` | `run_state/positions/` | `position.py:23 STATE_DIR = HERE / "run_state" / "positions"`；`position.py:360 open_positions()` | **状态机读取** |
| `state_package.py` | `run_state/state_package_latest.json` | `state_package.py:25 OUT_DEFAULT` | 写入 |

## 2. 新 V1 runtime（`v1_upgrade/*.py`）
入口 `cycle.py`（零-LLM 直跑，Windows 任务 `hermes-v2-cycle` 同款；`--exec demo`）。风险：`gates.py`（`RiskGuard`/`Ledger.rebuild_risk_state`）；真值：`truth/truth_lib.py`。决策层 = `BASELINE_CONTROL` 控制臂（`cycle.py:402 signal_type="BASELINE_CONTROL"`）。
其状态/账本在 `v1_upgrade/ledger/`、`v1_upgrade/truth/evidence/`、`v1_upgrade/registry/`，均**未在本次删除操作范围内**。

## 3. 被删工件 → runtime 引用（DELETED_CODE_IMPACT.jsonl）
唯一删除操作 = commit **`43f9b2f`**（2026-09-24，`reset(v1): archive pre-reset history and start V1_RUN_20260924_RESET_01`），删除 **72 个文件，全部为 `run_state/` 下状态/历史工件**：

| 被删工件 | 数量 | runtime 引用 | 消费者类型 | 是否代码 |
|---|---|---|---|---|
| `run_state/decisions/20260907T*.json` … `20260908T0417Z.json` | 69 | **是** | 只读报表（metrics/opportunity）+ engine 每轮写 | 否 |
| `run_state/positions/POS-20260907T2355Z.json` 等 | 2 | **是** | 仓位状态机 `open_positions()` | 否 |
| `run_state/trader_summary.txt` | 1 | 否（0 命中） | — | 否 |

- **代码（.py）删除数 = 0。** 删除全部为 **state 类**。
- 同一 commit 还 **Modify** 了 `state_package_latest.json`（**非删除**，其 runtime 引用 `engine.py:37`/`metrics.py:146` 未断）与 `plan_ledger.jsonl`/`statistics.json`。
- `run_state/decisions/`、`run_state/positions/` 目录在删除后**继续存在并被 runtime 持续写入/读取**（见 §1）；删除只移除了 **09-07→09-24 的历史**。

## 4. 参考完整性（无引用断裂）
- 删除后无任何运行时 `import` 断裂；无 `os.remove/shutil.rmtree/unlink/rmdir` 出现在 V1 runtime 或 R8 脚本（扫描命中 = 0）。
- `state_package_latest.json`：runtime 引用存在（engine/metrics/state_package），**未被删**。
- 配置/注册表（`contracts/`、`registry/`）：无删除；`v1_upgrade/registry/` 无删除。
- 依赖清单（`configs/requirements-lock.txt`、`environment/requirements.txt` 等）无删除 commit。

## 5. 明确边界
- 本图仅覆盖 `research/hermes/trader_v1/**`（V1）。V3 的 `ff3f24a`（`git_diff_stat.txt` R100）与 V1 无关；money-hunter 的 `_hb_tick_cron.ps1`（09-13）非 V1 runtime。
- 旧 V1 与 V3 均不在“僵尸清理”影响范围内；V2 未触碰。
