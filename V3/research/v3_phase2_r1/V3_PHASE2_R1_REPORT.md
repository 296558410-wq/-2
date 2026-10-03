# V3 阶段2 R1 — 新机制与高频 Alpha 探索报告

- 任务：V3-PHASE2-NEW-MECHANISM-ALPHA-001（阶段2 · 第1轮）
- 时间：2026-10-01 12:30–12:5x UTC
- 边界（已冻结）：`V3_EXECUTION_MODE=RESEARCH_READONLY` · `V3_ORDER_SEND_ALLOWED=NO` · `V3_FORWARD_ALLOWED=NO` · `V3_LIVE_ALLOWED=NO` · V1/V2 零交互
- 数据：只读不可变快照 `V3-SNAP-20260922T025312Z`（36 文件 / **7,285,000 ticks** / 1055 段 / 2026-08-04T01:05Z–2026-09-22T02:39Z），**SHA256 36/36 与 MANIFEST 一致**
- 协议：`FROZEN_PROTOCOL.json`，`registry_hash_sha256 = 663829a925e87ae1642c512cf3cd5e636f9c8bc975b594cab021fcdf54c1bcaa`（**评估前冻结，未改**）
- 成本锚：`COST_MODEL_VERSION = CALIBRATION_20RT_20260921`，`REAL_RT_COST_BP = 0.914`；压力 x0/x1/x2/x3
- 复现：`python research/v3_phase2_r1/run_r1.py` → `results_r1.json`；`run_f1.py` → F1 并入

---

## 1. 冻结口径（评估前）

| 项 | 冻结值 |
|---|---|
| 冲击触发 | `\|z\| >= 2.0`（trailing 3000 ticks，沿用前轮约定，**非扫描**） |
| 价差/波动/到达率 regime | trailing 3000-tick 因果分位（q67 / q90），前向填充，**T 之前的数据** |
| 微价极端 | 0.70（后证退化，见 §4） |
| 期限 | 100 / 250 / 500 / 1000 / 2000 / 5000 ms |
| IS/OOS | 按时间 70/30（不洗牌） |
| 显著 | 符号翻转置换 2000 次 + 块自助 2000 次（块=事件序 50） |
| 方向 | 每个信息源**双向独立冻结**（延续 / 反转） |
| 阶梯 | INSUFFICIENT_SAMPLE → COST_INSUFFICIENT → REJECT → EDGE_UNCERTAIN → EXECUTION_UNREALISTIC → CANDIDATE |

**markout 三分（contract v2 §6/§7）**：`MID_MARKOUT = dir*(future_mid-entry_mid)`；`EXECUTION_MARKOUT = dir>0? future_mid-entry_ask : entry_bid-future_mid`；`COST_ADJUSTED = MID_MARKOUT − 0.914bp×stress`。阶梯判在 **cost-adjusted mid**。

## 2. 样本与事件

| 族 | 假设 | 事件数 | 1000ms 有效样本(eff_n) |
|---|---|---|---|
| A | A1 报价失衡冲击（TI_PROXY，双向） | 41,455 | 25,183 |
| A | A2 价格冲击（\|z500\|≥2，双向） | 5,096 | 2,690 |
| C | C1 宽价差 regime 起点（反转） | 70,849 | 19,547 |
| C | C2 报价到达率爆发（延续） | 100,352 | 75,472 |
| B | B1 微价位置（执行 Alpha） | **0** | — |
| F | F1 高波动 regime（非方向） | 19,402 | 19,402 |

`volume / volume_real / last` **恒为 0 ⇒ DATA_GAP**；一切流量特征只能是 `_PROXY`。

## 3. 结果（阶梯裁决）

**全部 6 条可测假设 × 6 个期限 = 36 个检验，无一进入 CANDIDATE。**

