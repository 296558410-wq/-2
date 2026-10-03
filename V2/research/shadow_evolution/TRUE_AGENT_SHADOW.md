# TRUE_AGENT_SHADOW — 三侧 Shadow（reference_rules / hermes_heuristic / true_llm_agent）

**目录**：`research/hermes/trader_v2/shadow_evolution/`
**边界**：V2 不停机 · 不触 V1 · PAPER 执行不变 · `order_send=0` · Shadow 不入 execution · 不改历史 ledger · 不改 V2 生产参数 · 不用 outcome 反向改 prompt/rule/threshold · 保留 reference/heuristic 作对照。

---

## 1. 三侧设计（同周期、同快照、同 as-of 时间戳）
| 侧 | 实现 | 说明 |
|---|---|---|
| `reference_rules` | `hermes.decide_pure(source="reference_rules")` | 与当前 V2 生产**完全相同**的确定性参照器（对照组 1） |
| `hermes_heuristic` | `agent_orchestrator.heuristic_decide()` | 独立**证据式**启发式（macro-align / priced_in / requires_confirmation / R / counter-thesis）；显式标注非 LLM（对照组 2） |
| `true_llm_agent` | `agent_orchestrator.orchestrate_llm()` | 真 LLM 编排；**无端点/密钥 ⇒ `LLM_UNAVAILABLE`（不静默退化）** |

三侧共享：`context_id` · `context_hash` · data snapshot（`agent1_/agent2_<cycle>.json`）· as-of 时间戳（`created_utc`）。

## 2. 数据/控制流
```
state/snapshots/agent1_/agent2_<cycle>.json  (只读)
   → agent_orchestrator.context_asof()  (CTX_DIR 重定向到 shadow/decision_contexts; freshness/health 以 cycle 时刻计)
   → discovery.discover()  (同一候选集合, 三侧共用)
   → 三侧决策 (reference / heuristic / true_llm_agent)
   → TRUE_AGENT_DECISIONS.jsonl (3 行/周期)
   → true_agent_outcomes.py → TRUE_AGENT_OUTCOMES.jsonl (MFE/MAE/future return, MT5 历史 M1 只读)
```

## 3. 记录字段（每行）
`shadow_side` · `cycle` · `ts_utc`(as-of) · `context_id` · `context_hash` · `health_overall` · `a1/a2_freshness` ·
`market_primary_last` · `decision` · `decision_source` · `signal_from_agents` · `agent_llm` · `agent_source` ·
`direction` · `opportunity` · `confidence` · `reason` · `evidence` · `regime_tags` · `risk_reason` · `plan` ·
`candidates` · **`input_hash`** · **`prompt_hash`** · **`decision_hash`**

## 4. 本轮结果（120 周期）
| 侧 | WAIT | TRADE | REJECT | LLM_UNAVAILABLE |
|---|---|---|---|---|
| `reference_rules` | 110 | 10 | 0 | — |
| `hermes_heuristic` | 108 | 10 | 2 | — |
| **`true_llm_agent`** | 0 | 0 | 0 | **120** |

- **真 Agent 未实际运行**（无可用 LLM 端点，见 `LLM_PROVENANCE.md`）。
- 参照/启发式两份**对照组完整保留**（`SHADOW_DECISIONS.jsonl` + 本文件三侧）。
- outcome 回填 **360/360 OK**。

## 5. 启用真 LLM 的契约（不改本 harness）
```
set V2_SHADOW_LLM_URL = <OpenAI-compatible /v1/chat/completions 端点>
set V2_SHADOW_LLM_KEY = <key>            # 仅经环境/密管注入；不写入仓库、不打印
# 模型: deepseek/deepseek-v4-flash (与 V2 config agents 一致)
```
- 请求: `POST {URL}` body `{model, messages:[system,user], temperature:0, response_format:{type:"json_object"}}`；
  其中 user 内容 = `{decision_context, candidates, hermes_regime_tags, prompt_md}` 的规范化 JSON；`prompt_hash` 随之固定。
- 返回须为 JSON（`decision` ∈ TRADE/WAIT/REJECT + reason/opportunity/direction/confidence）。
- 端点已配置时 `agent_llm="OK"` 并写真实决策；未配置时 `agent_llm="LLM_UNAVAILABLE"`——**永不**用启发式冒充。

## 6. 隔离与安全证据
- 只调用无副作用函数（`decide_pure`/`discover`/`build_plan`/`heuristic_decide`/`orchestrate_llm`）；**从不**调用 `hermes.decide()/run()`（会写 V2 state/ledger）。
- `CTX.CTX_DIR` 进程内重定向 → 上下文只写 `shadow_evolution/decision_contexts/`。
- MT5 仅 `copy_rates_range`（读）+ `initialize/shutdown`；**无 order_check / order_send**。
- V2 state 校验：`opportunity_ledger/hermes_memory/hermes_state` mtime 保持 22:09:17（生产周期，早于影子运行）。
