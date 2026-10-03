# V3 E-R1 — XAUUSD 短周期微观结构研究

- 任务：`V3-PHASE2-E-R1` ｜ 协议评估前冻结：`registry_hash_sha256 = a36765feb3760da1804a079080710d5347db09c82087f6ee0e0eeaa58ce3b0b2`
- 结果文件：`results_e_r1.json`（自带 `_self_sha256_after_write = 297f4e1b045ed3b3f4a0d5dbc618cf36161285b813a4b7fd0c64af1f6585443c`）
- 复现：`python research/v3_e_r1/run_e_r1.py` → `python research/v3_e_r1/finalize_e_r1.py`

**执行前确认（任务书要求）**
| 项 | 值 |
|---|---|
| 当前 git | `HEAD = efe1fee`（本任务前）；`trader_v3` 工作树干净 |
| 数据来源 | 不可变快照 `V3-SNAP-20260922T025312Z`，36 文件 / **7,285,000 ticks** / 2026-08-04T01:05Z–09-22T02:39Z / ms / UTC / **SHA256 36/36 MATCH** |
| registry hash | 协议冻结后 `a36765fe…`（本文开头）；结果自身 hash `297f4e1b…` |

## 1. 假设（冻结于评估前，双向独立）

| ID | 族 | 机制 | 方向 |
|---|---|---|---|
| E1_TICKIMB_CONT / _FADE | 1 Tick imbalance | `TI_PROXY = Σsign(dmid,100)/√100`，`\|TI\|≥2` 起点 | 跟随 / 反向 |
| E2_IMPACT_RECOVERY_FADE | 2 流动性补充·冲击恢复 | `\|z(ret500)\|≥2` 冲击后，流动性补充、中间价向冲击前回归 | 反向（fade） |
| E2_RECOVERY_TIME | 2 同上 | 冲击后价差回到中位 ±10% 所需时间（描述性） | — |
| E3_JOINT_STATE_DRIFT | 3 价差×波动×压力联合状态 | 联合格 `(价差三分位)×(rv三分位)×(压力符号)` 是否携带边际之外的信息 | 跟随压力 |
| E4_MICRO_CONT / _FADE | 4 微观延续/反转 | `\|z(ret100)\|≥2` 微冲量 | 跟随 / 反向 |

**PIT 合规**：全部特征只用 T 及之前数据（trailing 窗口 + 因果分位网格）；时间戳字段 `ts_utc`（ms/UTC，显式）；入场 = 信号 tick 之后的第一个 tick（多头吃 ask / 空头吃 bid）。
**未使用**：V1/V2 任何状态、历史盈利结果、未来数据；无参数扫描（阈值沿用前轮冻结约定）。

## 2. 数据范围

7,285,000 ticks / 1,055 段 / 35 个交易日（2026-08-04→09-22）。
`volume / volume_real / last` **恒为 0 ⇒ DATA_GAP** ⇒ 一切流量特征都是**报价口径**的 `_PROXY`。

## 3. 方法

- 成本锚 `REAL_RT_COST_BP = 0.914`（spread 0.18 + commission 0.22 USD/RT，`CALIBRATION_20RT_20260921`），压力 **0/1/2/3×**
- `MID_MARKOUT = dir×(future_mid−entry_mid)`；阶梯判在 **cost-adjusted**
- 期限 **{100, 250, 500, 1000, 2000, 5000} ms**；IS/OOS **按时间 70/30**；**符号翻转置换 2000 次**；**块自助 2000 次**；**重叠检查**报 raw n / overlap ratio / `effective_n`（贪心非重叠）
- E3 额外做 **BH-FDR（0.05）** 校正（9 格 × 6 期限 = 54 个检验）
- 阶梯：INSUFFICIENT_SAMPLE → COST_INSUFFICIENT → REJECT → EDGE_UNCERTAIN → EXECUTION_UNREALISTIC → CANDIDATE

## 4. 结果（各期限最佳毛边 bp）

