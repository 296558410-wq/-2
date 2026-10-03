# V3 RESEARCH FINAL STATUS（统一收尾 / 冻结 / 交接）

- 生成：2026-10-02（GMT+8）· 范围：`research/hermes/trader_v3`（V3 独立；V1/V2 未触碰）
- 本文件为 **V3 当前阶段的唯一权威状态页**；更细的每轮报告见各自目录。
- 冻结判据见 `V3_FREEZE_ACCEPTANCE.json`；全量哈希见 `V3_FREEZE_MANIFEST.json`（414 个产物 + 9 个协议哈希 + 原始数据引用）。

## 0. 四个验收

```text
V3_RESEARCH_FREEZE   = PASS
V3_HANDOFF           = PASS
TEMPORAL_HOLD        = RUNNING
TRADING_EXECUTION    = DISABLED   (RESEARCH_READONLY / ORDER_SEND=NO / FORWARD=NO / LIVE=NO)
```

## 1. 当前最终状态（先说）

```text
最终证据等级 = TEMPORAL_EVIDENCE_INSUFFICIENT
候选结论     = 全部 NO_VALIDATED_EDGE（无一通过 BH-FDR / bootstrap / 时间门）
唯一阻断条件 = G1：同源数据跨度 < 90 天（当前 59.40 天；门槛未降）
下一步       = 仅允许「Frozen R4 Revalidation」（等 TEMPORAL_READY + 用户指令）
```

## 2. 各轮结果一览（全部保留，未删除任何失败/UNKNOWN）

| 轮次 | 内容 | 结果 | 协议哈希（registry_hash_sha256） |
|---|---|---|---|
| Alpha Sweep R1 | 24 假设机制级 XAUUSD HFT 扫描 | NO_VALIDATED_EDGE | `45598674ab8645a1…` |
| F-R1 | 分钟级（1m–60m）结构搜索 | NO_VALIDATED_EDGE | `b0f20e6618b69861…` |
| F2b-R2 | 修正尺度 MA-reversion 正式验证 | NO_VALIDATED_EDGE | `4d45154f17d89142…` |
| Phase2 R1 | 新机制发现（冻结 tick 快照） | NO_VALIDATED_EDGE (COST_INSUFFICIENT) | `663829a925e87ae1…` |
| D-R1 | 事件微观结构 | NO_VALIDATED_EDGE (COST_INSUFFICIENT) | `7e1028555648e906…` |
| E-R1 | tick 微观结构 | NO_VALIDATED_EDGE | `a36765feb3760da1…` |
| R2-confirmation | P3 独立复核 + X3 beta 零检验 + 数据缺口审计 | 见该轮报告（无升级结论） | `a9f4dd4f9cfcd704…` |
| R3-integrity | 时间审计 + **event-loader 重建** + X3 market-neutral | 完整性修复（不改结论） | `bae1511f9d205fba…` |
| **R4-F5** | 90 天时间扩展 + 修正 loader 上的 F5 重验 | **TEMPORAL_EVIDENCE_INSUFFICIENT** | `adc5a94d7c12d384…` |

## 3. Event loader 修复记录（R3/R4，保留原样）

- 缺陷（R1）：`set((ts, 文件名))` 去重把 **283 行折成 75 个时间戳** ⇒ F5 族样本被少算。
- 修复：主键 `(pub_time_utc, title, source_file)` 按行计数；R4 终值 = **283 raw → 249 窗口内 / 67 独立时间戳**（并发 208 保留、真重复 0）；守恒链与损失原因逐条记录。
- R3 自身第一版实现错误（虚构字段主键）亦作为记录保留在 R3 结果中。

## 4. F5 数字（R4，完整表见 `v3_r4_temporal_f5/F5_R4_REPORT.md`）

- 样本：E1 n=46 / E2 n=60 / E3 n=9 / E4·E5 n=60（独立时间戳同数）；
- gross / net@1x：E1 5m +1.621/+0.707 · E2 5m +1.619/+0.705 · **E4 15m +2.229/+1.315** · E3 负 · E5 负；
- **成本阶梯**：2× 后仅 E4-15m 为正（+0.401）；3× 全负；
- **bootstrap**：全部 CI 含 0（E4-15m [−0.166, +4.561]）；
- **permutation**：最优 p=0.0295（E3，eff_n=6，不显著）；其余 ≥0.076；
- **BH-FDR**：24 项 **0 存活**；
- **Temporal Gate**：G1 ❌（59.11d<90d）· G2 ✅（44≥40）· G3 时间块（E2-5m、E4-15m net 同号，但不过显著/门）；
- ⇒ 所有候选（含镜像）`TEMPORAL_EVIDENCE_INSUFFICIENT`。

