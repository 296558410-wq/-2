# GITHUB_ARCHIVE_VERIFICATION.md — 归档验证（本地可验证部分）

- 归档时点：2026-10-03（Asia/Shanghai）
- 归档仓库：`C:\AIQuant-XAUUSD-Systems`（**本地**，未创建 remote、未 push）
- 最终状态：**`GITHUB_ARCHIVE_PARTIAL`**（本地完成；push 待人工创建远端仓库）
- **GitHub clone verification = `PENDING_REPO_CREATION`**

---

## 1. 仓库树检查（三系统齐全）

| 系统 | 归档文件数 | 目录 |
|---|---|---|
| V1 | 2655 | `V1/` |
| V2 | 1126 | `V2/` |
| V3 | 1108 | `V3/` |
| shared | 339 | `shared/` |
| archive | 8 | `archive/` |
| docs | 2 | `docs/` |
| 顶层文件 | 8 | README/ARCHITECTURE/… 注册表 |
| **合计（git 跟踪）** | **5246** | — |

V1 / V2 / V3 均在树中，`V2/V2_GRAND_ARCHITECTURE/`（含 `PHASE2_LIVE_EVIDENCE/`）完整存在。 ✅

## 2. 关键文件 SHA256 对比（源 ↔ 归档）

归档文件与源文件**逐字节一致**（`core.autocrlf=false`，无换行改写）：

| source | archive | match |
|---|---|---|
| research/hermes/trader_v1/engine.py | V1/src/engine.py | ✅ |
| research/hermes/trader_v1/ledger.py | V1/src/ledger.py | ✅ |
| research/hermes/trader_v1/trader_core.py | V1/src/trader_core.py | ✅ |
| research/hermes/trader_v2/V2_ARCHITECTURE.md | V2/docs/V2_ARCHITECTURE.md | ✅ |
| research/hermes/trader_v2/V2_GRAND_ARCHITECTURE/FINAL_REPORT.md | V2/V2_GRAND_ARCHITECTURE/FINAL_REPORT.md | ✅ |
| research/hermes/trader_v3/V3_ALPHA_MAP.md | V3/docs/V3_ALPHA_MAP.md | ✅ |
| research/microstructure_memory/daily/20261002.json | V1/microstructure_memory/daily/20261002.json | ✅ |

示例哈希：
```
engine.py           7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d
ledger.py           8a62ac954ccf4d4c42a4d0cb9db789847bd40487170c8500cb065e8317a08876
trader_core.py      49cf0deddceea531158f48a8b9d20923c5dfc89d4b15d3569afbc816f03e274e
V2_ARCHITECTURE.md  8962bea0e34d330a162bfb8064792380f738c8b7837135a8665767a393ab57a3
```
全系统逐文件哈希见 `V1|V2|V3/manifests/FILE_INDEX.json`。

## 3. Python 语法检查

- 方式：`ast.parse` 全量扫描归档内全部 `.py`。
- 结果：**760 个 .py 文件，语法错误 0**。
- 附注：出现 3 处无害 `SyntaxWarning: invalid escape sequence '\A'`（docstring 中含 Windows 路径），
  非错误、非改动。

## 4. Import Smoke（**不执行**交易逻辑）

- 方式：设置 `MT5_RESEARCH_READONLY_MODE=1` / `MT5_ORDER_API_DISABLED=1`，以**包限定导入**方式导入
  纯库模块（不进入 `__main__`、不触发执行路径）。
- 结果：

| module | status |
|---|---|
| research_engine.statistics.multiple_testing | IMPORT_OK |
| research_engine.statistics.bootstrap | IMPORT_OK |
| research_engine.validation.split | IMPORT_OK |
| research_engine.core.signal | IMPORT_OK |
| alpha_engine.filters | IMPORT_OK |

5/5 通过。 ✅（未执行任何订单/连接账户代码）

## 5. Replay smoke（只读）

- 状态：**NOT_RUN（有意跳过）**。运行 replay 需加载运行上下文，存在触碰源/执行路径的风险；
  按“只读归档、零执行”原则**未运行**。语法 + import + 哈希三项已覆盖代码完整性。
  → 若要正式 replay 冒烟，请在**隔离环境**中、对源仓库只读副本执行。

## 6. 密钥再扫描（提交前）

- 工具：自定义健壮扫描器（无 gitleaks / detect-secrets）。
- 扫描文件：5248；敏感文件名命中 **0**；真实密钥 **0**；疑似命中 **1**（已判定 false positive：
  `V3/.../_v1_close_runid_r20.py` 中 `TOKEN="V1_RUN_20260924_RESET_01"` 是 run id）。
- 判定：`SECRET_FOUND=false`。详见 `SECURITY_SCAN_REPORT.md`。

## 7. 运行时排除记录

- `archive/ARCHIVE_MANIFEST.json#excluded_runtime_assets`：6,865 条（176 个整目录聚合 + 逐文件条目）。
- 明细：`archive/EXCLUDED_RUNTIME_ASSETS.jsonl`。
- 策略：`archive/RUNTIME_EXCLUSION_POLICY.md`。

## 8. 远端验证（**未做，因未 push**）

- `git remote -v` → 空（**无 remote**）。
- 未创建远端、未 push、未 force push。
- 待人工创建私有仓库 `AIQuant-XAUUSD-Systems` 后，方可执行：clone → compare → secret 复扫，
  即完整的 §C13 远端验证。

## 9. 提交与分支

| ref | commit | 说明 |
|---|---|---|
| `archive/2026-10-03-baseline` | `3c5e69d` → `c4976de` → (security commit) | 归档分支（本步骤先落此分支） |
| `main` | 同 archive tip | 验证后创建（fast-forward，无覆盖） |

> 提交信息见 §C14：`archive: V1 V2 V3 baseline source` / `docs: add architecture and version registry` /
> `security: add archive policy and verification`。

## 10. §23 最终状态块

```
Archive   : AIQuant-XAUUSD-Systems  (local staging repo)
Path      : C:\AIQuant-XAUUSD-Systems
Visibility: PRIVATE
Systems   : V1 (2655) / V2 (1126) / V3 (1108) / shared (339) / total tracked 5246
Secrets   : 0 real (1 false positive)
Scanner   : custom (gitleaks/detect-secrets unavailable)
Source    : C:\AIQuant @ 665bf2950302b57a5d8fa8bb539083c2df653286 (research/v2-grand-architecture-phase2)
Push      : NOT DONE (no remote, no push)
GitHub clone verification = PENDING_REPO_CREATION
FINAL STATUS = GITHUB_ARCHIVE_PARTIAL  (local complete; push pending remote creation)
```