| 假设 | 最大 \|MID markout\| | 方向 | perm_p | net@1x (bp) | net@2x (bp) | 裁决 |
|---|---|---|---|---|---|---|
| A1_TICKIMB_CONT | +0.0058 bp @5000ms | 延续 | 0.468 | −0.908 | −1.822 | **COST_INSUFFICIENT** |
| A1_TICKIMB_REV | −0.0058 bp @5000ms | 反转 | 0.468 | −0.920 | −1.834 | **COST_INSUFFICIENT** |
| A2_PXSHOCK_CONT | −0.2128 bp @5000ms | 延续 | 0.0005 | −1.127 | −2.041 | **COST_INSUFFICIENT** |
| A2_PXSHOCK_REV | **+0.2128 bp** @5000ms | 反转 | 0.0005 | −0.701 | −1.615 | **COST_INSUFFICIENT** |
| C1_WIDESPREAD_MR | +0.0339 bp @5000ms | 反转 | 0.0005 | −0.880 | −1.794 | **COST_INSUFFICIENT** |
| C2_ARRIVAL_BURST_CONT | −0.0196 bp @5000ms | 延续 | 0.0005 | −0.934 | −1.848 | **COST_INSUFFICIENT** |
| B1_MICROPRICE_EDGE | — | — | — | — | — | **NOT_TESTABLE** |

**关键判读（问题 A / 问题 B 分开答）**

- **问题 A（是否存在统计关系）**：A2 价格冲击（5s）与 C1/C2 存在**可检出但极弱**的关系 —— `perm_p ≈ 0.0005`，
  但量级只有 **0.03–0.21 bp**，且 A2 延续/反转**互为镜像**（+0.213 / −0.213），说明这更像**单笔噪声的镜像**，
  而非系统性传导。A1 / C2 连显著性都没有（perm_p ≈ 0.47 / 量级 0.006–0.02 bp）。
- **问题 B（是否够覆盖成本）**：**远远不够**。全部假设的毛边（MID markout）都 **< 0.914 bp 成本锚**，
  最大者 0.213 bp 仅为其 **23%**。故阶梯在 **COST_INSUFFICIENT** 停止（不是 REJECT，不是「没有 alpha」）。
- **A2 反转在 5s 上净额 −0.70 bp（1x）**：统计显著也被成本吞掉；x2 成本下 −1.62 bp。

## 4. 未测族（如实收口，不编造）

- **B 执行 Alpha — NOT_TESTABLE**：`B1` 用 `(mid−bid)/(ask−bid)` 定义微价位置，因 `mid ≡ (bid+ask)/2`
  **恒等于 0.5**（构造性退化），触发 0 事件。真正的 size-weighted microprice / 队列 / 成交概率需要
  `bid_vol/ask_vol`，而该字段 **恒为 0（DATA_GAP）**。⇒ 本快照上「执行 Alpha」族**不可测**，非「无 alpha」。
- **D 事件微观结构 — NOT_TESTABLE**：无与 tick 窗口（2026-08-04..09-22）**重叠**的 PIT 事件日历
  （Jin10 窗口为 2026-09-21..26，前轮已证零重叠）。零重叠 ⇒ 停该支线，不编数据。
- **E 跨市场 Lead-Lag — LIMITED**：Yahoo 5m DXY/VIX/^TNX 仅覆盖 ~2026-08-25..09-18（约 18 个交易日）；
  且 DXY 冲击传导已在**前轮 R2/F1–F2** 测过。本轮不重复、不夸大。

## 5. 伪影体检（正向结果才需要；本轮无正向扣成本结果）

最大毛边 0.213 bp < 成本 ⇒ 未产生「扣成本还赚」的结果，故伪影体检表不适用。
仍需记录两条**结构性观察**：
1. A2 延续与反转毛边**互为镜像**（+0.213 / −0.213 bp）⇒ 是噪声镜像，不是可交易方向。
2. `exec_mean` 在所有假设上**更负**（如 A2 反转 exec_mean 仅 +0.032 bp，MID 为 +0.213 bp）——
   说明「用 ask 进 / bid 出」的过价差把本已微弱的毛边进一步吃掉。

## 6. 数据/方法学副作用审计

