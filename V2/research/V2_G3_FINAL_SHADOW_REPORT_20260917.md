# V2 G3 FINAL SHADOW REPORT — 20260917

> **定稿（FINALIZED）** — cron `v2-g3-48h-audit`，ts_utc `2026-09-19T11:07:51Z` (19:07 CST)。
> 本文件为 run `V2-SHADOW-20260917-105319-b5e4` 的 G3 终结报告，**替换**该文件 2026-09-17T18:54Z 的临时快照（当时读数：0.0h / 1 cycle / `INSUFFICIENT_EVIDENCE`）。
> 只读审计；未改策略 / V1 / V3 / 历史 run；未发任何 broker 单；**未进入 Forward**。

## 数据层冻结版本
- freeze git: `8d997fb` · schema pit=`pit/1` · input_snapshot=`input_snapshot/1`
- versions: `{"strategy_version": "hermes2-prompt/0.1.0", "agent1_version": "agent1/0.1.0", "agent2_version": "agent2/0.2.0-pit", "hermes_version": "hermes2/0.1.0", "paper_engine_version": "paper/0.1.0", "ledger_version": "ledger/1"}`
- freeze清单: `research/V2_G3_DATA_FREEZE_20260917.md`（git `8d997fb` / config sha `7bfab969…`）

## Shadow run（本次审计对象）
- run_id: `V2-SHADOW-20260917-105319-b5e4`（RUN_META `shadow=true` / `PAPER, no-broker`）
- manifest start: `2026-09-17T10:53:19Z` · manifest end（计划 48h 窗口）: `2026-09-19T10:53:19Z`
- **实际 end / status**: `2026-09-18T10:25:08Z` / **STOPPED**
- **实际连续运行**: **23.53 h**（< 24h）；墙钟自 manifest start 计 48.23 h
- cycle 数: **90** · 决策 TRADE 8 / WAIT 82 / REJECT 0
- 执行: attempts 8 / executed 5 / rejected 3（rejected 均为 `RISK_LIMIT`，发生在 sizing 修复 F3 之前）
- failures: agent1 0 · agent2 0 · hermes 0 · ledger 0 · restarts 0 · blocked: null

## 每类 WAIT 原因（reason_code）
- TECH_MACRO_CONFLICT（技术/宏观冲突）: 37
- NO_FOLLOW_THROUGH（无跟随）: 30
- TRADE_OK（证据通过门禁）: 12
- PRICED_IN（已 priced-in）: 9
- DATA_DEGRADED（数据降级）: 4
- DATA_STALE（数据陈旧）: 2

## 数据源稳定性 / GAP
- 主行情: `XAUUSD (router: mt5→local_fxtm→yahoo) + quotes/macro sina/tencent(国内) + reference GC=F`
- 数据 GAP（显式，不填 0/不伪造）: `["central_bank_policy_rates:no_direct_api(placeholder)", "bls_macro:no_domestic_source(BLS 403)", "cot:no_domestic_source(CFTC 403)", "global_gold_etf_flows:WGC_JS(未取)", "central_bank_gold_purchases:no_source"]`

## 证据链
- Replay MATCH: **90/90**
- Ledger hash chain: **PASS** `{"n": 220, "head": "fd982c71a37ae259f543a206bbac3e810dafe4f6da3b88f429305adee84be38d"}`
- Scheduler 漏周期: **4 段 gap / 5 个缺失窗口** → `10:45Z→11:15Z`(缺 11:00Z)、`14:00Z→14:30Z`(缺 14:15Z)、`21:30Z→22:00Z`(缺 21:45Z)、`22:30Z→23:15Z`(缺 22:45Z、23:00Z)（均 2026-09-17）
- input_snapshot: 90/90 cycle · inputs 快照文件 94 个（全部 XAUUSD）
- timeline 行数 90

## 安全不变量
- execution_mode（运行语义）: PAPER (shadow/no-broker)，但 manifest 字段记录为 `BROKER_DEMO`（元数据不一致，见下）
- BROKER_ORDER_SENT: **FALSE**（全程无 broker 单）
- FORWARD_VALIDATION_ALLOWED: **YES**（文件现存在；09-18 切 BROKER_DEMO 时开启）— ⚠️ 与"保持 NO"的 G3 契约不符
- FORWARD_STARTED: FALSE（本次审计未启动、不得启动）
- V1 隔离(静态): PASS

