# V3 · Alpha Sweep R1 — 大规模机制级扫描（XAUUSD 高频）

- 任务：`V3-ALPHA-SWEEP-R1`｜协议评估前冻结：`registry_hash_sha256 = 45598674ab8645a12cf71b18629fcb6d4f3796285c6074cb1746258d9433460f`
- 结果：`results_alpha_sweep_r1.json`（`sha256 = 6a5092b178f08a259e78023e117a14e651fb07f4f37c300c61114bf05a37ab7f`）
- 复现：`freeze_protocol.py` → `run_sweep_r1.py` → `finalize_sweep.py`
- **边界**：`ORDER_SEND=0`｜`LIVE=NO`｜未进执行｜未做 demo/live shadow｜未读 V1/V2 作输入｜未改 V1/V2｜未用历史盈利｜无前视/未来函数｜未删不利样本｜子样本仅作稳健性审计
- **本轮 24 个假设全部重新预注册**；未重打包已关闭的 F2b；D-R1/E-R1/F-R1 的失败结果**未**被当作样本或标签

## 0. 数据（DATA_REGISTRY）

| 语料 | 来源 | 规模 |
|---|---|---|
| **TICK** | `V3-SNAP-20260922T025312Z` | 36 文件 / **7,285,000 ticks** / 1,055 段 / 2026-08-04→09-22 / ms·UTC / **SHA256 36/36 MATCH**；`volume` 恒为 0 ⇒ 一切流量特征为报价口径 `_PROXY` |
| **BAR** | 由 TICK 派生 | **47,963 根 1m bar** |
| **EVENT** | `V3-SNAP-PIT2-20261001T131500Z` + 冻结日历 vintage | 1,712,560 ticks / 2026-09-21→10-01；vintage `JIN10_CALENDAR_20261001T130733Z.json` 283 事件（2026-09-28→10-03）；**落在 tick 窗口内 75 条** |

**成本模型**：`REAL_RT_COST_BP = 0.914`（spread 0.18 + commission 0.22 USD/RT），压力 0/1/2/3×。

## 1. 前置校验（合成，无市场数据）

| 特征 | 合成 std | 区间 | 结果 |
|---|---|---|---|
| TI | 0.9939 | [0.85, 1.15] | **PASS** |
| z100 | 0.9929 | [0.85, 1.15] | **PASS** |
| z500 | 1.0042 | [0.85, 1.15] | **PASS** |
| z5 | 1.0203 | [0.85, 1.15] | **PASS** |
| z1 | 1.0578 | [0.85, 1.15] | **PASS** |

⇒ **零 `INVALID_IMPLEMENTATION` 来自前置校验**。

## 2. 全量表（24 个基础假设；`__MIRROR` 不独立）

