# LIVE_SHADOW_ARCHITECTURE

> Phase 2（Live Shadow Evidence）架构与运行说明。分支 `research/v2-grand-architecture-phase2`。
> 一切 SHADOW-ONLY，**不反写 production**，`order_send = 0`。

## 数据流

```
production PIT inputs (local FXTM tick archive, read-only)
        │
        ├── 15m bars + PIT features + regime           (common/data.py, 复用 Phase 1)
        ▼
 Strategy Factory ─▶ Strategy Registry ─▶ Strategy Brain ─▶ Competition ─▶ Evolution
        │                   │                    │               │             │
        └───────────── LIVE_EVIDENCE_STREAM.jsonl (per cycle × strategy) ─────┘
                                   │
                     Outcome backfill 15/30/60/240m  (raw ticks, strict PIT)
                                   ▼
                          OUTCOMES.jsonl
                                   │
      scorecard / lifecycle / regime matrix / v1 arm / degradation /
      48h review / evolution proposals / candidate queue / false-alpha /
      lifetime dataset / OOS & statistical progress
```

## 每周期记录字段 (spec §2)

`cycle_id, decision_ts, data_asof, strategy_id, strategy_version, mechanism, regime,
signal, confidence, regime_fit, recent_stability, evidence, counter_evidence,
strategy_state, final_shadow_decision, production_decision, input_hash, output_hash`
（附：`shadow_direction/shadow_confidence/conflict_state/n_votes/data_quality/mode/cycle_kind/atr14/close_ref`）。

## PIT 纪律

- 15m bar 以 pandas resample 左标签 `t` 聚合 `[t, t+15m)`，**只有到 `t+15m` 才算完成**；
  因此 shadow `decision_ts = 标签 + 15m`，其自身 close = 该完成 bar 的最后成交价（严格早于 `decision_ts`）。
- Outcome 只用 `(decision_ts, decision_ts+H]` 内的原始 tick，保证 `decision_ts < future_data_ts`。
- `input_hash` = 最近 200 根 ≤t 的 PIT bar 窗口的 sha256；`output_hash` = 该周期 shadow 输出的 sha256。
- 置信度只用「结果已发生」的历史交易校准（trailing window），无前视。

## 运行 / 幂等

```bash
python runner/shadow_stack.py --mode seed        # 回放可验证历史（SEED/REPLAY）
python runner/shadow_stack.py --mode live        # 当前时点单周期（闭市则记 MARKET_CLOSED）
python runner/backfill.py                        # 增量 outcome 回填（可反复运行）
python runner/gpu_batch.py                       # 增量 GPU 统计
python runner/analytics.py                       # 生成全部分析交付物
python runner/stability_check.py                 # 每日稳定性自检（FAIL-CLOSED）
python runner/build.py                           # 端到端（不含 manifest）
python runner/make_manifest.py                   # SHA256 —— 必须最后一步
```

幂等键：stream = `(cycle_id, strategy_id)`；outcome = `(cycle_id, strategy_id, horizon_min)`。
重复运行只追加缺失项，**从不改写历史**（`LIVE_EVIDENCE_STREAM.jsonl` / `OUTCOMES.jsonl` 只增）。

## 边界（15 条 hard boundaries）

V2 PAPER_LOCAL 持续 RUNNING；production 决策/执行链 0 改动；V1/V3 0 触碰；`order_send=0`；
不进入 `BROKER_DEMO/LIVE`；不改 Alpha/阈值/RiskGuard/成本；不改历史 ledger/state/evidence；
策略仅 SHADOW；不因缺乏交易而降低阈值；不因亏损自动改策略；不做固定 48h 更新（48h 仅观察窗）；
无真实 LLM ⇒ `LLM_UNAVAILABLE`；不自动升级 production；研究失败 `FAIL-CLOSED` 且不影响 production；
**不创建任何 scheduler**（本 runner 可调用、幂等，调度交由 parent）。

## 目录

交付物全部位于 `PHASE2_LIVE_EVIDENCE/`；runner 代码位于 `runner/`；运行态（registry/log/gpu 缓存）位于 `shadow/`。