## 5. 数据覆盖（截至 2026-10-02 10:42Z）

| 项 | 值 |
|---|---|
| 同源快照 | staging_fxtm(24 文件) + live_fxtm(20 文件)，共 44 文件 / 8,951,761 ticks |
| 覆盖 | 2026-08-04 01:05Z → **2026-10-02 10:39Z** = **59.3987 天**；活跃日 **44** |
| 连续性 | 时间空隙段 55；>1h 缺口 51（最大 57.25h＝staging→live 接缝；周末休市 49.17h×4 属正常） |
| PIT | OK（逐文件单调、列齐备、ts=UTC ms、volume=0 报价代理；采集即记录） |
| 快照 manifest | `3417edf9814f9b0f…`（R4 冻结快照，已复验 MATCH） |
| 异源 | DUKA 等**未使用**（不同源+不同 schema） |

## 6. Temporal Hold（RUNNING）

- 机制：`research/v3_temporal_hold/`（每日检查 → `HOLD_LOG.jsonl`+`HOLD_STATUS.json`）；日志首日含一条 instrument-fix 记录（ts 单位 bug，已修复并保留）。
- 自动化：① `v3-temporal-hold-daily-check`（每日 09:40 GMT+8，零-LLM，静默）② `v3-temporal-hold-ready-watch`（每 6h；**一次性**，达标时向本会话报 `TEMPORAL_READY`）。
- **预计 TEMPORAL_READY = 2026-11-02T01:05Z**（约 31 天后；若采集连续）。G2 已达标；**唯一缺口 = G1 的 ~30.6 天**。

## 7. 已证伪 / 未验证 / 未解决

**已证伪（保留为失败证据）**：以上 9 轮全部候选机制族在成本与统计口径下均无 validated edge；B 族结构性 NOT_TESTABLE（无真实成交量）；"R1 样本量 75" 为 loader 缺陷产物。
**未验证（数据/方法缺口）**：≥90 天样本下的 F5 行为；G3 的持续性；session/vol/spread 拆分的泛化；E3（n≤9）；执行层建模与成本锚再导；GPU 大规模性能。
**未解决（UNKNOWN）**：时段外 34 个事件；staging→live 3 天接缝；无真实成交量字段。

## 8. Git（可追溯）

- 本日 V3 关键 commit（全部 path-limited `research/hermes/trader_v3/**`）：
  `568fd8e → … → cf755fe → 78f5343 → efe1fee → ecb0b48 → 4e99a15 → 4b87073 → 83f7d82 → d64a17e → ddd10ba → df996a8 → 1ab7a37 → 收尾 commit `535731c`（+ 记录提交）`
- 本次收尾提交内容：`gpu_infra/` + `research/v3_freeze_handoff/`（含本文件、`V3_FREEZE_MANIFEST.json`、`V3_FREEZE_ACCEPTANCE.json`）。

## 9. GPU 基础设施（V3_GPU_INFRA）

- `research/hermes/trader_v3/gpu_infra/`：R4 语义 bootstrap/permutation 核（CPU/GPU）、4GB 分块、OOM 回退、向量化 tick 特征、batch、CPU/GPU parity、benchmark。
- 自检 **8/8 PASS**；permutation 3.4× 加速（bootstrap 小规模 CPU 更快，如实记录）。**仅基础设施，无交易结论。**

## 10. 下一阶段唯一入口

```text
NEXT STAGE = Frozen R4 Revalidation（唯一允许动作）
入口条件：TEMPORAL_READY 报告 + 用户明确指令
执行要求：完全相同的冻结 R4 协议（F5_R4_FROZEN_PROTOCOL.json adc5a94d…），
          不调阈值/方向/持有期/成本锚/统计方法/门槛；不得引入新假设或新 family。
```

**本文件写入后：V3 主动研究停止；不自动启动任何新 Alpha 研究或交易执行。**

---
*附表：协议哈希全量 9 条见 `V3_FREEZE_MANIFEST.json::protocol_hashes`；产物 414 件逐文件 SHA256 同文件。*
