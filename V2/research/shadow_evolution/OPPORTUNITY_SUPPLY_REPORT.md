# OPPORTUNITY_SUPPLY_REPORT — 机会供给来源与 `opp_geo_shock` 主导原因

样本：Shadow 最近 **120 周期**（`SHADOW_DECISIONS.jsonl`，reference 侧）+ 生产 `state/opportunity_ledger.jsonl`（全历史 2815 机会）。

## 1. 供给统计（120 周期）
| 候选 | 出现周期数 | 占比 |
|---|---|---|
| **`opp_geo_shock`** | **120 / 120** | **100.0%** |
| `opp_narrative_flow_divergence` | 21 | 17.5% |
| `opp_fbo_short` | 8 | 6.7% |
| `opp_bo_short` | 6 | 5.0% |
| `opp_bo_long` | 5 | 4.2% |
| `opp_fbo_long` | 3 | 2.5% |
| `opp_trend_*` | **0** | 0% |

**每周期候选数**：1 个 → **80 周期（66.7%）**；2 个 → 37（30.8%）；3 个 → 3（2.5%）。
⇒ **2/3 的周期只有 1 个候选，且那个候选 100% 是 `opp_geo_shock`。**

全历史对照（`opportunity_ledger` 2815 条）：`geo_shock 1442`、`narrative_flow_divergence 431`、`macro_repricing_short 329`、`trend_long 152`、`bo_long 140`…——`geo_shock` 亦为最大类。

## 2. 为什么 `opp_geo_shock` 长期主导（代码级，只读定位）
`hermes/discovery.py`：
```python
geo_n = len(_g(a2, "geopolitics", "events", default=[]))
...
if geo_n > 0:                       # ← 只要 Agent2 有 ≥1 条地缘事件就生成
    cands.append({"id": "opp_geo_shock", "category": "geopolitical", "dir_hint": "LONG",
                  "requires_confirmation": True, ...})
```
**原因链（全部命中，缺一不可）**：
1. **触发条件过宽**：`geo_n > 0` 即生成。Agent2 的 `geopolitics.events` 由新闻源（wallstreetcn/CNBC/FXStreet/Jin10）驱动，**几乎每轮都 ≥1 条地缘相关新闻** → `opp_geo_shock` **恒生成**（本样本 120/120）。
2. **它恒为 `requires_confirmation=True`** → 进入 `hermes.gate()` 必然落到 `"该机会需市场确认(follow-through 未验) → 先观察"` ⇒ **WAIT**。
3. **技术类候选门槛过严**：`trend` 需 `regime=="trend"` **且 ≥3 个 TF `swing_bias` 同向**；`breakout/false_breakout` 需 15m `breakout.state` 为特定值。当前 `market_regime=range`（15m/60m/5m 均 range）⇒ 技术类**几乎不生成**（本样本 trend=0）。
4. **选择器取"第一个有候选的类别"**（生产参照器 `CATEGORY_PRIORITY=[false_breakout, breakout, trend, macro_repricing, geopolitical, narrative_flow]`）——若技术类空缺，则落到 `geopolitical`（geo_shock）→ 恒 WAIT。

## 3. 结论
- `opp_geo_shock` 的主导 = **结构性**（供给端触发过宽 + 需求端恒需确认 + 技术类门槛与当前 regime 不匹配），**非偶然**。
- 直接后果：**绝大多数周期无可执行候选** → 决策层长期 WAIT（本样本 reference 110/120 = 91.7% WAIT）。
- 与既有 `research/OPPORTUNITY_DEGENERATION_DIAG_20260915.md` 的独立结论一致（geo_shock 100% 出现、选择器为参照器）。
- **本报告只做统计与定位，不提出参数改动**（硬边界：不改策略参数）。
