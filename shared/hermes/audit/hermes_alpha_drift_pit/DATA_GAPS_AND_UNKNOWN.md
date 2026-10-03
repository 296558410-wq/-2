# 数据缺口与 UNKNOWN（DATA_GAPS_AND_UNKNOWN）

> 原则：**无法证明 PIT / 输入不可复原 / 版本不可确认 → `UNKNOWN`，禁止补造、禁止用“应该”收尾。**
> 缺字段一律照实记；不得把推断写成事实。

## 1. 旧 V1（magic 90002）
| 缺口 | 影响 | 等级 |
|---|---|---|
| 早期决策**完整输入快照**已轮转（`run_state` 现仅 09-23→09-28；09-07→09-17 决策仅 `state_summary`） | 无法复原“当时 Hermes 看到什么”，无法做同输入重放，无法判定重启/时点是否改变输入 | `DATA_GAP`（v1_audit class-E） |
| `commission` / `swap` 未记录（trade master 标 `DATA_GAP`） | 真实净额只能靠券商 deal 另算；价差 vs 净额两口径需并列 | `DATA_GAP` |
| 入场时点 spread 未记录（可由 tick 推导 ~0.32–0.35bp） | 成本分析只能 `PARTIAL` | `PARTIAL` |
| 2026-09-13 / 09-15(0632) 等若干笔 tick 覆盖缺失 | 对应路径/MFE 不可算 | `DATA_GAP` |

## 2. 新 V1（magic 90011）
| 缺口 | 影响 | 等级 |
|---|---|---|
| 重启**之前**的 truth 决策快照不存在（truth 系统 10-02 才上线） | 无法用快照做重启前后逐字段对照（≠“无差异”） | `DATA_GAP` |
| 接线缺陷期 `data_age` 被写死 0、未记录真实值 | 当时数据新鲜度不可复原 | `UNKNOWN` |
| 归档 tick `ts_utc` 标签为服务器帧(UTC+3)；`broker_time_utc`/`last_bar_utc` 亦标 UTC 实为 UTC+3 | 已在分析中统一 −3h 换算；原始档保留 | `FACT（已知标注缺陷）` |
| tick 归档缺口 `2026-10-01T02:39:06→04:00:27Z`(81.3min) 覆盖 `V1T-2378208028`（盈利笔） | 该笔路径指标 `UNKNOWN`（不影响任何亏损归类） | `DATA_GAP` |
| ledger 历史 `PNL` 无 cost 字段 | 净额口径须用券商 deal 另算 | `PARTIAL` |

## 3. V2（PAPER）
| 缺口 | 影响 | 等级 |
|---|---|---|
| **0 笔真实（非 smoke）PAPER 成交**；6 条 `paper_executions` 全为 smoke/合成（`DEC-ctx-smoke`、`P`），`paper_account.realized_pnl=0.0`，仅 1 个合成 OPEN 位 | **无法评估 V2 的“先盈后亏”** → 该问 `NOT_EVALUABLE` | `DATA_GAP` |
| 1666 条决策**全部 `outcome=null`、`why_wrong=null`** | 无决策后果标注，无监督信号 | `DATA_GAP` |
| 75,394 条证据 `point_in_time_valid=unknown`（100%） | 无法认证 PIT | `UNKNOWN` |
| 73,315 个 evidence_id 带 `previous_content_sha256`（旧内容被覆盖），仅 31 个保留 >1 版本 | 决策时刻的**内容版本不可复原** → 内容级 PIT = 不可认证 | `PARTIAL/UNKNOWN` |
| 宏观 878/878 行 `release_timestamp_unknown=true`、`point_in_time_confidence=low`；38 行 `revision_changed=true` | 宏观 PIT 不可证；存在修订回填风险 | `FAIL_UNKNOWN` |
| 1,482 条决策引用的 evidence_id 不在 registry | 引用链不完整 | `DATA_GAP` |
| `decision_source=reference_rules`（占位参照器），非设计的 LLM Hermes | V2 的“Hermes 判断力”未被真正测试 | `FACT` |

## 4. 跨系统 / 方法学
| 缺口 | 影响 | 等级 |
|---|---|---|
| 三系统**样本极小**（V1_OLD 109 笔/15 日、V1_NEW 32 笔/5 日、V2 0 笔） | 任何“漂移/变化点”判定统计功效不足 | `INSUFFICIENT_EVIDENCE` |
| “前期/后期”窗口由观测者选定 | 存在选择偏差；已在报告显式声明并锁定 | `INTERPRETATION` |
| DXY/UST10Y/VIX：V2 观测中确有（`v2_observe_only` 触发理由含 UST10Y/VIX）；V1_OLD/V1_NEW 未见记录使用 | V1 侧外部宏观输入 `UNKNOWN/NOT_USED` | `UNKNOWN` |
| Hermes `model/version/prompt hash`：V1_OLD 决策含 `model` 字段（近期），早期 `UNKNOWN`；V1_NEW 无 LLM；V2 无 LLM 决策 | prompt/model hash 级对照不可做 | `UNKNOWN` |

## 5. 不得补造的清单（照实留 UNKNOWN）
- 旧 V1 早期“当时输入”→ `UNKNOWN`
- V2 决策时刻证据**内容版本** → `UNKNOWN`
- 重启瞬间的“反事实（若非重启会怎样）”→ `UNKNOWN`（未知反事实，不作因果）
- V1_NEW 缺陷期真实 `data_age` → `UNKNOWN`
