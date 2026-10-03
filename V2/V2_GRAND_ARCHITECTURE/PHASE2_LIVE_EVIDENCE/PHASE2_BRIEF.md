# PHASE2_BRIEF — V2 Grand Architecture · Phase 2 (Live Shadow Evidence)

> Durable brief. Authoritative spec = Section B. Environment/recon = Section A.
> This phase is **continuous**. It does NOT aim to "find Alpha"; it builds the live shadow
> evidence pipeline and lets real cycles accrue. End state = `RESEARCH_CONTINUOUS`
> (or `RESEARCH_MILESTONE_REACHED` if a stage gate is met). Never auto-upgrade production.

---

# A. Ground rules & recon (READ-ONLY / SHADOW)

**Hard boundaries (the user's 15 rules):**
1. V2 `PAPER_LOCAL` keeps running — never stop it.
2. V2 production decision/execution chain unchanged.
3. V1 fully untouched. 4. V3 fully untouched. 5. `order_send = 0`.
6. Never enter `BROKER_DEMO` / LIVE.
7. Do not modify V2 production Alpha/thresholds/RiskGuard/cost assumptions.
8. Do not modify historical ledger/state/evidence.
9. Phase 1's 17 strategies may only run in Shadow.
10. Shadow must NOT call `order_check` / `order_send`.
11. Do not lower thresholds because of a lack of trades.
12. Do not auto-change a strategy because of losses.
13. Do not update strategies on a fixed 48h; 48h is only an observation window.
14. No real LLM endpoint ⇒ keep `LLM_UNAVAILABLE`.
15. Do not auto-upgrade production after this phase.

**Also:** research-component failure must be `FAIL-CLOSED` and must never affect production.
Shadow output goes ONLY to `V2_GRAND_ARCHITECTURE/shadow/` (and the Phase-2 directory below); never write back to production.

**Git:** create branch `research/v2-grand-architecture-phase2` from current HEAD
(`13769ef` on `research/v2-grand-architecture`). Commit ONLY under
`research/hermes/trader_v2/V2_GRAND_ARCHITECTURE/PHASE2_LIVE_EVIDENCE/` (+ a minimal shadow
data dir if needed). Never commit production-state churn.

**DO NOT CREATE ANY SCHEDULER.** Do not create/modify Windows scheduled tasks, launchers,
cron, or automations. Build the per-cycle runner so it is invocable and idempotent, and leave
scheduling to the parent. (Parent will wire the scheduler after the user chooses a mechanism.)

**Recon facts already confirmed (verify, don't re-litigate):**
- Existing Windows tasks: `\OpenClaw\{hermes-tick-collect, hermes-v2-cycle, hermes-v2-observer}`,
  plus `v1up-panel`, `v3-calibration-pilot`. `hermes-v2-cycle` runs every ~15 min via
  `C:\Users\surface\.openclaw\launchers\hermes-v2-cycle-hidden.vbs` (zero-LLM, direct). Do not touch them.
- **Market is closed now (weekend).** V2 health: `market_open=false`, `cycle_result=MARKET_CLOSED_SKIP`,
  `current_cycle=2026-10-03T05:00:00Z`. ⇒ Real new cycles/decisions/outcomes this session will be ~0;
  report that honestly rather than inventing activity. The runner must handle `MARKET_CLOSED`/`DATA_GAP`.
- Local XAUUSD tick archive: `C:\AIQuant\data\live_fxtm\ticks_YYYYMMDD.parquet` (from 2026-09-07 …).
  15/30/60/240m future returns, MFE/MAE, first-touch are derivable from it for seeding + outcome backfill.
- Phase 1 modules (callable entry points) live in `V2_GRAND_ARCHITECTURE/`:
  `strategy_factory/run_factory.py`, `strategy_registry/run_registry.py`, `strategy_brain/run_brain.py`,
  `strategy_memory/run_memory.py`, `evolution/run_evolution.py`, `gpu_research/run_gpu.py`,
  `opportunity_hub/run_hub.py`, `intelligence/run_intelligence.py`, `pipeline/run_program.py`.
  Reuse them; do not rewrite Phase 1.
- Phase 1 findings to respect: 17 candidates / 11 families; FDR pass 0/17; `CANDIDATE_REGISTRY` empty;
  OOS numbers dominated by noise (random control out-earned candidates); V2/V3 have 0 executed trades;
  only V1 has executable history. Do NOT re-run the full 13,296-combo search unless new data/hypothesis
  justifies it (spec §12) — incremental update only.
- **Known Phase 1 defect to avoid:** the SHA256 manifest was written BEFORE the final runner rewrite.
  In Phase 2 the SHA256SUMS manifest MUST be generated as the LAST step, after every file is frozen.
- `python` = `C:\AIQuant\.venv\Scripts\python.exe` (3.12.10). GPU = RTX A2000 4GB, torch 2.14.0+cu126.

**Language:** dashboard/report prose in Chinese; IDs/field names/filenames English.

---

# B. Authoritative specification (Phase 2)

## 总目标
在 Phase 1 大架构基础上进入：**真实连续市场数据积累 → 多策略 Shadow 竞争 → Outcome 回填 →
退化监测 → 候选验证**。核心目标：让 V2 多策略系统形成第一批真正具有时间连续性、PIT 完整、
可 OOS 验证的策略生命周期数据。不扩大架构，不强行找 Alpha。

## 二、Live Shadow Evidence Stream
所有真实 V2 周期用与 production 相同的 PIT 输入，额外送入
`Strategy Factory → Strategy Registry → Strategy Brain → Strategy Competition → Evolution Monitor`，
结果只进 `V2_GRAND_ARCHITECTURE/shadow/`，不得反写 production。每周期保存：
cycle_id, decision_ts, data_asof, strategy_id, strategy_version, regime, signal, confidence, evidence,
counter_evidence, strategy_state, final_shadow_decision, production_decision, input_hash, output_hash。

## 三、连续 Outcome 回填
每个 Shadow decision 自动产生 15m / 30m / 60m / 240m，记录 future return, MFE, MAE,
TP/SL first-touch（适用时）, data completeness, DATA_GAP。严格 `decision_ts < future_data_ts`，禁止 future leakage。

## 四、Production vs Shadow 对照
每周期记录 Production Reference VS Strategy A…N VS Strategy Brain，回答：谁发现机会/谁没发现/
谁与 Reference 一致/谁互相冲突/谁产生更多假机会/谁在特定 regime 更好。不能只看收益。

## 五、策略实时生命周期
维护 RESEARCH/SHADOW/CANDIDATE/VALIDATED/ACTIVE/DEGRADED/RETIRED（生产不允许 ACTIVE）。
Shadow 策略持续记录 age, sample count, effective_n, rolling expectancy, confidence, calibration,
MFE, MAE, failure type, regime distribution, drawdown。

## 六、衰退监测（不自动重置）
监测 expectancy/precision/confidence/calibration drift, MAE expansion, MFE contraction,
opportunity quality decay, regime mismatch, signal concentration。输出
`NORMAL / DEGRADING / SUSPECTED_EXHAUSTION / DATA_INSUFFICIENT`。禁止因 `SUSPECTED_EXHAUSTION` 自动重启/改策略。

## 七、策略竞争机制
每观察窗口比较：短周期 15m/30m；中周期 60m/240m；风险 MFE/MAE/drawdown；稳定性 rolling/regime/time block；
统计 effective_n/bootstrap CI/permutation/FDR → `STRATEGY_SCORECARD`。Scorecard 仅用于研究排序，不得直接决定生产。

## 八、Regime × Strategy 实证矩阵
实时积累 (TREND/RANGE/BREAKOUT/TRANSITION/EVENT) × (Trend/Momentum/Reversal/Breakout/Volatility/Structure/Macro/Event/Hybrid)，
记录 sample/precision/expectancy/MFE/MAE/stability。目标：找到策略适用区域，而非万能策略。

## 九、重点观察 V1 Baseline
`V1 M15 close vs MA20` 作固定控制臂；每 Shadow 周期比较 V1 baseline VS V2 reference VS V2 multi-strategy；
重点记录 V1 能发现的机会新体系能否发现。不得把 V1 历史结果当训练标签。

## 十、Candidate Queue
进入 `CANDIDATE_QUEUE` 至少需：PIT PASS, OOS PASS, effective_n 足够, 成本后有效, Bootstrap CI,
Permutation, FDR, 稳定性, 多时间窗口, 非单一 regime 依赖（或明确标注 regime 限定性）。不满足 `STAY_SHADOW`。
禁止因表现好看直接升级。

## 十一、GPU 使用策略
继续用 RTX A2000 4GB，但不做无意义连续暴力搜索。GPU 用于新增样本批量评估、rolling feature、
bootstrap、permutation、walk-forward、candidate validation、strategy correlation、regime matrix。
累计到预设研究批次再做 GPU 批处理。记录 GPU runtime/CPU baseline/speedup/VRAM/batch size。

## 十二、不要重复 Phase 1
禁止再次完整搜索 13,296+ 相同历史组合，除非新增真实数据/明确 hypothesis/新 mechanism family/
Phase 1 结果指出新问题；否则只做 incremental update。

## 十三、48h Review（不是 48h Reset）
每 48h 生成 `V2_48H_REVIEW`：①最近48h市场状态 ②哪些策略产生信号 ③哪些完全沉默 ④哪些退化
⑤哪些发现 Reference 漏掉的机会 ⑥哪些机会是假的 ⑦是否出现新机制证据 ⑧是否有策略达 Candidate Queue
⑨是否 NO_CHANGE ⑩是否值得发起新 Shadow Experiment。默认 `NO_CHANGE`，除非有证据。

## 十四、Evolution Proposal（不执行）
发现结构性退化：观察→hypothesis→Evolution Proposal→离线验证→Shadow。禁止"发现问题→自动改生产"。

## 十五、重点寻找三种东西
A 真正的新 Alpha（与 V1 baseline/Reference/Random 都不同）；B 条件 Alpha（只在某 regime 有效）；
C Alpha 互补性（两个弱策略组合产生稳定增量而非叠加风险）。特别计算 signal/return/drawdown correlation 与 opportunity overlap。

## 十六、假 Alpha 防火墙
任何漂亮结果自动检查 multiple testing/sample size/regime concentration/time concentration/cost sensitivity/
parameter sensitivity/placebo/shuffled control/unseen OOS。只单窗口成立→`FRAGILE`；只单 regime→`REGIME_CONDITIONAL`；
FDR 不通过→`NOT_VALIDATED`。

## 十七、长期数据资产
每周期数据形成不可变资产：market context→strategy signals→brain decision→outcome→lifecycle→evidence。
历史结果之后不得被覆盖。最终形成 `V2_STRATEGY_LIFETIME_DATASET`。

## 十八、运行稳定性
每日检查 scheduler/data router/agent1/agent2/context/discovery/strategy factory/strategy brain/outcome engine/
ledger/replay/shadow modules。任何异常 `FAIL-CLOSED`；研究组件异常不能影响 production。

## 十九、Git / 完整性
独立 commits、Git 可追溯、SHA256、experiment manifest。最终检查：生产代码未修改 / 实验代码全部可追溯 /
manifest 最新 / replay PASS。**最终文件全部冻结后，最后一步再生成 SHA256 manifest。**

## 二十、结束条件
不以"发现 Alpha"为结束。满足 A(出现足够证据的 VALIDATED_CANDIDATE) / B(发现明确新机制需独立研究) /
C(样本仍不足但系统连续稳定运行) / D(发现架构缺陷需修复) 任一即可阶段性结束。无论哪种都不自动改 production。

## 二十一、交付目录
`C:\AIQuant\research\hermes\trader_v2\V2_GRAND_ARCHITECTURE\PHASE2_LIVE_EVIDENCE\`
至少：`LIVE_SHADOW_ARCHITECTURE.md`, `LIVE_EVIDENCE_STREAM.jsonl`, `STRATEGY_SCORECARD.jsonl`,
`STRATEGY_LIFECYCLE.jsonl`, `REGIME_STRATEGY_MATRIX.json`, `V1_REFERENCE_COMPARISON.jsonl`,
`PRODUCTION_VS_SHADOW.md`, `48H_REVIEW.jsonl`, `DEGRADATION_MONITOR.md`, `EVOLUTION_PROPOSALS.jsonl`,
`CANDIDATE_QUEUE.jsonl`, `FALSE_ALPHA_REPORT.md`, `OOS_PROGRESS.md`, `STATISTICAL_PROGRESS.md`,
`GPU_USAGE_REPORT.md`, `DATA_MANIFEST.json`, `REPLAY_REPORT.md`, `SHA256SUMS.txt`, `FINAL_REPORT.md`.

## 二十二、最终必须回答（块）
真实新增周期 / 真实新增 decision / 真实新增 outcomes；Shadow strategies / Candidate strategies /
Validated candidates；V1 baseline 是否仍能发现不同于 V2 的机会（YES/NO/INCONCLUSIVE）；
是否发现新机制（YES/NO）；是否发现条件 Alpha（YES/NO）；是否发现策略互补（YES/NO）；
是否发现稳定退化前兆（YES/NO/INCONCLUSIVE）；Evolution evidence（SUPPORTED/INCONCLUSIVE/NOT_SUPPORTED）；
Production changes 0；order_send 0；V1 touched 0；V3 touched 0。
最终状态 `RESEARCH_CONTINUOUS`（或 `RESEARCH_MILESTONE_REACHED`）。绝不自动进生产。
