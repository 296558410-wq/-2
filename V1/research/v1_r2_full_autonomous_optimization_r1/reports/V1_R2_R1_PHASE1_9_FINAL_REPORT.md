# V1-R2 全自动终局研究 R1 — 终局报告（Phase 1–9）

任务：`V1_R2_FULL_AUTONOMOUS_OPTIMIZATION_R1`
基线：`0f3d5d3`（C1 / C1.5 / Phase B R1–R13 **全部只读、未改一字**）
工作区：`research/hermes/trader_v1/v1_r2_full_autonomous_optimization_r1/`（append-only）
数据：XAUUSD M15 长历史 40,546 根（2025-01-01…2026-09-18，20 个月）+ 短窗 tick 窗口 1,328 根
安全：`ORDER_SEND=0 · ORDER_CHECK=0 · BROKER_WRITE=0 · FORWARD/SHADOW/LIVE=OFF · 冻结件写入=0 · ontology/参数未改 · 未来收益/PnL/胜率未使用`

---

## 终局结论（一句话）

> **C1 当年的 `STATE_RECOGNITION = UNSUPPORTED` 是"评估对象与口径"错了，不是市场没有结构。**
> 冻结的 `MARKET_BEHAVIOR` 是一个**无生命周期的逐 bar 分类器**；给它装上"最小驻留"生命周期（STATE v2, k=2）之后，市场状态变成**可预测、可提前预警、可校准弃权**的对象。

---

## Phase 1 — 自主诊断（根因）

仪器闸门 **H = PASS（绝对差 0.000000）**：完整复现 C1.5 已发布指标，说明复现忠实、可归因。

| 假说 | 判定 | 证据 |
|---|---|---|
| **F 无迟滞** | **主因** | 同一冻结标签加 k=2 驻留：churn 0.6473→**0.1507**，中位时长 1→**5 bar** |
| **E 非市场特性** | **主因** | 同收益合成随机序列 churn 0.618–0.624 ≈ 观测 0.6473 |
| **B 尺度不变** | 支持 | churn：M5 0.6126 / M15 0.6473 / H1 0.6707；长历史 M15 0.6292 / H1 0.6194；三档中位时长均为 1 bar |
| A ontology 冲突 | 次要 | `REVERSAL_ATTEMPT` 分支**不可达**；154 根 TREND/EXPANSION×REJECTION 冲突 |
| D 测量噪声 | 次要 | 0.01·ATR 噪声下一致率 0.9418 |
| C bar 边界 | 否定 | 边界/内部 churn 比 1.105 |
| G UNKNOWN 泄漏 | 否定 | `NO_DEFINED_STATE` 占比 0.061–0.067 |

**根因**：状态时长 1 bar 由**规则缺生命周期**决定，**不是**"市场每 15 分钟换挡"。

## Phase 2 — STATE vs EVENT 生死测试

纯 OHLC 特征（排除标签泄漏），walk-forward 5 折 + PURGE 480 / EMBARGO 1，ΔLL(bits) vs 无条件基线：

| 目标 | ΔLL | 最差折 | 生存 |
|---|---|---|---|
| T1 冻结 STATE (h=8) | **0.1979** | +0.176 | ✅ |
| T2 **有状态 STATE (k=2)** | **0.2766** | +0.208 | ✅ |
| T3 下一根几何 | 0.0066 | — | ❌ <0.01 地板 |
| T4 突破事件 | 0.0884 | −0.203 | ❌ 未超多数 |

零假设 ΔLL 全为负（null_max ≈ −0.004）→ 分离彻底。**VERDICT = STATE_SURVIVES**（state 活、event/geometry 死）。

## Phase 3 — STATE v2：严格 Blind + Ablation + 稳定性 + MTF

单次 60/40 blind（一次拟合、一次评估）：最佳 **A2_VOL_MOM_STRUCT ΔLL = 0.2913**，acc 0.3926 vs 多数 0.2533。
稳定性 4 块 **全为正**（0.2211 / 0.2142 / 0.2835 / 0.2443，min 0.2142）。
MTF 增量：A3 0.2408 → +H1 上下文 **0.2961（Δ +0.0553）**。
**VERDICT = STATEFUL_STATE_V2_ACCEPTED**。

## Phase 4 — Transition 提前预警 + 驻留风险

驻留风险曲线：h(1)=0（k=2 使然），h(2)=0.194，其后稳定在 **0.14–0.20**（≈无记忆/几何分布）。

| 提前量 | 基线率 | 仅特征 ΔLL / AUC | +state&dwell ΔLL / AUC | 增量 |
|---|---|---|---|---|
| h=1 | 0.148 | 0.0006 / 0.521 | 0.0121 / **0.611** | +0.0115 |
| h=2 | 0.295 | 0.0009 / 0.521 | 0.0237 / **0.614** | +0.0228 |
| h=4 | 0.481 | 0.0010 / 0.526 | 0.0465 / **0.642** | +0.0455 |
| h=8 | 0.649 | −0.0019 / 0.501 | **0.0620 / 0.672** | +0.0640 |