| ID | 族 | 语料 | 最佳期限 | n | eff_n | 毛边 bp | 1×成本后 | IS | OOS | p | 95% CI | 阶梯 | 归类 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T1_TICK_IMBALANCE | F1 | TICK | 250ms | 41,455 | 41,441 | −0.031 | −0.945 | −0.030 | −0.033 | 0.002 | [−0.04,−0.02] | COST_INSUFFICIENT | COST_INSUFFICIENT |
| T2_PRESSURE_PERSIST | F1 | TICK | 100ms | 41 | 41 | +0.046 | −0.868 | −0.012 | +0.128 | 0.638 | [−0.13, 0.23] | COST_INSUFFICIENT | COST_INSUFFICIENT |
| T3_LIQUIDITY_SHOCK | F1 | TICK | 5s | 5,094 | 2,687 | **+0.212** | −0.702 | +0.185 | +0.281 | **0.0005** | [0.06, 0.36] | COST_INSUFFICIENT | COST_INSUFFICIENT |
| T4_SPREAD_STRESS | F1 | TICK | 250ms | 2,918 | 2,745 | +0.123 | −0.791 | +0.185 | +0.018 | 0.005 | [0.00, 0.25] | COST_INSUFFICIENT | COST_INSUFFICIENT |
| T5_MICRO_REVERSAL | F1 | TICK | 5s | 12,553 | 6,872 | **+0.210** | −0.704 | +0.207 | +0.217 | **0.0006** | [0.12, 0.30] | COST_INSUFFICIENT | COST_INSUFFICIENT |
| P1_IMPULSE | F2 | BAR | 60m | 2,323 | 485 | +0.854 | −0.060 | +1.848 | −1.522 | 0.187 | [−1.54, 3.28] | COST_INSUFFICIENT | COST_INSUFFICIENT |
| P2_ABNORMAL_REVERSAL | F2 | BAR | 1m | 801 | 788 | +0.426 | −0.488 | +0.475 | +0.301 | 0.064 | [−0.12, 0.83] | COST_INSUFFICIENT | COST_INSUFFICIENT |
| **P3_VOL_EXPANSION_DIR** | F2 | BAR | **60m** | 2,644 | 545 | **+1.365** | **+0.451** | +1.678 | +0.678 | **0.026** | [0.16, 2.52] | EDGE_UNCERTAIN | **EDGE_UNCERTAIN** |
| P4_BREAKOUT | F2 | BAR | 60m | 5,396 | 566 | +1.272 | +0.358 | +2.059 | −0.835 | 0.001 | [−1.68, 4.22] | EDGE_UNCERTAIN | EDGE_UNCERTAIN |
| P5_FAILED_BREAKOUT | F2 | BAR | 60m | 8,463 | 6,187 | −0.113 | −1.027 | −0.100 | −0.146 | 0.006 | [−0.20,−0.05] | COST_INSUFFICIENT | COST_INSUFFICIENT |
| P6_RANGE_COMPRESSION | F2 | BAR | 1m | 2,322 | 2,322 | (非方向) lift **−0.063** | — | — | — | — | — | NON_DIRECTIONAL | NON_DIRECTIONAL |
| X1_SCALE_AGREEMENT | F3 | BAR | 60m | 1,771 | 432 | +1.287 | +0.373 | +2.689 | −2.057 | 0.093 | [−1.26, 3.71] | EDGE_UNCERTAIN | EDGE_UNCERTAIN |
| X2_SCALE_DISAGREEMENT | F3 | BAR | 5m | 581 | 337 | +0.536 | −0.378 | +0.452 | +0.732 | 0.101 | [−0.46, 1.55] | COST_INSUFFICIENT | COST_INSUFFICIENT |
| **X3_HTF_REGIME_COND** | F3 | BAR | **60m** | 945 | 271 | **+4.261** | **+3.347** | +5.408 | +1.123 | **0.0005** | [0.32, 7.89] | **EXECUTION_UNREALISTIC** | EDGE_UNCERTAIN |
| S1..S5 (5 个) | F4 | BAR | — | — | — | — | — | — | — | — | — | — | **INVALID_IMPLEMENTATION** |
| E1_EVENT_X_MICRO | F5 | EVENT | 5m | 38 | 37 | +1.650 | +0.736 | −0.043 | +5.320 | 0.140 | [−0.30, 3.79] | EDGE_UNCERTAIN | EDGE_UNCERTAIN |
| E2_EVENT_X_VOL | F5 | EVENT | 5m | 48 | 46 | +1.213 | +0.299 | +0.747 | +1.866 | 0.436 | [−1.11, 4.20] | EDGE_UNCERTAIN | EDGE_UNCERTAIN |
| E3_EVENT_X_SPREAD | F5 | EVENT | — | — | — | — | — | — | — | — | — | — | **DATA_BLOCKED** |
| E4_POST_EVENT_CONT | F5 | EVENT | 5m | 48 | 46 | +1.434 | +0.520 | +0.479 | +2.770 | 0.092 | [−0.22, 3.07] | EDGE_UNCERTAIN | EDGE_UNCERTAIN |
| E5_POST_EVENT_FADE | F5 | EVENT | 1m | 50 | 50 | −0.200 | −1.114 | +0.567 | −1.258 | 0.824 | [−1.82, 1.04] | COST_INSUFFICIENT | COST_INSUFFICIENT |

**镜像**：全部 23 条 `__MIRROR` 已计算并保存；多数为 `COST_INSUFFICIENT`。镜像**不作为独立证据**。

## 3. 分类计数（基础假设）

| 归类 | 数量 |
|---|---|
| **VALIDATED_EDGE** | **0** |
| EDGE_UNCERTAIN | 7 |
| COST_INSUFFICIENT | 10 |
| NON_DIRECTIONAL | 1 |
| DATA_BLOCKED | 1 |
| INVALID_IMPLEMENTATION | 5 |
| **合计** | **24** |

**有效假设数 = 18**（= 24 − 1 DATA_BLOCKED − 5 INVALID_IMPLEMENTATION）

## 4. 多重检验（全局 BH-FDR, α=0.05）

| 项 | 值 |
|---|---|
| 检验总数 | **208** |
| BH 存活 | **44** |
| 说明 | "存活 FDR" ≠ 有 edge。存活者中绝大多数毛边仍 < 0.914 bp 成本（如 T3/T4/T5 家族），属于**统计显著但经济不可见** |

## 5. 关键读数与诚实修正

