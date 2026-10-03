# THREE_WAY_COMPARISON — reference_rules vs hermes_heuristic vs true_llm_agent

样本：**120 个真实归档周期**（`agent1_/agent2_<cycle>.json`），三侧共享 `context_id`/`context_hash`/快照/as-of 时间戳。
证据：`TRUE_AGENT_DECISIONS.jsonl`(360 行) · `TRUE_AGENT_OUTCOMES.jsonl`(360 行)。

## 1. 三侧决策分布
| 侧 | WAIT | TRADE | REJECT | LLM_UNAVAILABLE |
|---|---|---|---|---|
| `reference_rules` | **110** | **10** | 0 | — |
| `hermes_heuristic` | **108** | **10** | **2** | — |
| `true_llm_agent` | 0 | 0 | 0 | **120** |

三侧**逐周期可比较**：120/120 周期均有三行。

## 2. 一致性
| 对比 | 一致 | 一致率 | 差异 |
|---|---|---|---|
| reference ↔ 生产记录 | 120/120 | **100.0%** | 0（PIT 输入对齐、参照器可复现） |
| reference ↔ hermes_heuristic | 118/120 | 98.3% | 2 周期 |
| true_llm_agent ↔ 任一 | — | — | **无法比较**（`LLM_UNAVAILABLE`） |

**差异周期（reference 与 heuristic）**：`20261002T0052Z`、`20261002T0107Z`
- 候选仅 `[opp_geo_shock(需确认), opp_narrative_flow_divergence(方向未定)]`
- reference：取首个有候选类别 → geo_shock → **WAIT**（"该机会需市场确认"）
- heuristic：无候选通过证据筛 → **REJECT**
- **差异仅存在于"无候选可用"时的 WAIT vs REJECT 语义**；TRADE 集合**完全重合（10/10，同一 opportunity/方向）**。

## 3. 是否产生不同的机会/方向
- 三侧**共享同一候选集合**（同一 `discovery.discover()`）⇒ **机会来源无差异**。
- reference 与 heuristic 选中的 TRADE 机会**完全一致**（10/10）；**无新增方向**。
- `true_llm_agent` 因 `LLM_UNAVAILABLE` **未产出**任何机会/方向。

## 4. 差异对应的未来 outcome（窗口 240min，MT5 历史 M1）
| 侧/决策 | n | MFE 中位(bps) | MAE 中位(bps) | +30m 未来收益中位(bps) |
|---|---|---|---|---|
| reference TRADE | 10 | +37.2 | **−102.0** | +6.1 |
| heuristic TRADE | 10 | +37.2 | −102.0 | +6.1 |
| reference WAIT | 110 | — | — | +12.1 |
| heuristic WAIT | 108 | — | — | +13.3 |
| heuristic REJECT | 2 | — | — | +6.7 |
| true_llm_agent | 120 | — | — | +8.6（仅记录，非决策结果） |

- 事实级：10 个执行候选的中位 **MAE(−102bps) 远大于 MFE(+37.2bps)**，30m 后续 +6.1bps；WAIT 周期 30m 后续 +12.1bps。
- **不作因果、不调参、不以 outcome 反向改规则**（硬边界）。

## 5. 结论
- 三侧架构与逐周期对照**已成立且可审计**；**但真 LLM 侧本轮未产生实质差异**（`LLM_UNAVAILABLE`）。
- 现有两份对照（reference/heuristic）差异**极小且集中**（仅 2 周期、仅 WAIT/REJECT 语义）。
- 真实差异度量**待 LLM 端点可用后重跑**（同一 harness，无需改动）。