| 假设 | raw 事件 | 最大毛边 | 期限 | 阶梯 |
|---|---|---|---|---|
| E1 TI 跟随 | 41,455 | **−0.073** | 5000ms | COST_INSUFFICIENT |
| E1 TI 反向 | 41,455 | **+0.073** | 5000ms | COST_INSUFFICIENT |
| **E2 冲击恢复 fade** | 5,096 | **+0.212** | 5000ms | COST_INSUFFICIENT |
| E2 恢复时间 | 5,096 | — | — | **INVALID_OPERATIONALISATION** |
| E3 联合状态 | 9 格 | ±0.093 | 5000ms | COST_INSUFFICIENT，**FDR 存活 0/54** |
| E4 微延续 | 12,553 | +0.174 | 5000ms | COST_INSUFFICIENT |
| E4 微反转 | 12,553 | −0.174 | 5000ms | COST_INSUFFICIENT |

**读数**：E1/E4 的 CONT/FADE 仍严格互为镜像（±x）⇒ 噪声镜像，非方向性传导。
**E3 的重点**：联合状态看起来能挑出"最好"的格子，但 **54 个检验无一通过 BH-FDR**，且最好格子也只有 0.093 bp ⇒ **联合状态没有携带边际之外的可交易信息**。

## 5. 成本影响

- **全部可评假设止于 `COST_INSUFFICIENT`**：最大毛边 **0.212 bp = 成本锚的 23%**
- 无一条在 1× 成本后为正 ⇒ 2×/3× 更无意义
- 结论是**成本墙**，不是"数据不足"：E1 有效样本 41,448、E4 12,501，均远超门槛 30

## 6. 局限（如实）

1. **`volume ≡ 0`**：真正的 OFI / 队列 / 成交带不可得 ⇒ 第 1 族只能用报价代理，**代理不是真 OFI**
2. **E2_RECOVERY_TIME 操作性失败**：价差在冲击当刻多数已在中位 ±10% 内，计时器在 `j=i` 立即触发 ⇒ 中位/ p90 都是 **0 ms**，**该指标什么都没测到**。如实标 `INVALID_OPERATIONALISATION`，**不作为发现**
3. **冲击 ≤ 5s**：5,000ms 是冻结的最长期限；更长尺度未测
4. **窗口**：35 个交易日、单一 demo 场所（FXTM）；跨场所普适性未证
5. **E3 网格步长 500 tick**：为抑制重叠而做的确定性抽样，可能漏掉更短的联合状态

## 7. 可重复性与一处 R1 缺陷（重要）

| 对照 | 本次 | Phase-2 R1 | 判定 |
|---|---|---|---|
| 冲击 fade @5000ms | **+0.212 bp** | A2_PXSHOCK_REV **+0.213 bp** | ✅ **一致**（同快照、同触发、同方向） |
| tick imbalance | E1 用 `sign(TI_PROXY)` | A1 传了**常数 ±1** | ⚠️ **不可比** |

**发现的 R1 缺陷**：Phase-2 R1 的 `A1_TICKIMB_CONT/REV` 把**常数方向（+1/−1）**传进求值器，而不是协议里写的 `sign(TI_PROXY)` —— 也就是说那两行量的是**固定做多/做空**，**不是**声明的失衡机制。E-R1 的 E1 按冻结定义正确实现，因此两者不是"矛盾"，而是 **R1 的 A1 两行属实现缺陷**。这正是"换协议重跑"的价值。

## 8. 最终判定

```
V3_E_R1 = NO_VALIDATED_EDGE
```
淘汰原因：**全部可评假设止于 `COST_INSUFFICIENT`**（最大毛边 0.212 bp < 成本锚 0.914 bp）；无成本后为正者；无稳定性/非随机/可重复的证据支持 `VALIDATED_EDGE`。

**边界核对**：未改 V1/V2（本次只写 `research/hermes/trader_v3/`）；未读 V1/V2 交易状态作为输入；未用历史盈利；未进执行；**未下单**；未调协议迎合结果；未用未来数据；未做参数挖掘。

> 附注（非本任务范围，仅记录）：`trader_v2` 工作树有 13 个**未提交的代码改动**（mtime 2026-09-18/19/29，**非本次产生**），意味着**在跑的 V2 与 git HEAD 不一致**。
