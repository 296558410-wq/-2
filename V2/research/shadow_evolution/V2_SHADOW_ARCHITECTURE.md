# V2_SHADOW_ARCHITECTURE — V2 Evolution Shadow（真实 Agent 决策影子路径）

**隔离目录**：`research/hermes/trader_v2/shadow_evolution/`
**边界**：V2 不停机 · 不读/不改 V1 · 不改 PAPER 执行 · `order_send=0` · 不改历史 ledger · 不改策略参数 · 纯 Shadow · 不用结果反向改假设。

---

## 1. 目标与设计
在 V2 持续运行的同时，对**同一个冻结 PIT 快照**同时产出两条决策，并各自挂 outcome 链：
- **A. `reference`**：当前 V2 生产的确定性参照器（`hermes.decide_pure(source="reference_rules")`）。
- **B. `agent`**：Agent1+Agent2+Hermes **真编排** 决策（LLM 编排；无端点时用显式标注的启发式回退）。
两条共享 **同一 `context_id` / `context_hash` / 数据快照 / 采集时刻**，各自记录 `input_hash` + `decision_hash`。

## 2. 数据/控制流
```
state/snapshots/agent1_<cycle>.json + agent2_<cycle>.json   (V2 每周期归档的完整快照; 只读)
        │
        ├─ agent_orchestrator.context_asof(cycle, a1, a2)   ← 复用 hermes/context.py，
        │       · CTX.CTX_DIR 重定向到 shadow_evolution/decision_contexts（不写 V2 state）
        │       · freshness/health 以 **cycle 时刻** 计（PIT 忠实回放，非 now）
        │
        ├─ discovery.discover(ctx,a1,a2)  → 候选机会（与生产同函数）
        │
        ├─ A: hermes.decide_pure(..., source="reference_rules")     ← 无副作用
        └─ B: agent_orchestrator.orchestrate(ctx,a1,a2,cands,tags)
                 ├─ llm      : V2_SHADOW_LLM_URL/KEY 已配置 → 真调用（生产用）
                 ├─ external : 外部编排(审计/人工/LLM)产出 → --agent-decision 注入
                 └─ heuristic: 无 LLM 时的**独立证据式**决策（显式标注, 非 LLM 结论）
        │
        ▼
SHADOW_DECISIONS.jsonl   (每周期 2 行: reference + agent)
        ▼
shadow_outcomes.py  → SHADOW_OUTCOMES.jsonl  (MFE/MAE/future return/TP-SL path/时间窗口)
```

## 3. 模块
| 文件 | 职责 |
|---|---|
| `shadow_cycle.py` | 单周期影子入口：`--emit-input`（导出冻结输入供外部编排）/ `--agent-decision`（注入）/ 默认 |
| `shadow_backfill.py` | 用历史归档快照批量产出（本快照：**120 周期 / 240 行**） |
| `agent_orchestrator.py` | as-of 上下文 + 真编排（llm/external）+ 启发式回退 + prompt/input hash |
| `shadow_outcomes.py` | outcome 链（MT5 历史 M1，只读） |
| `shadow_analyze.py` | reference↔生产↔agent 对齐 + 供给统计 |
| `SHADOW_DECISIONS.jsonl` / `SHADOW_OUTCOMES.jsonl` | 产物 |
| `decision_contexts/` | **shadow 自己的**冻结上下文（CTX_DIR 重定向），不碰 V2 |

## 4. SHADOW_DECISIONS.jsonl 字段
`shadow_side` · `cycle` · `ts_utc` · `context_id` · `context_hash` · `health_overall` · `a1_freshness` · `a2_freshness` ·
`market_primary_last` · `decision` · `decision_source` · `signal_from_agents` · `agent_llm` · `agent_source` ·
`direction` · `opportunity` · `confidence` · `reason` · `regime_tags` · `risk_reason` · `plan` · `candidates` ·
`input_hash` · `decision_hash`

## 5. 隔离与安全证据
- `CTX.CTX_DIR` 进程内重定向 → 上下文写入 `shadow_evolution/decision_contexts/`；**V2 `state/decision_contexts/` 未被写**。
- 全程只调用**无副作用**函数（`decide_pure` / `discover` / `build_plan`）；**从未调用** `hermes.decide()`/`hermes.run()`（那会写 V2 state/ledger）。
- MT5 仅 `copy_rates_range`（读历史）；**无 order_check / order_send**。
- V2 PAPER 执行链、scheduler、config、ledger 均未触碰。

## 6. 局限（诚实）
- **无 LLM 端点** ⇒ 120/120 行 `agent_llm=AGENT_LLM_UNAVAILABLE`，agent 侧用**启发式回退**（`agent_source="hermes_heuristic(evidence-based, no-llm)"`），**不是** LLM 结论；接上 `V2_SHADOW_LLM_URL/KEY` 即切到真 LLM 编排（同一接口）。
- 本快照为**最近 120 周期**（约 30h）；可 `--limit N` 扩到全部 1727 对快照。
- PIT 忠实回放依赖归档快照中的 `data_ts`；缺失者按 `unknown`（→health FAIL）。
