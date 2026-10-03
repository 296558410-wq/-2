# AGENT_STATUS — Agent1 / Agent2 / Hermes 现状
只读取 `state/agent1_latest.json`、`state/agent2_latest.json`、`state/agent2_trigger.json`、`state/hermes_state.json`、`state/hermes_decision_latest.json`、`state/v2_run_health.json`。

## Agent1（技术）
| 项 | 值 |
|---|---|
| 版本 | `agent1/0.1.0` |
| 最新生成 | 2026-10-02T14:07:17Z（cycle 2026-10-02T14:07Z） |
| 状态 | **OK** |
| 报价源 | gold_spot=**mt5**(XAUUSD) · gold_comex=sina(hf_GC) · silver=mt5 · dxy=sina(DINIW) · ust10y=tencent(usUST) · vix=sina(znb_VIX) · gld=tencent(usGLD)；全部 `_freshness=FRESH`、`_fallback_level=0` |
| 历史 | XAUUSD@mt5；5m/15m/60m/4h/1d 全部 `state=ok`（n_bars 1963/887/396/148/89） |
| 输出 | 逐 TF MA/EMA/RSI/ATR/结构/趋势(ER)/突破/bar_behavior/range60/vwap + `market_regime`(range) + `key_levels` + `data_quality.gaps=[]` |
| 备注 | `point_in_time` 注：历史单源、不取未收盘；当前 K 线源=mt5 |

## Agent2（宏观/全球）
| 项 | 值 |
|---|---|
| 版本 | `agent2/0.2.0-pit` |
| 最新 snapshot | 2026-10-02T14:09:17Z |
| 状态 | **OK** |
| 宏观 | usd=sina DINIW(101.71, −0.32%) · rates=tencent usUST(proxy, 非 ^TNX) · real_rates=TIP(proxy) · central_banks: **fed=null, ecb=null** |
| **data_gaps（5）** | central_bank_policy_rates:no_direct_api · bls_macro:no_domestic_source(BLS 403) · cot:no_domestic_source(CFTC 403) · global_gold_etf_flows:WGC_JS(未取) · central_bank_gold_purchases:no_source |
| 触发 | `agent2_trigger.json` 最近 ts = **2026-09-28T03:53Z**（阈值触发文件未随近期周期刷新） |

## Hermes（决策层）
| 项 | 值 |
|---|---|
| n_runs | 1671 |
| 最新决策 | `WAIT` · reason=`该机会需市场确认(follow-through 未验) → 先观察` · chosen=`opp_geo_shock` · regime=[GEOPOLITICAL_EVENT, RANGE] |
| **decision_source** | **`reference_rules`（占位参照器，非 LLM）** |
| **signal_from_agents** | **false** |
| live_trading | false |
| 假设库 | `current_hypotheses=[]`、`invalidated_hypotheses=[]`（空） |

## 时间周期与依赖
- cadence（config）：agent1 15m · agent2 60m · hermes 15m · engine 15m · daily review 23:30 UTC。
- `v2_run_health`：`gateway_dependency=false`、`llm_dependency=false`（**周期不依赖 OpenClaw / LLM**）。
- shadow_guardian：cycles=90，snapshots=94，snapshot_ok=94，`replay_mismatch=[]`。

## 判定
三个 Agent **当前均在正常出数**（agent 层 OK、replay MATCH、data_quality.gaps=[]）；但 **Hermes 用的是 `reference_rules` 占位器**、且 `signal_from_agents=false` ⇒ **Agent1/Agent2 的产出没有作为信号进入下单路径**（现状下决策与执行未被真正驱动）。
