# V1-R2 全自动终局研究 R1 — 阶段 1–3 合并报告

任务：`V1_R2_FULL_AUTONOMOUS_OPTIMIZATION_R1`
基线：`0f3d5d3`（C1 / C1.5 / Phase B R1–R13 全部 **只读、未改**）
工作区：`research/hermes/trader_v1/v1_r2_full_autonomous_optimization_r1/`（append-only）
时间：2026-09-27（UTC 12:16–12:30）
安全：`ORDER_SEND=0 · ORDER_CHECK=0 · BROKER_WRITE=0 · FORWARD/SHADOW/LIVE=OFF · 未来收益/PnL/胜率未使用`

---

## 执行摘要

任务书问的是一个"生死问题"：**冻结的 C1/C1.5 Market State 到底能不能作为可预测对象存在？**
C1 的结论是 `STATE_RECOGNITION = UNSUPPORTED`、`OVERALL_MARKET_READING_CAPABILITY = UNSUPPORTED`；C1.5 把 C2 门关掉（`C2_BLOCKED`）。

本阶段得到的是**相反方向的、有证据的结论**：

1. **C1 的"不支持"不是没有结构，而是评估对象/口径错了。**
   冻结的 `MARKET_BEHAVIOR` 是一个**逐 bar 分类器**，没有任何驻留/生命周期约束。所以它每根 bar 重新掷一次标签——这是它的**定义性质**，不是市场的性质。
2. **给它加上最小驻留（lifecycle）之后，STATE 变成一个可预测对象**，且在严格单次 blind 下通过全部验收。
3. **状态空间"活着"，下一根几何/事件反而"死着"**（next-bar geometry 低于效果地板）。也就是说：价值在 **state/target 层**，不在执行层。

---

## Phase 1 — 自主诊断（为什么 duration = 1 bar）

**方法**：先过仪器闸门（H），再对同一套冻结规则逐条测试 A–H 假说；短窗（1,328 根 M15，09-07…09-25）+ 长历史（40,546 根 M15，20 个月）双窗口。

| 假说 | 结果 | 证据 |
|---|---|---|
| **H 仪器/口径** | **PASS（绝对差 0.000000）** | 完整复现 C1.5 已发布指标：persistence 0.1447、churn 0.6473、duration median 1.0、mean 1.544、entropy 3.0114 |
| **F 无迟滞** | **SUPPORTED（主因）** | 对**同一套冻结标签**加 k=2 最小驻留：churn 0.6473→**0.1507**，中位时长 1→**5 bar**；k=3→0.0497/13 bar |
| **E 非市场特性** | **SUPPORTED（主因）** | 同收益合成随机序列跑同一 labeler：IID 0.6244 / block-bootstrap 0.6184 ≈ 观测 0.6473 |
| **B 尺度不变** | SUPPORTED | churn：M5 0.6126 / M15 0.6473 / H1 0.6707；长历史 M15 0.6292 / H1 0.6194；三档中位时长都是 1 bar |
| **A ontology 冲突** | 支持（次要） | `REVERSAL_ATTEMPT` 分支**不可达**（labeler 从不产出 `REGIME=REVERSAL`）；154 根 `TREND/EXPANSION` 与 `REJECTION` 冲突 |
| **D 测量噪声** | 支持（次要） | 0.01·ATR 噪声下标签一致率 0.9418（≈6% 翻转），churn 仍 ≈0.64 |
| **C bar 边界** | 否定 | 边界/内部 churn 比 1.105（可忽略） |
| **G UNKNOWN 泄漏** | 否定 | `NO_DEFINED_STATE` 占比 0.061–0.067 |

**根因结论**：冻结 `MARKET_BEHAVIOR` = **无记忆的逐 bar 分类器**；其 1-bar 时长由**规则定义（缺生命周期）**与**labeler 的随机性**共同决定，与市场是否"每 15 分钟换挡"无关。C1.5 的 `TARGET_UNCERTAIN` / `C2_BLOCKED` 是这个定义缺陷的**必然结果**。

---

## Phase 2 — STATE vs EVENT 生死测试

**协议（预注册）**：特征 = **纯 OHLC 派生指标**（labeler 输出严格排除，避免自证循环）；模型固定 multinomial logistic（C=1.0，训练集内标准化）；expanding walk-forward 5 折，PURGE=480 / EMBARGO=1；主指标 = 样本外 log-loss 增益 ΔLL(bits)；零假设 = block-shuffle 目标重跑全流程（NPERM=30）；效果地板 0.01 bits。