### 5.1 最强但**不可采信**：`X3_HTF_REGIME_COND @60m`
毛边 **+4.261 bp**、1×/2×/3× 成本后 **+3.347 / +2.433 / +1.519 bp**（**挺过 3× 成本**）、p=0.0005、CI [0.32, 7.89] 不含 0、IS +5.408、OOS +1.123 —— 单看数字是全场最强。
**但它排除在证据之外，原因有两条**：
1. **它是 LONG-ONLY**（`|z5|≥2 且 ch60>0 且 ret5>0`，方向恒为 +1）。在一个黄金总体上行的样本里，**做多信号无法与 beta 敞口区分**；其镜像（做空）为 `COST_INSUFFICIENT`。
2. 冻结阶梯判它 **`EXECUTION_UNREALISTIC`**（`std 32.76 bp > 5×|4.261|`），即收益离散度大到不可执行。

### 5.2 最强且**未被 long-only 混淆**：`P3_VOL_EXPANSION_DIR @60m`
毛边 **+1.365 bp**、1× 后 **+0.451**、permutation **p=0.026**、bootstrap CI **[0.16, 2.52] 不含 0**、IS **+1.678** 与 OOS **+0.678 同为正**。
**唯一失败点：2× 成本压力**（net2x = **−0.463 bp**）。⇒ 判 `EDGE_UNCERTAIN`，**不构成已验证 edge**。

### 5.3 统计最干净的效应，全部淹没在成本里
`T3_LIQUIDITY_SHOCK`（+0.212 bp，p=0.0005，CI[0.06,0.36]）、`T5_MICRO_REVERSAL`（+0.210 bp，p=0.0006，CI[0.12,0.30]）、`T4_SPREAD_STRESS`（+0.123 bp，p=0.005）、`T1`（p=0.002 但**方向为负**）。
⇒ 这些是**真信号**，但量级只有往返成本的 **10%–23%**。

### 5.4 非方向性发现：压缩**不**导致扩张
`P6_RANGE_COMPRESSION`：压缩起点后的前向 |位移| 在**每个期限都低于**基线（lift **−0.063 / −0.022 / …**）⇒ **"压缩后必扩张"在本样本不成立**（反方向）。

## 6. 失败归类（必须修正的两处——我自己的实现缺陷）

| 项 | 原判 | **修正为** | 原因 |
|---|---|---|---|
| `S1..S5`（5 个）+ 镜像 | EDGE_UNCERTAIN | **INVALID_IMPLEMENTATION** | 预注册的**逐桶分解返回空字典**（meta 查表用 bar 收盘 ts，而求值器传入的是入场 tick ts），**"状态条件化"这个检验根本没被交付**；其 pooled 数字只是 `P1_IMPULSE` 的副本 |
| `P6_RANGE_COMPRESSION` | COST_INSUFFICIENT | **NON_DIRECTIONAL** | 它是唯一非方向性假设，方向性阶梯不适用 |
| `E3_EVENT_X_SPREAD` | — | **DATA_BLOCKED** | 宽价差事件不足 |
| F5 其余（E1/E2/E4/E5） | EDGE_UNCERTAIN | 保留，但**强标欠功效** | 仅 **75** 条日历事件落在 tick 窗口内（vintage 283 条跨 09-28→10-03，快照止于 10-01 12:54Z）；n=48–50 |

## 7. 最终判定

```
STATUS = NO_VALIDATED_EDGE
```
- **0 个**假设满足 `VALIDATED_EDGE` 的全部要求（成本后为正 + IS/OOS 同正 + p<0.05 + CI 不含 0 + eff_n≥30 + 不依赖单一桶 + 挺过 2× + 通过全局 BH-FDR）。
- 最强项 `X3` 挺过 3× 成本但**因 long-only 与执行离散度被排除**；次强项 `P3` **倒在 2× 成本**。
- 统计最干净的 tick 级效应（p≤0.005、CI 不含 0）**量级只有 0.09–0.21 bp**，是成本的 10%–23%。

## 8. 下一步建议

1. **不要在这批机制上调参**：24 个假设、5 个族、208 个检验，全局 FDR 存活 44 个但**没有一个能同时过成本与稳健性**。这是**成本墙**，不是参数问题。
2. **唯一值得独立复检的是 `P3_VOL_EXPANSION_DIR`**：它过了 1× 成本、置换、自助 CI、IS/OOS 双正，只倒在 2×。建议**另立冻结协议**在**更长样本**上预注册复检（而不是在本地调阈值）。
3. **`X3` 必须用 long-only 对照证伪**：在同一样本上跑「无条件做多」的基准；若基准同样盈利，则 X3 是 beta 不是 alpha。
4. **补齐两个数据缺口**：① 装一次 `volume`（真 OFI 不可得 ⇒ F1 永远只是代理）；② 让事件语料与 tick 窗口对得上（目前只有 75 条可用）。
5. **修掉 S 族的实现缺陷**后，若仍要做状态条件化，应作为**新的冻结协议**重跑。