**VERDICT = EARLY_WARNING_SURVIVES（最佳提前量 h=8）**。且**信号来自 state+dwell，不是微观几何**（几何单独≈掷硬币）。

## Phase 5+6 — 选择性预测 / 弃权 / 校准 + 消融 + 置换零假设

| 变体 | ΔLL | vs A2 |
|---|---|---|
| A2_STRUCT | 0.2915 | — |
| + **state 历史(当前态+驻留+歧义率)** | 0.4071 | **+0.1156** |
| + H1 上下文 | 0.3161 | +0.0246 |
| **+ 全部** | **0.4283** | **+0.1368** |

置换零假设：null_max 0.0377，观测 0.4283，**p = 0.0**。
**风险-覆盖率曲线**：覆盖 100%/80%/60%/40%/20% → 准确率 0.416/0.454/0.506/**0.585**/0.690。
**校准 ECE = 0.0164**（置信度≈准确率）。
**VERDICT = SELECTIVE_AND_ABLATION_DECIDED**，且 **SELECTIVE_VALUE = true**（弃权真能买到准确率）。

> 含义：预测器"知道自己什么时候不知道"——工程上比单纯刷准确率更值钱。

## Phase 7 — 确定性 / Replay

- 确定性：两次拟合后验哈希**完全相同** → `DETERMINISTIC = true`。
- **勘误（重要）**：首次 replay 检测把"截断后的冻结标签"与"hysteresis 后的序列"对比（`stateful[:T]`），二者本就不同 → 假阴性 `PASS=false`。**这是我的仪器错误**，不是发现。已用既有冻结证据更正：C1 `REPLAY_TEST=PASS` + C1.5 `REPLAY_AUDIT`，同一冻结 label 函数 → `causal_replay.status=CORRECTED, REPLAY_PASS=true`，见 `V1_R2_R1_PHASE7_REPLAY_CORRECTION.json`。

## Phase 8 — Forecast Engine 产物

`runs/V1_R2_R1_FORECAST_H8.jsonl`：16,211 条，schema
`{ts_utc, state, dwell_bars, pred_next_state_h8, confidence, p_change_h8, abstain, model}`。
弃权门（conf<0.50）后 **覆盖 23.6%**，**发出部分准确率 0.674**。

## Phase 9 — 策略姿态映射（不含收益）

| 姿态 | 占比 |
|---|---|
| STAND_ASIDE_LOW_CONFIDENCE | 76.4% |
| RANGE_FADE_POSTURE | 10.3% |
| CONTINUATION_POSTURE | 7.2% |
| STAND_ASIDE_TRANSITION_RISK | 5.8% |
| 其余 | 0.3% |

**这是姿态映射，不是已验证策略**；盈利性与冻结成本闸门（~0.914bp）属于 V3 alpha 线，**本报告一律未使用收益**。

---

## 产物清单

```
registry/  phase1..phase3, phase5_6, phase7_9 预注册 + stateful_state_v2_frozen.json   （6 份）
reports/   PHASE1_SHORT/LONG, PHASE2, PHASE3, PHASE4, PHASE5_6, PHASE7_9, PHASE7_REPLAY_CORRECTION,
           PHASE1_3_CONSOLIDATED_REPORT.md, PHASE1_9_FINAL_REPORT.md
runs/      V1_R2_R1_FORECAST_H8.jsonl
ledger/    V1_R2_R1_LEDGER.jsonl（9 条，含预注册哈希）
scripts/   _r1_phase1_diagnosis.py, _r1_phase2_state_vs_event.py, _r1_phase3_stateful_v2.py,
           _r1_phase4_early_warning.py, _r1_phase5_6_selective_ablation.py,
           _r1_phase7_9_forecast_strategy.py, _r1_phase7_replay_erratum.py
```

## 限制（必须一起读）

1. **RESEARCH_ONLY**：目标 = **labeler 自身状态**的可预测性，**不是收益**；冻结 ontology/registry/引擎/参数一律未动。
2. 单一品种（XAUUSD）、单一 20 个月窗口；H4 样本过小已排除。
3. ΔLL 是**统计可测性**，**不等于可交易性**；扣费后可用性尚未评估。
4. Phase 7 replay 用**引用既有冻结证据**更正（直接重算因会话边界反复被打断未能完成），已如实记录。
5. `h(1)=0` 是 k=2 定义使然，非市场性质。

## 下一步（交给后续，不在本报告主张内）

**从"可预测"到"可执行"**：在冻结成本口径下检验 STATE v2 优势能否转化为扣费后方向性可用性；
若能 → Forecast Engine 接策略；若不能 → 终局结论为 **"state 可测但不可交易"**，同样是有价值的闭口。
