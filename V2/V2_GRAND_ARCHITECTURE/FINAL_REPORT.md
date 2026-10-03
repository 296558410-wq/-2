# FINAL_REPORT

code_commit `23116019e2a4c47a7e4eec4150d61ac3681b788f` · dataset_hash `b726a7919b56a90f…` · seed `20261003`
branch `research/v2-grand-architecture`

## 交付目录

模块：`strategy_factory/`, `strategy_registry/`, `strategy_brain/`, `strategy_memory/`, `evolution/`, `gpu_research/`, `opportunity_hub/`, `intelligence/`, `pipeline/`

报告：ARCHITECTURE / STRATEGY_LIFECYCLE / STRATEGY_COMPETITION / REGIME_STRATEGY_MATRIX / FAILURE_ANALYSIS / MULTI_STRATEGY_REPORT / STRATEGY_FACTORY_REPORT / STRATEGY_BRAIN_REPORT / EVOLUTION_ENGINE_REPORT / GPU_RESEARCH_REPORT / ALPHA_DISCOVERY_REPORT / V1_CAPTURE_REPLICATION / OOS_REPORT / STATISTICAL_EVIDENCE / STABILITY_REPORT / REPLAY_REPORT / FINAL_REPORT

登记表：STRATEGY_REGISTRY.jsonl / CANDIDATE_REGISTRY.jsonl / EXPERIMENT_REGISTRY.jsonl / GPU_BENCHMARK.json / DATA_MANIFEST.json / SHA256SUMS.txt

## 12 条验收回答

1. 是。`strategy_factory/` 生成 17 个候选，跨 11 个机制族（含 trend/range/momentum/reversal/breakout/vol-expansion/vol-contraction/mtf/event/macro/hybrid），每个含完整元数据（creation commit + dataset hash + PIT 要求 + 成本模型）。
2. 是。17 个策略各自独立计算 PIT 信号并可在同一 bar 上并行给出立场；Brain 每 bar 聚合（本阶段 discovery/validation/OOS 均实跑）。
3. 是。Brain 支持 AGREEMENT / CONFLICT / ABSENT / DATA_GAP，并在冲突或不足时输出 WAIT；冲突计数见 STRATEGY_BRAIN_REPORT。
4. 是。`strategy_registry/` 实现 7 态生命周期与转移守卫；本阶段状态计数 `{"RESEARCH": 17}`。单次盈利不晋升 ACTIVE。
5. 是（机制层面）。`evolution/` 以 9 类证据触发（无固定 48h）判定 NO_CHANGE/SHADOW/CANDIDATE_RELEASE/RETIRED；触发策略数 = 12（样本不足以确证）。
6. 是。GPU(NVIDIA RTX A2000 Laptop GPU) 实测承担：特征矩阵 [26220, 16]、13296 组合批量评估、bootstrap(60000)、permutation、walk-forward；GPU 2.1793s vs CPU 14.5518s，speedup 6.68×，peak VRAM 1223.2MB。GPU research = PASS。
7. 是（有限）。在 disc+val+oos 同时为正的机制数 = 5；但样本跨度小、FDR 通过 0/17，统计上多为 INCONCLUSIVE。
8. 否（未确证）。多数候选未稳定超过简单基准 V1_M15_vs_MA20 / RANDOM_CONTROL；见 OOS_REPORT 与 ALPHA_DISCOVERY_REPORT。
9. 是（协议层面）。PIT→freeze→discovery→validation→untouched OOS→bootstrap→permutation→FDR→stability→shadow 全部实现并落盘；但 FDR 通过仅 0/17，统计效力不足。
10. 暂无。进入 SHADOW/CANDIDATE 的候选 = 0（CANDIDATE_ONLY，不自动进生产）。
11. Evolution 证据 = INCONCLUSIVE。触发因素可计算，但真实 OOS 证据不足以支持 CANDIDATE_RELEASE（0 次 release）。
12. 是。V2 production 0 修改；run V2-PAPER-20261001-205202-8b9e 保持 RUNNING；order_send=0；V1/V3 0 触碰。

## 大实验 A–F 结论

- **A** `NOT_SUPPORTED`
- **B** `INCONCLUSIVE`
- **C** `INCONCLUSIVE`
- **D** `INCONCLUSIVE`
- **E** `PASS`
- **F** `NOT_SUPPORTED`

## 最终状态块

```
Production changes = 0
order_send = 0
V1 touched = 0
V3 touched = 0
V2 production behavior changed = 0
GPU research = PASS
Validated Alpha candidates = 0
Evolution evidence = INCONCLUSIVE
```

## 核心问题

是——系统已从「一个策略」变成一个可发现、可验证、可竞争、可淘汰、可进化的框架：工厂生成 17 个跨 11 族的独立候选，Registry 管理生命周期，Brain 能在一致/冲突/缺席/数据不足间决策，GPU 真机承担大规模研究计算，Evolution 以证据触发而非固定时钟。但诚实地说：受限于仅 ~18 个交易日的可验证样本与FDR 通过 0/17，目前没有任何候选被统计确证为稳定 alpha，也未发现超越简单基准的新机制；因此本阶段是「架构成立、证据不足」——系统已具备‘能进化’的能力，但尚无用得上的证据。