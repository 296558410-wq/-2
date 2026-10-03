# ECONOMIC RELEVANCE RULES — 经济相关性门（v0，2026-09-07）
> 唯一目的：**不要把统计漂移直接变成赚钱候选。**
> 统计漂移 = INFORMATION。只有 information → probability/payoff/cost 变化 → net EV 成立的链条才进入 MONEY。
> 本文件是周评审的人工裁决依据；engine 只做通道标注，不做最终裁决。

## 0. 五个通道（对应任务书 §三/§十）
漂移只有当它可能改变以下之一时，才允许进入候选讨论：
| 通道 | 含义 | 净 EV 影响路径 |
|---|---|---|
| PROBABILITY | 未来价格方向/事件概率分布变化 | P(win) 变化 |
| PAYOFF | 收益分布形态变化（尾部、跳跃、恢复不对称） | AvgWin/AvgLoss 变化 |
| COST | 交易成本结构变化（spread 水平/分布） | 直接进 net EV 减法项 |
| EXECUTION | 可成交性/时延/滑点/排队变化 | 是否可执行 + 成交质量 |
| OPPORTUNITY_FREQUENCY | 机会出现频率变化 | 每单位时间的 EV 总量 |

## 1. 字段 → 通道映射（与 drift_engine.py ECON_CHANNELS 同步）
| 字段 | 通道 | 说明 |
|---|---|---|
| median_spr_bps / p90_spr_bps | COST, EXECUTION | spread 水平直接决定成本层 |
| p99_spr_bps | COST, EXECUTION, TAIL | 极端 spread 影响尾部成本（跳空/闪崩窗口） |
| spread_usd_median / p90 | COST | 同上（绝对口径） |
| arrival_per_min | OPP_FREQ, INFORMATION | tick 到达率 = 机会密度；本身只信息 |
| burst_min_p99_count / burst_minutes | OPP_FREQ, INFORMATION | 报价突发 = 活动状态 |
| n_minutes | OPP_FREQ | 活跃时长 |
| rv1m_bps | PROBABILITY, PAYOFF | 波动状态 → 概率/赔率层（无方向信息时只信息） |
| n_jump_min / max_min_move_bps | PAYOFF, TAIL | 价格跳跃 = 尾部/执行风险 |
| 各 session 的 median_spr_bps | COST(+EXECUTION) | 会话内成本结构 |

## 2. INFORMATION vs MONEY 判定树
1. 统计漂移（z≥3 & rel≥15%）发生？
2. 命中 ≥1 通道（上表）？
   - 否 → **INFORMATION_ONLY**：记录（DRIFT_LOG），不研究。
3. 通道命中后，问：这个变化是否可能改变"某类交易机会的净 EV"？
   - 幅度是否足够大（相对成本层/信号层已有上界，见 §3）？
   - 持续性是否够（单日/单 session 闪烁 → 不可执行，忽略）？
   - 事前可识别性（发生时能否已知？事后才知道 = 无交易价值，RQ-H1 教训）？
   - 否 → 记录，不研究（§三：否则记录但不研究）。
4. 全部通过 → 仅此时允许打 `CANDIDATE_TRIGGER`（观察级）→ 周评审 → §六 升级判据
   → UNPROVEN MECHANISM → 预注册队列（仍不是实验）。

## 3. 幅度标尺（来自已测证据，成本层）
- retail 往返成本实测基线 ≈ 1.7bps（ACCESS LAB）；ECN CFD ≈ 0.2–0.6bps；CME DMA ≈ −0.5bps（近似）。
- 已测空间内 spread 层净可提取上界 ≈ 0.1bps/笔（S7 / RQ-H1）→ 低于成本 → KILLED。
- 因此：**spread 中位数漂移 ≤ ~0.2bps 且不持续 → 经济意义存疑**；只有大幅(>0.5bps)、
  持续(≥3 日)、跨 session 的 spread 结构变化才可能重开成本层讨论（S-04 保持 KILLED 直到此类证据出现）。
- rv/jump 类漂移单独出现 → 风险层信息（S-06 INFORMATION_ONLY 先例），无方向规则时不算 MONEY。

## 4. 负面清单（历史教训固化）
- 毛量/activity 类变化：proxy，不是 order flow → 默认 INFORMATION（NM-1 不升级为正式候选，任务书裁定）。
- "新结构出现但无法执行/成本吃光" → 一律记录即止。
- 单日单 session 的 spread p99 尖峰（1-5s 闪烁，S3/Breaker 证据）→ 不可交易，忽略。
- 池化 IC 高但日内 t≈0（RQ-H1 K2 教训）→ 观察必须按 session/时段分层，禁止只报聚合值。

## 5. 裁决责任
engine：标注通道 + 记录。周评审（LLM 会议，静默）：按本规则裁决 → 记录即止 / 打 CANDIDATE_TRIGGER /
升级 UNPROVEN MECHANISM。裁决写入 DRIFT_LOG 对应条目（verdict 字段）。material（升级）才上报用户。
