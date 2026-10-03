# GRAND_ARCHITECTURE_BRIEF — V2 多策略智能交易系统 · 第一阶段

> Durable working brief. The authoritative specification is Section B below (the user's task book).
> Section A is environment/recon fact. Follow the exact deliverable tree and stop condition.

---

# A. Ground rules & recon (READ-ONLY / SHADOW)

**Hard boundaries (non-negotiable):**
1. Current V2 `PAPER_LOCAL` must keep running — never stop it.
2. Do not modify current V2 production behaviour.
3. V1 fully isolated — no modification.
4. V3 fully isolated — no modification.
5. `order_send = 0`.
6. Never enter `BROKER_DEMO` / LIVE.
7. Do not modify current V2 production Alpha parameters/thresholds/cost/RiskGuard.
8. Do not modify historical ledger / state / evidence.
9. All new modules go into an independent Shadow/Research namespace.
10. No using future data to train/select/tune/evaluate past decisions.
11. Every strategy candidate must be PIT + OOS.
12. Never redefine metrics/cost/sample window/success criteria because results are poor.
13. Never pass off a heuristic/rule model/simulated agent as a real LLM.
14. No real LLM endpoint ⇒ must state `LLM_UNAVAILABLE`.
15. Stop at the end of this phase; do not auto-modify production, do not auto-advance.

**Git:** create branch `research/v2-grand-architecture` from current HEAD; commit only files under
`research/hermes/trader_v2/V2_GRAND_ARCHITECTURE/`. Never commit production-state churn.

**Recon facts already confirmed (verify, don't re-litigate):**
- Repo `C:\AIQuant`; branch at recon = `research/v2-historical-strategy-decay-lab`.
- Python: `C:\AIQuant\.venv\Scripts\python.exe` = 3.12.10.
- **GPU is real and usable:** `nvidia-smi` → NVIDIA RTX A2000 Laptop GPU, 4096 MiB, driver 591.55, CUDA 13.1.
  `python -c "import torch"` → torch **2.14.0+cu126**, `torch.cuda.is_available() == True`,
  device `NVIDIA RTX A2000 Laptop GPU`, capability `(8,6)`, total VRAM **4.29 GB**.
  ⇒ Section 八 must do genuine GPU compute with batch/chunk/streaming to fit 4 GB. "GPU exists" is NOT a pass.
- **Reusable GPU infra already present:** `research/gpu_accelerator/` (core, features, market, statistics,
  benchmark, tests, REPORT.md, AUDIT.md) — reuse it rather than rebuilding from scratch.
- **Prior read-only lab to wire in (Section 七):** `research/hermes/trader_v2/V2_HISTORICAL_STRATEGY_DECAY_LAB/`
  Branch `research/v2-historical-strategy-decay-lab` @ `2311601`, 32 files, SHA256SUMS 46/46.
  Its conclusion: **not enough evidence** — 2 real trade-bearing systems (V1_OLD magic 90002 Hermes candidate,
  109 closed; V1_NEW magic 90011 BASELINE control arm, 32 closed); V2 magic 90003 & V3 = **0 executed trades**;
  fresh-start/decay/reset/48h all INCONCLUSIVE or NOT_ESTABLISHED. Do not re-run it; consume its artifacts.
- V2 run is RUNNING (`run_id V2-PAPER-20261001-205202-8b9e`, `run_status RUNNING`, `blocked=null`,
  `replay_status MATCH`, `PAPER_LOCAL`). Do not disturb.
- Historical replay data for Section 二十一 lives in: `V2_HISTORICAL_STRATEGY_DECAY_LAB/`
  (`AGE_ALIGNED_DATASET.jsonl`, `SYSTEM_EPISODES.jsonl`, `HISTORICAL_SYSTEM_REGISTRY.json`,
  `STRATEGY_LIFECYCLE_DATABASE.json`) and `research/hermes/audit/hermes_alpha_drift_pit/`.

**Language:** report prose in Chinese (spec is Chinese); keep IDs/field names/filenames English
as specified. Dashboard copy defaults to Chinese.

**Expected honest shape (do not force a positive):** given V2/V3 have 0 executed trades and only V1 has
executable history (1 independent system), most statistical claims (Sections 五/六/十七/二十二/二十三)
will legitimately land `INCONCLUSIVE` / `NOT_SUPPORTED` / `NOT_EVALUABLE`. Report that truthfully.

---

# B. Authoritative specification

## 总目标
把当前 V2 从 `单一 Reference Decision + Opportunity Discovery` 升级为：**多策略、自适应、可进化、GPU 加速、可审计的 XAUUSD 智能交易研究系统。**
本阶段不是为了立即增加交易，也不是为了寻找一个"最高收益策略"。核心目标是建立一套可以持续
`发现机制 → 生成策略 → 验证 → 竞争 → 淘汰 → Evolution → Shadow` 的完整系统。

## 一、硬边界
（见 Section A 的 15 条，逐条遵守。）

## 二、第一目标：建立 V2 Strategy Factory
创建独立模块 `strategy_factory/`，负责：市场现象 → 研究假设 → 候选机制 → 策略生成 → 策略验证 → Strategy Registry。
至少支持：趋势/震荡/动量/反转/突破/波动扩张/波动收缩/多周期结构/事件新闻/宏观共振/混合机制。
不得简单复制已有 V1/V2 规则。每个策略必须有：`strategy_id`, `hypothesis_id`, mechanism, feature_set,
parameters, expected_horizon, applicable_regime, entry logic, exit logic, invalidation, cost model,
PIT requirements, creation commit, dataset hash。

## 三、建立 Strategy Registry
`strategy_registry.jsonl`；生命周期：`RESEARCH → SHADOW → CANDIDATE → VALIDATED → ACTIVE → DEGRADED → RETIRED`。
不得因单次盈利直接 ACTIVE。必须记录 first_seen / validation history / OOS history / regime history /
drawdown / performance decay / failure reason / retirement reason。

## 四、建立 Multi-Strategy Brain
`strategy_brain/`。输入：市场状态 + Opportunity + 各策略预测/置信度/近期表现/长期稳定性 + 成本 + regime + 风险状态。
输出：strategy_candidates, direction, confidence, evidence, counter_evidence, conflict_state, final_decision。
必须支持：策略一致、策略冲突（例：Trend=LONG, Momentum=LONG, Reversal=SHORT, Breakout=NONE）、策略缺席、
数据不足→`WAIT/DATA_GAP`。不得强迫交易。

## 五、建立 Strategy Competition
比较 short-term precision / expectancy / cost-adjusted return / MFE / MAE / calibration / stability /
effective_n / OOS performance / regime fit。**禁止简单按历史收益排序选冠军。**
需综合 `Performance + Stability + Regime Fit + Sample Size + Cost Robustness`。输出 strategy_state。

## 六、建立 Evolution Engine
`evolution/`。不是"每两天自动改策略"。流程：监测 → 发现性能变化 → 提出升级假设 → 生成 candidate →
Historical validation → OOS → Shadow → 决定。状态：`NO_CHANGE / SHADOW / CANDIDATE_RELEASE / RETIRED`。
**不得固定 48h。** 触发因素：edge degradation / regime transition / opportunity degradation /
confidence drift / calibration drift / cost sensitivity / MAE expansion / MFE contraction / prediction drift。

## 七、建立 Strategy Lifecycle / Decay Monitor
把刚完成的 Historical Strategy Decay Lab 接入研究框架。持续记录 `system_age` 及 strategy_age /
regime_age / performance_age / confidence_age。监测 Birth/Early/Stable/Degradation/Exhaustion/Recovery/Retirement。
**不得预设衰竭时间**，必须由数据识别。

## 八、建立 GPU Research Engine
正式使用 **RTX A2000 4GB**。创建 `gpu_research/`。GPU 优先承担：特征矩阵、大规模 rolling window、
候选策略批量评估、bootstrap、permutation、多窗口 walk-forward、模型训练、策略组合评价、regime conditional analysis。
必须记录：GPU model, CUDA version, framework version, peak VRAM, utilization, CPU runtime, GPU runtime, speedup。
要求：**确实使用 GPU 进行大规模研究计算**。4GB 不是借口，用 batch/chunk/streaming 控显存。

## 九、建立 GPU Strategy Search
允许大规模搜索 feature+window+regime+direction rule+confirmation+risk structure。
禁止"搜百万策略只挑收益最高一条"。必须 Discovery → Validation → Untouched OOS，记录完整搜索空间与
searched hypotheses / valid candidates / rejected candidates / rejection reason / multiple testing correction。

## 十、建立"简单策略优先"基准
所有复杂模型至少比较：V1 Baseline (`M15 close vs MA20`)、Simple Momentum、Simple Mean Reversion、
Simple Breakout、Current V2 Reference、Random/Negative Control。没稳定超过简单基准 ⇒ 不得视为升级。

## 十一、建立 Regime-Aware Strategy Matrix
`strategy × regime` 矩阵（TREND/RANGE/BREAKOUT/EVENT/TRANSITION × Trend/Momentum/Reversal/Breakout/
Volatility/Macro/Event/Hybrid）。输出 performance / OOS / confidence / effective_n / degradation。
目标：找到每个策略"擅长什么"。

## 十二、建立 Opportunity Hub
重构 Discovery 概念，**原 Discovery 保留为 Reference**。允许多个独立来源产生机会
（Technical/Momentum/Reversal/Breakout/Volatility/Macro/Event/Structure），
流程 `Generate → Rank → Filter → Strategy Brain`。不能出现某个来源长期垄断机会；
**禁止通过降低门槛人为制造交易数量。**

## 十三、建立 Evidence Fusion
每个策略不能只输出方向，必须输出 direction/confidence/evidence/counter_evidence/regime/horizon/
expected_move/risk。多策略证据融合；若 evidence=strong 且 counter_evidence=strong，允许结果 `WAIT`。

## 十四、建立 Strategy Memory
`strategy_memory/`。记录每次预测、当时市场状态、结果、MFE、MAE、failure type、regime、strategy age、
confidence calibration。目的：建立策略自己的生命周期档案。**禁止 outcome leakage。**

## 十五、建立自动 Failure Analysis
每次失败分类：DIRECTION_ERROR / TIMING_ERROR / REGIME_ERROR / RISK_ERROR / COST_ERROR / DATA_ERROR /
EXECUTION_ERROR / OPPORTUNITY_ERROR / NO_IDENTIFIABLE_ERROR，并统计 `strategy × failure_type`。

## 十六、建立 Strategy Retirement
连续退化时可 `DEGRADED → RETIRED`，保留全部历史；市况变化可 `RESEARCH → SHADOW` 重新验证。禁止删除旧策略。

## 十七、建立组合策略层
至少研究 Single Strategy / Equal Weight / Confidence Weight / Regime Weight / Diversity Weight，
严格 OOS，不能只按历史收益分配权重。特别检查多策略是否都在赌同一风险因子：
计算 return correlation / signal correlation / drawdown correlation / overlap / regime overlap。

## 十八、建立 V2 Intelligence Interface
`intelligence/interface.py`，为真实 LLM 预留标准接口（market interpretation / evidence synthesis /
counter-evidence / strategy conflict interpretation / hypothesis generation）。**LLM 不能拥有最终 Risk/Execution
authority**，硬风控永远由非 LLM 层控制。无 endpoint ⇒ `LLM_UNAVAILABLE`，不得 fallback 冒充真实 Agent。

## 十九、建立统一研究协议
所有策略研究必须遵循：PIT → Hypothesis Freeze → Discovery → Validation → Untouched OOS → Bootstrap →
Permutation → FDR → Stability → Shadow。并保存 input hash / code commit / config hash / seed / data source /
feature hash / model hash。

## 二十、建立总控制面板
不接生产，只做 Research Dashboard。至少显示：策略总数及各生命周期计数、Market Regime、策略一致/冲突、
近期性能、近期退化、Opportunity Concentration、GPU 状态、Evolution 状态。文案默认中文。

## 二十一、必须进行历史回放
至少用 V1_OLD / V1_NEW / 当前 V2 历史可验证数据，重放 Strategy Factory / Strategy Brain / Evolution Engine。
**不允许把历史策略结果当未来训练标签。** 历史只用于 architecture validation / replay validation / mechanism research。

## 二十二、必须新增几个大实验
- **A** Multi-Strategy vs Single Strategy（Single V1 / Single Reference / Multi-Strategy）
- **B** Strategy Diversity（是否真的减少 drawdown / regime failure / false signal）
- **C** Strategy Brain（固定规则组合 vs Strategy Brain）
- **D** Evolution（NO_EVOLUTION vs Evidence-triggered Evolution）
- **E** GPU Search（Manual/small vs GPU large-scale；重点不是收益冠军，而是找到之前无法枚举的稳定机制）
- **F** V1 Capture Replication（V1 历史捕捉到的机会，多策略系统能否用 PIT 重新发现）

## 二十三、最终验收（必须直接回答 12 问）
1 是否已建立真正的 Strategy Factory？ 2 是否可同时运行多个互相独立的策略？ 3 是否可自动判断一致与冲突？
4 是否存在策略生命周期管理？ 5 是否能自动发现退化而非固定时间重启？ 6 GPU 是否真正承担大规模研究计算？
7 是否发现新的稳定短周期机制？ 8 新机制是否超过 V1 simple baseline？ 9 是否经过严格 OOS/Bootstrap/Permutation/FDR？
10 是否存在真正值得进入 Shadow 的候选？ 11 Evolution 是否有证据支持？ 12 当前 V2 production 是否保持 0 修改？

## 二十四、最终交付目录 `C:\AIQuant\research\hermes\trader_v2\V2_GRAND_ARCHITECTURE\`
```
ARCHITECTURE.md
strategy_factory/  strategy_registry/  strategy_brain/  strategy_memory/  evolution/
gpu_research/  opportunity_hub/  intelligence/
STRATEGY_LIFECYCLE.md  STRATEGY_COMPETITION.md  REGIME_STRATEGY_MATRIX.md  FAILURE_ANALYSIS.md
MULTI_STRATEGY_REPORT.md  STRATEGY_FACTORY_REPORT.md  STRATEGY_BRAIN_REPORT.md
EVOLUTION_ENGINE_REPORT.md  GPU_RESEARCH_REPORT.md  ALPHA_DISCOVERY_REPORT.md
V1_CAPTURE_REPLICATION.md  OOS_REPORT.md  STATISTICAL_EVIDENCE.md  STABILITY_REPORT.md  REPLAY_REPORT.md
CANDIDATE_REGISTRY.jsonl  STRATEGY_REGISTRY.jsonl  EXPERIMENT_REGISTRY.jsonl
GPU_BENCHMARK.json  DATA_MANIFEST.json  SHA256SUMS.txt  FINAL_REPORT.md
```

## 二十五、Git / 完整性
独立 branch、独立 commits、所有新增代码进入 Git、每个实验有 manifest 与 hash、生产目录零修改、最终 scope 检查。

## 二十六、最终状态
只允许 `RESEARCH_COMPLETE` 或 `RESEARCH_COMPLETE_WITH_CANDIDATES`（存在候选则 `CANDIDATE_ONLY`）。
绝不自动进入 production。最终必须明确：
```
Production changes = 0
order_send = 0
V1 touched = 0
V3 touched = 0
V2 production behavior changed = 0
GPU research = PASS / FAIL
Validated Alpha candidates = N
Evolution evidence = SUPPORTED / INCONCLUSIVE / NOT_SUPPORTED
```
最后回答核心问题：**V2 是否已经从"一个策略"真正开始变成"一个能够发现、验证、竞争、淘汰和进化策略的系统"。**
任务结束后停止。