| 目标 | ΔLL (bits) | 最差折 | acc_model | acc_majority | 零假设 | 生存 |
|---|---|---|---|---|---|---|
| T1 冻结 STATE (t→t+8) | **0.1979** | +0.176 | 0.335 | 0.283 | null_max −0.0020, p=0.0 | ✅ |
| T2 **有状态 STATE** (k=2) | **0.2766** | +0.208 | **0.391** | 0.253 | null_max −0.0044, p=0.0 | ✅ |
| T3 下一根几何 | 0.0066 | — | 0.453 | 0.451 | — | ❌ <0.01 地板 |
| T4 突破事件 (H8) | 0.0884 | **−0.203** | 0.773 | **0.784** | — | ❌ 未超多数且折间不稳 |

**VERDICT = `STATE_SURVIVES`**。有状态版本把 ΔLL 提升 **+40%**（0.198→0.277），且每折为正。零假设分布全部为负，分离彻底。

> 即：**state 是活的，event/geometry 是死的。**

---

## Phase 3 — 有状态 STATE v2：严格 Blind + Ablation + 稳定性 + MTF 增量

**协议（预注册）**：`STATE_V2 = 冻结标签 + 最小驻留 k=2`（k 由 Phase 1 预注册，**未对目标调参**）；**单次 60/40 blind**（一次拟合、一次评估、不重训）；4 个等分块稳定性；H1 多周期上下文增量。

**分项消融（blind）**

| 特征阶梯 | ΔLL (bits) |
|---|---|
| A0 波动率 | 0.2765 |
| A1 +动量 | 0.2789 |
| **A2 +结构（最佳）** | **0.2913** |
| A3 +斜率 | 0.2408 |

**稳定性（A3，4 块）**：ΔLL 0.2211 / 0.2142 / 0.2835 / 0.2443 → **全为正**，min 0.2142，mean 0.2408。

**MTF 增量**：A3 0.2408 → 加 H1 上下文 0.2961，**Δ = +0.0553 bits → MTF_ADDS_VALUE = true**。

**验收**：`blind ΔLL ≥ 地板` ✅ · `超多数基线` ✅ · `4 块全正` ✅ → **`STATEFUL_STATE_V2_ACCEPTED`**。

---

## 产物（全部 append-only，账本带哈希）

```
registry/v1_r2_r1_phase1_preregistration.json    a1d97d4f…
registry/v1_r2_r1_phase2_preregistration.json    18c38bab…
registry/v1_r2_r1_phase3_preregistration.json    eb6da842…
registry/v1_r2_r1_stateful_state_v2_frozen.json  ← STATE v2 定义（RESEARCH_ONLY）
reports/V1_R2_R1_PHASE1_DIAGNOSIS_{SHORT,LONG}.json
reports/V1_R2_R1_PHASE2_STATE_VS_EVENT.json
reports/V1_R2_R1_PHASE3_STATEFUL_V2.json
ledger/V1_R2_R1_LEDGER.jsonl                     ← 4 条，全部可追溯
_r1_phase1_diagnosis.py / _r1_phase2_state_vs_event.py / _r1_phase3_stateful_v2.py
```

**仪器修复记录**：Phase 2 v1 因特征未标准化导致 lbfgs 不收敛（测量不可靠）→ 按"先查仪器"原则加训练集内标准化（PIT 安全）后重跑；**非结果调参**。

---

## 限制

- **RESEARCH_ONLY**：冻结 ontology / registry / 引擎 / 参数**一律未写**。
- 目标是 **labeler 自身输出**的可预测性，**不是收益**；本阶段**未涉及任何 PnL/未来收益/执行**。
- 单一品种（XAUUSD）、单一 20 个月窗口；H4 样本过小已排除。
- ΔLL 是**统计可测性**，不等于**可交易性**（成本 ~0.914bp 的门槛尚未在本口径下评估）。

## 未完成（goal 仍 active）

Phase 4 Transition 提前预警 · Phase 5 方向/Neutral/Abstention 拆解 · Phase 6 MTF 深化 · Phase 7 Counter-evidence 消融 · Phase 8 严格 Blind+Null 全量 · Phase 9 Forecast Engine + Strategy Mapping + 终局报告。

**下一步最该做的**：把 STATE v2 从"可预测"推进到"可执行"——即在冻结成本口径下，检验 ΔLL 优势能否转化为**扣费后**的方向性可用性；若不能，终局结论即为"state 可测但不可交易"。
