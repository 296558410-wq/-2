# DISCOVERY_SHADOW_REPORT — 任务 A：Opportunity Discovery（生成/排序分离）

样本：**120 个真实 PIT 周期**（`state/snapshots/agent1_/agent2_<cycle>.json`）。
组件：`shadow_evolution/discovery_shadow.py`（新，Shadow）· `discovery_compare.py`（对照）· 数据 `_discovery_shadow_stats.json`。
**reference = 原 `hermes/discovery.py`（未改动，保持对照）**；新 discovery **不降低任何阈值/触发条件**（直接复用原生成函数）。

## 1. 结构改动（仅为"生成 vs 排序"分离）
1. **生成**：与原 discovery **完全相同**的条件（零阈值变更），仅增加 `source` 标签；
2. **presence vs trigger**：常驻型来源（geopolitical / macro_repricing / narrative_flow，`requires_confirmation=True`）在缺乏可观察 follow-through 时标 `presence_only=True`；
3. **排序独立**：新增 `rank()`（确定性：期望R / 有无触发 / 方向明确 / 未定价 / 证据量），**不再用 first-hit 类别优先级**；
4. **选择**：`select()` 先取有触发的最高分候选，presence-only 仅兜底。

## 2. 供给统计（120 周期，reference）
| 来源 | 出现周期数 | 占比 |
|---|---|---|
| `opp_geo_shock` | **120 / 120** | **100%** |
| `opp_narrative_flow_divergence` | 46 | 38.3% |
| `opp_bo_short` | 8 | 6.7% |
| `opp_fbo_short` | 4 | 3.3% |
| `opp_fbo_long` | 3 | 2.5% |
| `opp_bo_long` | 3 | 2.5% |
| `opp_trend_*` | **0** | 0% |

每周期候选数：**1 个 → 64 周期（53.3%）**；2 → 48；3 → 8。

## 3. reference vs 新 discovery 逐周期对照
| 指标 | reference | 新 discovery |
|---|---|---|
| 候选来源分布 | geo 120 / narrative 46 / … | **完全相同** |
| 每周期候选数 | 1:64 / 2:48 / 3:8 | **完全相同** |
| 选中分布 | geo 102 / fbo_l 3 / fbo_s 4 / bo_s 8 / bo_l 3 | **完全相同** |
| geo_shock 选中占比 | **0.85** | **0.85** |
| **选择改变周期数** | — | **0 / 120** |

## 4. 结论
- **单一供给仍在**：`opp_geo_shock` 候选 **120/120 = 100%**，选中 **85%**。根因 = **生成条件的频率**（新闻源几乎恒有地缘事件 ⇒ `geo_n>0` 恒真），**不是排序**。
- **新 discovery 未产生行为变化**（`picks_changed = 0`）——原类别优先级已优先技术类，故"排序分离"对结果无影响。此结果本身即**证明**了单一化的根因在**生成侧**。
- **未降低门槛、未人为制造交易**（候选/选择集合逐周期完全一致）。
- 真正消解单一化需要改动**生成触发条件**（例如要求可观察 follow-through 才生成 geo 候选）——这属于**阈值/触发策略变更**，**超出本任务硬边界**（"禁止通过降低门槛人为制造交易数量"），故**未实施**，登记为**待决事项**。
- PIT/hash/replay：输入为归档快照（PIT as-of），每周期记 `input_hash`/`decision_hash`；replay 见 `REPLAY_REPORT.md`。
