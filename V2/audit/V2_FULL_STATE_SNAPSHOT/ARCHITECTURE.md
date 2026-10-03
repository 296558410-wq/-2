# ARCHITECTURE — V2 真实运行链（以当前实际代码与配置为准）
只读从 `runtime/`、`agents/`、`hermes/`、`execution/`、`data_sources/`、`ledger/`、`config/v2_config.json` 恢复；**不据文档猜**。

## 0. 顶层调用链
```
Windows Task Scheduler  (hermes-v2-cycle, 15m)
        │   （不经 OpenClaw / 无 LLM 依赖）
        ▼
runtime/v2_scheduled_cycle.py            ← 周期入口（零-LLM 直跑）
        │
        ├─ data_sources/router.py        ← 唯一取数入口（P0-02：router = sole data entry）
        │        ├─ registry.py          ← 源优先级/符号表
        │        ├─ adapters_market.py / adapters_macro.py
        │        ├─ mt5_market.py        ← V2 独立 MT5 实例（只读行情）
        │        ├─ local_bars.py        ← 本地 tick→bar
        │        ├─ cache.py / pit_cache.py  ← FRESH/STALE/PIT as-of
        │        ├─ net.py               ← 超时/重试/退避
        │        └─ validate.py / health.py / audit.py
        │
        ├─ agents/technical/agent1.py    ← Agent1（技术面，15m）
        │        ├─ market_data.py  features.py
        ├─ agents/macro_global/agent2.py ← Agent2（宏观/全球，60m）
        │        ├─ sources.py  evidence.py  release_registry.py  event_trigger.py
        │
        ▼
hermes/context.py      ← 组装 decision context（build_health：技术+宏观+源健康+\
                           PIT/新鲜度；DEGRADED→WAIT，FAIL→REJECT）
        ▼
hermes/discovery.py    ← Opportunity Discovery（geo_shock / macro_repricing / trend / \
                           breakout / false_breakout / narrative_flow_divergence）
        ▼
hermes/hermes.py       ← 门控 + 决策（CATEGORY_PRIORITY 取一个候选；requires_confirmation→WAIT）
        ▼
execution/execution_guard.py  ← 执行守卫（新文件，未跟踪）
execution/paper_executor.py | broker_demo_executor.py | fxtm_demo_adapter.py | price_space.py
        ▼
ledger/ledger.py  →  ledger/hermes_v2_ledger.jsonl  ；ledger/replay.py（回放/对账）
        ▼
state/  → opportunity_ledger.jsonl · hermes_memory.jsonl · evidence_registry.jsonl ·
         macro_releases.jsonl · paper_* · agent*_latest.json · v2_run_health.json ·
         runs/ACTIVE.json · snapshots/ · decision_contexts/
        ▼
dashboard/server.py（V2 面板，只读展示）
```

## 1. Agent1（技术）— `agents/technical/`
- **输入**：quotes（gold_spot=XAUUSD@mt5、gold_comex=sina hf_GC、silver=XAGUSD@mt5、dxy=sina DINIW、ust10y=tencent usUST、vix=sina znb_VIX、gld=tencent usGLD）；历史=XAUUSD@mt5（5m/15m/60m/4h/1d）。
- **输出**：逐 TF 的 MA/EMA/RSI14/ATR14/结构(swing)/trend_range(ER)/breakout/bar_behavior/range60/vwap + `market_regime` + `key_levels` + `data_quality`；`point_in_time`（历史单源 Yahoo→已改 mt5，未收盘不取）。
- **周期**：15m。

## 2. Agent2（宏观/全球）— `agents/macro_global/`
- **输入**：usd=sina DINIW、rates=tencent usUST（7-10Y ETF **代理**，非 ^TNX）、real_rates=TIP 代理、GLD 流量、新闻（wallstreetcn/cnbc/fxstreet/jin10）、日历（jin10）。
- **输出**：`gold_macro_state`（BEARISH/NEUTRAL/…）+ news/事件 + **evidence registry** + `release_registry`（宏观发布 + PIT）+ `event_trigger`（阈值触发）。
- **周期**：60m。**data_gaps**：中央行政策利率(无直连 API) · BLS 宏观(403) · COT/CFTC(403) · WGC ETF 流量(JS 未取) · 央行购金(无源)。
- **fail-closed**：核心宏观测 DEGRADED 不得降级为 NEUTRAL（commit `18a440c`）。

## 3. Hermes 决策层 — `hermes/`
- `context.py`：`build_health()` 仅依据 `data_quality.gaps` 与 freshness 判技术健康；**P0 修复后**加入 `trading_source_status`（源必须=mt5，否则 DEGRADED）。
- `discovery.py`：候选生成（`opp_geo_shock` 只要地缘事件非空即生成，`requires_confirmation=True`）。
- `hermes.py`：`CATEGORY_PRIORITY=[false_breakout, breakout, trend, macro_repricing, geopolitical, narrative_flow]` 取**第一个有候选的类别** → `gate()`；`requires_confirmation=True` 直接 WAIT。
- **决策来源 = `reference_rules`（占位参照器）**，`signal_from_agents=false`（docstring：生产应为 LLM 编排）。
- `PROMPT.md`（hermes2-prompt/0.1.0）；config `hermes.voting_forbidden=true`。

## 4. Risk / Execution
- **Risk**（config `execution.risk`）：`per_trade_pct=1.0`、`max_daily_loss_pct=3.0`、`max_consecutive_losses=4`、`single_position=true`、`max_notional_usd=25000`；contract：min 0.01 / max 0.05 手、contract_size 100oz、杠杆 500。
- **Execution**：可插拔后端 `[paper_local, fxtm_demo, oanda_v20]`；`backend=fxtm_demo`、`execution_mode=BROKER_DEMO`、`broker_demo_enabled=true`、`live_trading=false`；成本模型 spread 0.35bps/slip 0.30bps/latency 250ms。
- **守卫**：`execution_guard.py`（未跟踪）、`d364f5d` 券商止损**预校验 fail-closed**、`a6229b1` PIT as-of 缓存、价格空间验证 `price_space.py`（可开关，集成时为 additive/inert）。

## 5. Ledger / Replay / Truth
- `ledger/ledger.py`：事件式账本（`event_id/event_type/seq/timestamp_utc/environment/execution_mode/strategy_id/…`）+ `replay.py` 回放；`migrate_demo_calibration.py` 迁移。
- `state/snapshots/`（3521）与 `state/decision_contexts/`（1828）= 决策输入快照/上下文（P1-b `e0f2a6a`：decision input snapshot + `decide_pure` 离线回放 + fail-closed）。
- `replay_status=MATCH`；shadow guardian 每周期校验（`tools/shadow_guardian.py`）。

## 6. 隔离（config `isolation`）
`allow_real_trading=false`、`reuse_v1_mt5_terminal=false`、`reuse_v1_ledger=false`、`reuse_v1_account=false`；V2 独立 paper 账户与账本；V1 只读。
