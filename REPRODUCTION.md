# REPRODUCTION.md — 如何复现研究（只读、不执行交易）

> 目标：让人在**不触发任何交易/执行**的前提下，检查代码可编译、可 import、可重放。
> 本归档是源码快照；真实运行环境在 `C:\AIQuant`。

## 1. 环境

- Python：`3.12.10`（源环境 `C:\AIQuant\.venv\Scripts\python.exe`）。
- 依赖：见 `shared/environment/requirements.txt`、`shared/configs/requirements-lock.txt`。
- GPU 研究（V2 Grand Architecture）：torch + CUDA（源机为 RTX A2000 4GB）。
- MT5 研究访问：默认**只读**，模板见 `shared/configs/mt5_research_readonly.env.example`
  （`MT5_RESEARCH_READONLY_MODE=1`、`MT5_ORDER_API_DISABLED=1`）。

> ⚠️ 归档内**不含** broker 凭据。复现时请自备环境变量，且**不要**把密钥写入仓库。

## 2. 最低限度健全性检查（不执行交易）

```powershell
# 1) 语法编译检查（不 import、不运行）
python -m compileall -q V1 V2 V3 shared
# 2) import smoke（仅导入模块，不进入主循环、不发单）
$env:MT5_RESEARCH_READONLY_MODE="1"; $env:MT5_ORDER_API_DISABLED="1"
python -c "import importlib,sys; importlib.import_module('shared.research_engine.core.backtest')"
# 3) 按 SHA256 校验关键文件
python tools/verify_sha256.py   # 见 GITHUB_ARCHIVE_VERIFICATION.md §3 的哈希行
```

## 3. 研究复现入口（示例）

| 目的 | 入口 |
|---|---|
| 通用研究内核 | `shared/research_engine/`（`core/`, `statistics/`, `validation/`, `compute/`） |
| V2 Grand Architecture 组合扫描（GPU） | `V2/V2_GRAND_ARCHITECTURE/gpu_research/` + `pipeline/` |
| V2 Phase2 live evidence（冻结报告） | `V2/V2_GRAND_ARCHITECTURE/PHASE2_LIVE_EVIDENCE/FINAL_REPORT.md` |
| V2 run 重放/审计 | `V2/research/runs/<RUN_ID>/run_manifest.json` + `V2/src/ledger/` |
| V1 重放研究 | `V1/src/replay_study.py` |
| V3 机会引擎评审 | `V3/opportunity_engine/mechanism_validation_r*/`, `tradability_r1/` |

> 复现研究脚本时请**务必保持只读**：任何会产生 `order_send` 或改写源仓库 `run_state/` 的操作都**不要**在
> 归档副本上执行。

## 4. 版本与血缘

- 源提交：`665bf2950302b57a5d8fa8bb539083c2df653286`
  （`research/v2-grand-architecture-phase2`），详见 `archive/SOURCE_COMMITS.md`。
- 冻结基线 tag：`v2-pricespace-validated-cf31862`、`V2_FULL_AUDIT_BASELINE`、`V2_REPAIRED_RUN_START`。
- 每个子系统文件清单（路径 + SHA256）：`V1|V2|V3/manifests/FILE_INDEX.json`。

## 5. 不做什么

- 不自动重跑生产循环；不连接真实账户；不发送订单；不改写历史账本/状态。
- 归档副本与源仓库是**独立**的：在副本上做任何实验都不应回写 `C:\AIQuant`。
