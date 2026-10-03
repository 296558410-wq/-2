# ARCHITECTURE — V2 多策略智能交易系统（第一阶段）

> 只读 / Shadow 研究程序。生产 V2 未改动；`order_send = 0`。code_commit `23116019e2a4c47a7e4eec4150d61ac3681b788f`。

## 总览
把当前 V2 从「单一 Reference Decision + Opportunity Discovery」升级为
**多策略、自适应、可进化、GPU 加速、可审计**的 XAUUSD 研究系统。本阶段只做研究，不接生产。

## 模块树
```
V2_GRAND_ARCHITECTURE/
├── ARCHITECTURE.md
├── common/              共享原语：hashing / data(PIT) / pit / cost / metrics / protocol / eval
├── strategy_factory/    机制库(11 族) + 工厂(生成候选与元数据)
├── strategy_registry/   生命周期状态机 + jsonl 注册表
├── strategy_brain/      多策略聚合：一致/冲突/缺席/数据不足 → WAIT
├── strategy_memory/     逐次预测与结果档案(无 outcome leakage)
├── evolution/           证据触发式演化(无固定 48h)
├── gpu_research/        torch/CUDA 真算：特征矩阵/rolling/batch 评估/bootstrap/permutation/walk-forward
├── opportunity_hub/     多来源机会生成→排序→过滤（原 Discovery 保留为 Reference）
├── intelligence/        真实 LLM 接口预留（LLM_UNAVAILABLE，无 authority）
└── pipeline/            编排与报告生成
```

## 关键约束
- PIT：特征只用 `bar<=t`；标签取自 `t+1..t+h`；OOS 在最终揭示前不参与选择。
- 成本：中位实测 round-trip spread = **0.1500** 价格单位（来自本地 FXTM tick 归档）。
- 数据：本地 XAUUSD tick 归档（4096945 ticks，26220 根 1m bar，
  2026-09-07..2026-10-02），dataset_hash `b726a7919b56a90f…`。
- 分裂：discovery `('2026-09-07', '2026-09-16')` / validation `('2026-09-17', '2026-09-23')` /
  untouched OOS `('2026-09-24', '2026-10-01')`。
- GPU：NVIDIA RTX A2000 Laptop GPU，torch 2.14.0+cu126，CUDA 12.6，
  peak VRAM 1223.2 MB，speedup 6.68×。

## 数据流
`tick 归档 → 1m/15m bars → PIT 特征矩阵 + regime → Strategy Factory 生成候选 →
Strategy Registry 登记 → Discovery 评估 →（GPU 大规模搜索）→ Validation →
Untouched OOS → Bootstrap/Permutation/FDR → Competition 打分 → Brain 聚合 →
Memory 建档 → Evolution 监测 → Portfolio 组合 → 报告`。