- **未改**：V1/V2 代码、配置、scheduler、MT5、账户、broker、ledger；V3 决策/风控/执行/账本/成本模型/prompt/阈值。
- **只读说明**：研究脚本只读快照目录；实时流后续追加不影响结论（快照不可变 + 逐文件 SHA256 校验）。
- **防未来函数**：特征全部因果（trailing 窗口 + 因果分位网格，仅用 T 之前数据）；分段（gap>60s）内做前向查找，跨段样本计 `HORIZON_CENSORED` 并排除。
- **时间戳单位**：`ts_utc` = `datetime64[ms, UTC]`，显式换算为 ms，未推断。
- **重复样本**：事件以 onset（连续区段首 tick）定义，天然低重叠；并在每个期限报 `effective_n`（贪心非重叠计数），不用原始事件数充当功效。

## 7. 子区间审计（item 9）

同一批冻结事件，按**不重叠子区间**拆分重报（未改阈值、未择优）：

**(a) 按交易时段（UTC 小时）**

| 假设 | ASIA 00-07Z | LONDON 07-12Z | NY 12-21Z |
|---|---|---|---|
| A1_CONT / A1_REV @5000ms | −0.032 / +0.032 | −0.034 / +0.034 | −0.056 / +0.056 |
| A2_CONT / A2_REV @5000ms | −0.098 / +0.098 | −0.040 / +0.040 | **−0.341 / +0.341** |
| C1_MR @5000ms | +0.028 | +0.017 | +0.048 |
| C2_CONT @5000ms | −0.026 | −0.012 | −0.020 |

**(b) 按流动性三分位（trailing 价差 TIGHT / MID / WIDE）**

| 假设 | TIGHT | MID | WIDE |
|---|---|---|---|
| A2_REV @5000ms | +0.218 | +0.174 | +0.234 |
| C1_MR @1000ms | **−0.030** | +0.009 | +0.018 |
| A1_CONT @5000ms | −0.032 | −0.046 | −0.046 |
| C2_CONT @5000ms | −0.019 | −0.021 | −0.019 |

**判读**：
1. **没有任何子区间达到成本锚**。全表最大子区间 = A2_REV 的 NY 时段 5s = **+0.341 bp**，仍是 0.914 bp 的 **37%**；扣 1x 成本后 −0.573 bp。没有「某个时段/某个流动性区间偷偷赚钱」的 pocket。
2. **C1 存在符号不稳定**：宽价差（MID/WIDE）为正、**紧价差（TIGHT）为负**（−0.030 bp）。这说明 C1 那点微弱「反转」与流动性状态绑定、不稳健，进一步支持不升级。
3. A2_REV 在三个流动性区间都约 +0.2 bp（+0.218/+0.174/+0.234）——**方向上一致但量级恒定地低于成本**，符合「单笔噪声镜像」而非可交易传导。

## 8. GPU 使用情况（item 12）

- **本轮未使用 GPU**：阶段2 R1 的特征计算/事件统计用 numpy（CPU）；7,285,000 行 × 3 列的中间数组约 200 MB，CPU 足够，用 GPU 无收益。
- GPU 可用性（阶段1 已实测，未变）：`NVIDIA RTX A2000 Laptop GPU` / CUDA 12.6 / torch 2.14.0+cu126 / VRAM 4095.6 MiB；分块 + OOM fallback 测试 PASS。
- **给项 12 的诚实答复：本阶段 GPU = NOT_USED（非失败）**；若后续进入大参数扫描/深度模型训练再启用，届时必须复跑 OOM fallback 证明。

## 9. 终态

```
PHASE2_R1_VERDICT = NO_VALIDATED_EDGE (COST_INSUFFICIENT)
- 可测假设 6/6 全部止于 COST_INSUFFICIENT；CANDIDATE = 0
- 未测族 B / D = NOT_TESTABLE（数据/覆盖），E = LIMITED —— 不计入失败，也不报「无 alpha」
- 需要多少数据 / 独立复现要多久：见 statistical-power-closure 口径（本报告的 eff_n 已按人群分别给出）
```
