# GITHUB_CLEAN_SNAPSHOT_AUDIT.md

> 生成（UTC）：2026-09-19T02:09:55.685785+00:00
> 方式：**只读源 + 只写 staging**；未 add remote / 未 push / 未 commit / 未改历史 / 未改原文件。

## 1. Source
```text
C:\AIQuant   （原始项目；本次未做任何修改）
```

## 2. Staging
```text
C:\AIQuant\github_publish_staging
```

## 3. 文件统计
- 文件数：**546**
- 总大小：**3.52 MB**

| 类别 | 文件数 |
|---|---:|
| Audit | 51 |
| Configuration templates | 2 |
| Documentation | 51 |
| Hermes | 141 |
| Research report | 43 |
| V1 | 38 |
| V2 | 198 |
| V3 | 22 |

## 4. 排除统计

- 排除文件总数：**27305**（其中本次裁定/强制**额外排除 +66**：`trader_summary.txt` + `memory/reviews/*.json` ×65；其余为扫描期间新增的运行态文件）
- 覆盖：运行态 / 缓存 / 凭据 / 账户快照 / 原始新闻 / market data / logs / temporary files
- 关键项确认未进入 staging：
```text
trader_v2/state/evidence_registry.jsonl
trader_v1/run_state/plan_ledger.jsonl
run_state/**
state/**
*.jsonl
.env*
demo_calibration/**
data_cache/**
```

### 4b. MANIFEST_DISCREPANCY（manifest 分类与实际不一致）

| 文件 | 问题 | 处置 |
|---|---|---|
| `research/hermes/trader_v1/trader_summary.txt` | 运行态交易日志(order tickets/equity/positions)，manifest 误归 V1 | 已排除（§7 强制） |
| `research/hermes/trader_v1/memory/reviews/  (65 个 *.json)` | V1 运行/复盘记忆数据（entry/exit/PnL），非协作代码基线 | 已排除（用户裁定 2026-09-19） |

**用户裁定排除（2026-09-19）**：`trader_v1/memory/reviews/*.json`（V1 运行/复盘记忆，含 entry/exit/PnL）已从 staging 排除；原文件保留。

## 5. 脱敏记录（仅 staging 副本）

| 文件 | 类型 | 次数 |
|---|---|---:|
| `research/hermes/trader_v2/dashboard/acc_probe.py` | MT5 登录账号 | 1 |
| `research/hermes/trader_v2/dashboard/datasource.py` | MT5 登录账号 | 1 |
| `research/hermes/trader_v2/execution/broker_demo_executor.py` | MT5 登录账号 | 1 |
| `research/hermes/trader_v2/execution/fxtm_demo_adapter.py` | MT5 登录账号 | 1 |
| `research/hermes/trader_v2/research/AUDIT_BASELINE_20260915.md` | MT5 登录账号 | 1 |
| `research/hermes/trader_v2/research/BASELINE_AUDIT_20260914.md` | MT5 登录账号 | 1 |
| `research/hermes/trader_v2/research/FXTM_DEMO_CALIBRATION_PHASE2.md` | MT5 登录账号 | 3 |
| `research/hermes/trader_v2/research/FXTM_DEMO_CALIBRATION_PHASE2.md` | broker order ticket | 2 |
| `research/hermes/trader_v2/research/ISSUE_20260915_replay_block.md` | MT5 登录账号 | 1 |
| `research/hermes/trader_v2/research/ISSUE_20260915_replay_block.md` | broker order ticket | 1 |
| `research/hermes/trader_v2/research/MODULE_6_REPORT.md` | MT5 登录账号 | 4 |
| `research/hermes/trader_v2/research/MT5_MULTI_INSTANCE_AUDIT.md` | MT5 登录账号 | 1 |
| `research/hermes/trader_v2/research/V2_BROKER_DEMO_ENABLE_20260918.md` | MT5 登录账号 | 2 |
| `research/hermes/trader_v2/research/V2_BROKER_DEMO_ENABLE_20260918.md` | broker order ticket | 1 |
| `research/hermes/trader_v2/research/V2_FULL_AUDIT_20260917.md` | MT5 登录账号 | 1 |
| `research/hermes/trader_v2/tests/test_broker_reconcile.py` | MT5 登录账号 | 2 |
| `research/hermes/trader_v2/tests/test_module6_broker_demo.py` | MT5 登录账号 | 2 |
| `research/hermes/trader_v2/tests/test_v2_repair.py` | broker order ticket | 1 |

- 脱敏后残留：MT5 账号 **0** / order ticket **0**（均应为 0）

## 6. 原始文件完整性

- 源文件仍存在（未被删/改）：`{'research/hermes/trader_v1/trader_summary.txt': True}`
- 原始 Git history commits：before **249** / after **249**（未变）
- `git remote -v`：（空，未连接）

## 7. 安全扫描（staging）

- 含 credential 关键词文件：**67**（通用词为主，需人工二核）
- 硬编码 `key=value` 凭据：**无**
- MT5 账号残留：**0** ｜ order ticket 残留：**0**
- broker 服务器名 `ForexTimeFXTM-Demo01`：**12** 文件 → `BROKER_SERVER_METADATA_ONLY`（保留）
- 本机路径 `C:\AIQuant`：**60** 文件 → `LOCAL_ENVIRONMENT_REFERENCE`/`PATH_REFACTOR_REQUIRED`
- 本机用户名 `C:\Users\...`：**6** 文件
- 运行态痕迹文件：**无**
- 脱敏后 staging 内 .py 语法自检：**全部通过**

## 8. GitHub 发布风险

| 项 | 等级 | 说明 |
|---|---|---|
| 凭据(password/token/api_key/private key) | CLEAR | 二次扫描无硬编码凭据 |
| MT5 登录账号 | CLEAR | staging 已脱敏，残留 0 |
| MT5 密码 | CLEAR | 从未入库 |
| order ticket | CLEAR | 已脱敏，残留 0 |
| 运行态数据 | CLEAR | staging 无运行态文件 |
| broker server 元数据 | LOW | 仅服务器名，已标记 |
| 本机路径/用户名 | MEDIUM | 60+6 文件；报告类可保留，代码依赖 `PATH_REFACTOR_REQUIRED` |

## 结论

**最终状态：CLEAN_SNAPSHOT_FROZEN_FOR_GITHUB**

_未 push、未 add remote、未 commit、未改历史、未改原文件。_
