# REFERENCE_VS_AGENT — 参照器决策 vs 真编排(Agent)决策 逐周期对照

样本：**120 个真实归档周期**（`state/snapshots/agent1_/agent2_<cycle>.json`）· 同一时间戳/同一数据快照/同一 `context_hash`。

## 1. 决策分布
| 侧 | WAIT | TRADE | REJECT | 说明 |
|---|---|---|---|---|
| **reference**（生产参照器） | **110** | **10** | 0 | 与当前 V2 生产**完全一致** |
| **agent**（真编排/启发式回退） | 108 | 10 | 2 | `agent_llm=AGENT_LLM_UNAVAILABLE`×120 |

## 2. 关键验收：reference ↔ 生产 **逐周期一一对应**
- 匹配周期 120，**决策一致 120 / 120 = 100.0%**（mismatch 0）。
- ⇒ Shadow 的 PIT 输入与生产**对齐**且可复现生产参照器决策（仪器已自检，见 §5）。

## 3. reference vs agent 一致性
- **一致 118 / 120（98.3%）**。
- **分歧 2 周期**（`20261002T0052Z`、`20261002T0107Z`）：候选仅 `[opp_geo_shock(需确认), opp_narrative_flow_divergence(方向未定)]`。
  - reference：`gate()` 取第一个有候选的类别 → geo_shock → WAIT。
  - agent：无候选通过证据筛 → **REJECT**（更严格）。
- TRADE 集合**完全一致（10/10，同一 opportunity/方向）**；差异仅在"无候选可用"时 WAIT vs REJECT 的语义。
- 置信度：reference 固定 0.55（`build_plan` 占位）；agent 0.6（启发式）；**接真 LLM 后两者将由模型给出**。

## 4. Outcome 链（窗口 240min，MT5 历史 M1，只读）
| 侧/决策 | n | MFE 中位(bps) | MAE 中位(bps) | +30m 未来收益中位(bps) |
|---|---|---|---|---|
| reference TRADE | 10 | +23.6 | **−102.0** | +4.7 |
| agent TRADE | 10 | +23.6 | −102.0 | +4.7 |
| reference WAIT | 110 | — | — | +14.8 |
| agent WAIT | 108 | — | — | +15.3 |
| agent REJECT | 2 | — | — | +8.2 |

- **事实级观察**：这 10 个执行候选的中位 MAE（−102bps）**远大于**中位 MFE（+23.6bps）⇒ 按该窗口，这些机会呈**不利路径**；WAIT 周期的 30m 后续上移更多。
- **不作因果/不调参**（硬边界）：仅记录 outcome 链，供后续独立评估。

## 5. 仪器自检（先查仪器）
- 首轮 backfill 出现 `health FAIL 120/120` 与 `ref↔prod 0/120`：两处**我方仪器缺陷**，已修：
  1. as-of freshness 未解析 **ISO 字符串** `data_ts`（agent2）→ 改用 V2 `_to_epoch`；
  2. as-of 覆写漏了顶层 `ctx["agent1"]["freshness"]`（`gate()` 实际读该字段）→ 已补。
- 修复后：**ref↔prod 120/120**，health 分布恢复正常。
- 另有 cycle 格式归一化（`20261002T1407Z` vs `2026-10-02T14:07Z`）。

## 6. 结论
- **reference 与真编排 agent 可逐周期一一对应**（同时间戳/同快照/同 hash），TRADE 集合完全重合；
- **无 LLM 端点时 agent 侧为显式标注的启发式**（非 LLM 结论）；接入端点即切换为真 LLM 编排（同一接口）；
- 差异集中在"无候选可用"时的 WAIT（参照器）vs REJECT（agent 证据筛）；
- Outcome 链已建立并自动回填，可用于后续**独立**评估（不在本轮做结论）。