## 20 项 PASS 条件（§九）
| # | 条件 | 判定 | 说明 |
|---|---|---|---|
| 1 | 连续运行 | **FAIL** | 实际仅 23.53h（<24h，且未达 48h 即 STOPPED）。工具按墙钟 48.2h 会判 PASS —— 此处按**实际运行时长**判 FAIL |
| 2 | scheduler 无漏周期 | **FAIL** | 4 段 gap / 5 个缺失窗口（09-17 11:00/14:15/21:45/22:45/23:00Z）→ 硬失败项 |
| 3 | 无 stale_backfill | PASS | timeline 无 backfill 标记 |
| 4 | XAUUSD 标的一致 | PASS | 94 个 input 快照全为 XAUUSD |
| 5 | PIT 无未来数据 | PASS | offline_replay 未报未来时间戳 |
| 6 | Router 来源可追溯 | PASS | manifest `market_data_source` + per-cycle pit_cache source/source_hash |
| 7 | Agent1 provenance | PASS | agent1_error 全 0 |
| 8 | Agent2 provenance | PASS | agent2_error 全 0 |
| 9 | Hermes input_snapshot | PASS | 90/90 |
| 10 | WAIT 可解释 | PASS | 每 cycle 均有 reason_code（见上分布） |
| 11 | Replay 全 MATCH | PASS | 90/90 |
| 12 | Ledger hash chain | PASS | n=220，verify=True |
| 13 | 无真实 Broker 单 | PASS | shadow/no-broker；BROKER_ORDER_SENT=FALSE |
| 14 | V1 无变化 | PASS | 静态隔离检查通过 |
| 15 | Dashboard 与 backend 一致 | PASS | 由既有一致性测试覆盖（本次未重跑） |
| 16 | stale/error/unknown 未伪装 | PASS | reason_code + GAP 显式 |
| 17 | 数据源失败显式暴露 | PASS | 5 项 GAP 显式列出 |
| 18 | 无新策略修改 | PASS（附注） | 策略/prompt/候选未改；但 `hermes/context.py` 门禁逻辑在 run 中变更（F1，数据安全）→ 见 §冻结完整性 |
| 19 | 无未批准参数优化 | PASS | 配置变更均经用户授权，且 `per_trade_pct` 系回退基线值（非优化） |
| 20 | 单冻结版本样本 | **FAIL** | run 期间 config（3 次）+ 代码（3 文件）被改动，样本非单一冻结版本 |

**硬失败项**: `1_连续运行`（实际）、`2_scheduler无漏周期`、`20_单冻结版本样本`

## §冻结完整性（关键偏离）
冻结契约（`V2_G3_DATA_FREEZE_20260917.md`）规定：**冻结后禁止改策略/阈值/候选/风险参数；发现数据安全 bug → 单独提交 + 重新冻结 + 重启 G3 计时**。run `b5e4` 期间发生：
- config `v2_config.json` 3 次变更：`7bfab969`(冻结) → `91c3587b`(mode→PAPER) → `b0cc254b`(回 BROKER_DEMO + per_trade_pct/backend 改动)
- 代码 3 文件变更（F1/F2 数据安全）：`hermes/context.py`、`execution/fxtm_demo_adapter.py`、`data_sources/mt5_market.py`
- 22:45Z(09-17) 窗口执行被 `NON_PAPER_MODE: mode=BROKER_DEMO` 拒绝（incident），run_state 出现缺口
> **未重新冻结、未重启 G3 计时** → 按冻结契约，该 run 的 48h 样本不能视为"单一冻结版本"，须重跑。

## 工具运行结果（本次审计）
- `tools/shadow_guardian.py --mode evaluate` → `{"skipped": "no_shadow_run", "active": "V2-PAPER-20260919-014104-084c"}`（**未评估 b5e4**：ACTIVE 已非 shadow run）
- `tools/runtime_audit.py --seconds 15` → `model_hits=[]`（**PASS(无 model/API/Gateway 端点)**），remote 30，python 16 → `research/V2_RUNTIME_PROCESS_NETWORK_AUDIT_20260919.md`
- `tools/g3_final_report.py` → 因 ACTIVE 指向非 shadow run，产出 `research/V2_G3_FINAL_SHADOW_REPORT_20260919.md`（run `…084c`，hours 9.4，cycles 0，verdict FAIL：`13_无真实Broker单`）——**非本 run 报告**

## 环境偏离（前提失效）
- b5e4 于 `2026-09-18T10:25:08Z` 被 STOPPED，随即由 BROKER_DEMO run `V2-PAPER-20260918-102531-8648` 接替（用户 09-18 18:2x CST 指令"切模拟盘真实下单"）。
- 当前 ACTIVE = `V2-PAPER-20260919-014104-084c`（BROKER_DEMO，cycles 0）。
- ⇒ 系统已不在 G3 shadow 阶段；本 48h 审计的原始前提（b5e4 持续 48h）已不成立。

## FAIL / BLOCKED / UNKNOWN
- blocked: null
- hard_fail（工具口径）: `2_scheduler无漏周期`；（本次判定另含 `1_连续运行`、`20_单冻结版本样本`）
- 未决（P1 residual / 数据 GAP）: COT / BLS / 东财资金流 / WGC / 央行购金 / 政策利率
- UNKNOWN: 15_Dashboard 一致性未在本次重跑

## G3 最终结论
**FAIL**

- 理由：① scheduler 存在 4 段漏周期（硬失败）；② 实际连续运行仅 23.53h（<24h，未达 48h 窗口即停止）；③ run 期间 config/代码被改动，样本非单一冻结版本（冻结契约要求重冻+重启），故不满足 §九 全部 PASS 条件。
- 本 FAIL 为**流程/门禁未达标**（非策略爆亏）：证据链本身干净（Replay 90/90、Ledger PASS、BROKER_ORDER_SENT=FALSE、V1 隔离 PASS）。

> 下一阶段：**不得自动进入 Forward**；`FORWARD_STARTED=FALSE`。G3 **未 PASS** → 需按冻结契约**重新冻结并重跑**干净的 24h/48h shadow，再由人工确认 → G4。`FORWARD_VALIDATION_ALLOWED` 当前虽为 YES（09-18 切 BROKER_DEMO 时所开），但**本次审计不得据此启动 Forward**。
