# RUNTIME_EXCLUSION_POLICY.md — 运行时/易变资产排除策略

本策略在**代码树**中排除运行时/易变资产，逐条记录于
`ARCHIVE_MANIFEST.json#excluded_runtime_assets` 与 `EXCLUDED_RUNTIME_ASSETS.jsonl`。

## 1. 整目录排除（DIRECTORY_AGGREGATE）

`.git .venv venv __pycache__ .pytest_cache .mypy_cache .ruff_cache
.cache cache data_cache tmp .tmp _tmp logs run_state observations state
mt5_instances github_publish_staging .ipynb_checkpoints .idea .vscode dist build node_modules data`

理由：`RUNTIME_CACHE_OR_VOLATILE_DIR`（缓存/易变状态/大体积数据/构建产物）。

## 2. 按扩展名排除

| 扩展 | 理由 |
|---|---|
| `.jsonl` | 增长型追加流（ledger/timeline/live stream/evidence_registry/router_audit…） |
| `.log` | 临时日志 |
| `.parquet` `.sqlite` `.db` `.npy` `.npz` `.h5` | 批量数据体 |
| `.exe` `.dll` `.ex5` `.so` `.pyd` | 二进制/可执行 |
| `.png` `.jpg` `.webp` `.gif` `.ico` | 图片（架构图等以源为准） |
| `.zip` `.gz` `.tar` `.7z` | 归档包 |

## 3. 按文件名排除

`*_latest.json` `latest.json` `latest.md` `*_health.json` `heartbeat.*` `*scheduler_state*.json`
`*.bak*`（含 `.bak_<ts>`）。

## 4. 体量阈值

- 单文件 > **10MB** → `LARGE_ARTIFACT`（如 22MB 的 V2_TREE_HASH.json、20MB opportunity_pool 等）。
- `.csv` > **1MB** → `LARGE_CSV`。

## 5. 每周期证据目录“抽样保留”

对以下**每周期证据目录**中的 `.json` 保留 **每目录最多 12 个样本**，其余记录为
`BULK_EVIDENCE_SAMPLED`（完整集合仍在源仓库）：

`decisions/  decision_contexts/  inputs/  exec_guard/  snapshots/  pit/  ctx/  replay/`

> 采用 §C6 原则“schema/样本/README 代替膨胀的流”，保证仓库体量可控且可追溯。

## 6. 密钥类（安全优先）

`.env*`、`*.key`、`*.pem`、`*.p12` → **EXCLUDED（绝不入库）**，见 `SECURITY_POLICY.md`。

## 7. 替代物

对被排除的实时流，归档用 **冻结报告 + 代码 + schema/README** 代替：
例如 `V2/V2_GRAND_ARCHITECTURE/PHASE2_LIVE_EVIDENCE/` 保留了 runner 代码与 `FINAL_REPORT.md`、
`DATA_MANIFEST.json` 等冻结件，而 `LIVE_EVIDENCE_STREAM.jsonl`/`OUTCOMES.jsonl` 等增长流被排除并记录。
