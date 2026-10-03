# V3 Round 3 日线跨市场机制研究报告

`ts_utc = 2026-09-25T01:45:00.778530+00:00` · **`final_status = V3_ROUND3_COMPLETE_NO_CANDIDATE`**
`V3_FORWARD_READY = False` · `V3_STRATEGY_FORWARD = NOT_ENABLED` · `ORDER_SEND = 0`

```text
TIMEFRAME = DAILY（本轮硬限制：未使用任何 1m/5m/15m/30m 或盘中事件窗口）
GOLD_LEG  = GC_FUTURES_PROXY
GC=F (COMEX gold futures) is used as the gold leg because XAUUSD spot daily bars are not obtainable in a PIT-safe way (Yahoo XAUUSD=X/XAU=X -> 404; stooq throttled). The venue-correct FXTM sample is only ~26 daily bars (< 30). Transferability of any result to the FXTM spot execution venue is NOT established.
```

## 一、数据

| 序列 | 来源 | 覆盖 | 行数 | availability 规则 |
|---|---|---|---|---|
| GC（黄金腿） | YAHOO chart GC=F | 2024-09-24 → 2026-09-25 | 505 | 日线 bar D → D+1 00:00Z |
| DXY | YAHOO chart DX-Y.NYB | 2024-09-24 → 2026-09-25 | 504 | 同上 |
| VIX | YAHOO chart ^VIX | 2024-09-24 → 2026-09-24 | 503 | 同上 |
| UST10Y | US Treasury 官方日度收益率曲线 CSV（2024+2025+2026） | 2024-01-02 → 2026-09-24 | 683 | 同上 |

```text
并集日期数        : 692
missing_rate      : 0.207
dataset_hash      : a54d1fb9eba393303b1690d2ba8d1837de10a39c08d26d102fe57a1e82a61a86
registry_hash     : a0626d344a31bf4d06fe72d480da215878ebc4d74fc8a0aabd87b2538c233dac
timezone          : UTC (dates normalised to UTC; original series tz recorded per source)
每个源 hash/规则  : research/v3_strategy_round3/dataset_meta.json（source_facts）

XAUUSD 现货日线：不可获得 —— YAHOO XAUUSD=X / XAU=X → 404；stooq xauusd → 限流页（796B/3行）。
venue 正确的 FXTM 黄金日线样本 ≈ 26 个交易日（< 30），故【不能】用于日线机制检验。
=> 按任务书 §四 允许的变量集合，黄金腿改用 GC（COMEX 金期货）。这是**代理**，不是 FXTM 现货。
```

## 二、研究（新机制与淘汰）

| ID | 假设 | horizon | 机制类别 | 去重 |
|---|---|---|---|---|
| H24_DXY_INVERSE_STATE | a decisive DXY daily move is followed by an opposite-direction gold mo | 1 day | DXY_INVERSE | ADMIT |
| H25_UST_YIELD_STATE | a decisive daily change in the 10Y Treasury yield is followed by an op | 1 day | UST_STATE | ADMIT |
| H26_VIX_RISK_STATE | a decisive VIX jump is followed by a same-direction gold move (safe-ha | 1 day | VIX_STATE | ADMIT |
| H27_GC_XAUUSD_CONFIRMATION | a GC/XAUUSD divergence is resolved in favour of XAUUSD on the next day | 1 day | CROSS_CONFIRMATION | ADMIT |
| H28_DXY_UST_DOUBLE_STATE | when DXY and the 10Y yield move decisively in the SAME direction, gold | 1 day | DOUBLE_CONFIRM | ADMIT |
| H29_DXY_VIX_STRESS_COMBO | when DXY rises decisively AND VIX jumps decisively, gold rises the nex | 1 day | DOUBLE_STATE | ADMIT |
| H30_CROSS_MARKET_AGREEMENT | a three-variable macro agreement (DXY down, 10Y down, VIX up) is follo | 1 day | AGREEMENT_DIVERGENCE | ADMIT |
| H31_CROSS_MARKET_STATE_TRANSITION | a DXY state FLIP between t-1 and t (down->up or up->down) is followed  | 1 day | STATE_TRANSITION | ADMIT |

```text
Round 3 新机制 tested = 8
REJECT                = 1
INSUFFICIENT_SAMPLE   = 2（H27 数据阻塞 + H30 有效样本 13 < 30）
REJECT_DUPLICATE      = 0
EDGE_UNCERTAIN        = 5
CANDIDATE             = 0
```

**H21 / H22 / H23 未被改写**，仍为 `NOT_TESTABLE`（本轮未触碰其定义）。
H30 与 H21 的关系已显式声明：H30 是**新的日线假设、新 id、重新冻结**，不构成对 H21 的降级改写。

## 三、统计

| ID | bucket | n | eff n | 0x | 1x | 2x | 3x | walk-forward 3 折 | perm p | bootstrap CI95 | 判定 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H24_DXY_INVERSE_STATE | DXY_INVERSE | 203 | 203 | 5.44 | 4.526 | 3.612 | 2.698 | -11.126/9.592/20.244 | 0.20253 | [-14.004, 24.529] | EDGE_UNCERTAIN |
| H25_UST_YIELD_STATE | UST_STATE | 120 | 120 | 8.859 | 7.945 | 7.031 | 6.117 | -9.037/27.329/11.204 | 0.18188 | [-21.114, 37.743] | EDGE_UNCERTAIN |
| H26_VIX_RISK_STATE | VIX_STATE | 205 | 205 | 7.653 | 6.739 | 5.825 | 4.911 | -4.371/0.774/27.302 | 0.27515 | [-14.208, 26.382] | EDGE_UNCERTAIN |
| H27_GC_XAUUSD_CONFIRMATION | CROSS_CONFIRMATION | 0 | - | - | - | - | - | -/-/- | - | - | INSUFFICIENT_SAMPLE |
| H28_DXY_UST_DOUBLE_STATE | DOUBLE_CONFIRM | 56 | 56 | 34.572 | 33.658 | 32.744 | 31.83 | 3.389/20.215/86.273 | 0.84277 | [-4.822, 62.446] | EDGE_UNCERTAIN |
| H29_DXY_VIX_STRESS_COMBO | DOUBLE_STATE | 31 | 31 | -11.994 | -12.908 | -13.822 | -14.736 | 43.054/-74.585/-24.553 | 0.1006 | [-55.567, 26.053] | REJECT |
| H30_CROSS_MARKET_AGREEMENT | AGREEMENT_DIVERGENCE | 13 | 13 | 92.105 | 91.191 | 90.277 | 89.363 | 32.686/75.339/180.174 | 0.30713 | [-2.11, 126.959] | INSUFFICIENT_SAMPLE |
| H31_CROSS_MARKET_STATE_TRANSITION | STATE_TRANSITION | 45 | 45 | 7.115 | 6.201 | 5.287 | 4.373 | 8.631/7.407/1.957 | 0.31446 | [-20.692, 40.421] | EDGE_UNCERTAIN |

```text
成本锚            : 0.914 bp 往返；压力 0x/1x/2x/3x 全部记录（gross/net/cost impact）
样本时间序        : 全部按时间序分折 0-40% / 40-70% / 70-100%（无 shuffle）
重叠/自相关       : 1 日持有、逐日信号；overlap_ratio 已记录（见 round3_results.json）
bootstrap         : block bootstrap（block=5, 2000 次）→ CI95
permutation       : 条件样本 vs 无条件池的置换检验（1500 次）
regime            : vol 三分位 + 星期（样本 < 30 的分层标记 insufficient）
FDR               : BH q=0.05；Round3 进入 FDR 阶段 2 个，阳性 0 个
多重检验累计      : Round1 12 + Round2 11 + Round3 8 = 31（未因换轮次而遗忘）
```

### 必须写明的两点

**1) 无条件基线（决定性）**
```text
无条件 1 日 GC 均值 = 11.4198 bp
多数假设的条件均值为 +4.5 ~ +7.9 bp —— 低于无条件均值。
=> 它们的"正净收益"主要来自黄金在本样本期的整体上行漂移，而不是跨市场条件本身。
   这正是"不要因为 net > 0 就定义 Candidate"（§十九）的实例。
```

**2) 唯一"看起来像"的方向（但按纪律不算 Candidate）**
```text
H30 三变量宏观一致态（DXY↓ + 10Y↓ + VIX↑）：n=13, 均值 +91.2 bp, 三折 +32.7/+75.3/+180.2
   → 有效样本 13 < 30，按 §十二 必须判 INSUFFICIENT_SAMPLE。
   记录为【未来可优先验证的方向】，但在本轮【不是】Candidate，也不得据此进入任何后置流程。
反例（说明本轮没有过拟合）：H29（DXY↑+VIX↑）同样是小样本组合，均值 -12.9 bp，三折 +43/-75/-25 → REJECT。
```

## 四、安全

```text
未来数据泄漏    : 无。信号只用 bar t 与 t-1；成交在 close(t+1) → 平仓 close(t+2)；
                  日线 bar 一律 D+1 00:00Z 才可用；未使用 unfinished bar / future bar / future revision
V1/V2 隔离      : V1 代码未改 · V2 代码未改 · 未 import trader_v1 / trader_v2 ·
                  未读取 V1/V2 runtime state 作为研究数据
执行层 untouched: v3_adapter.py 未改 · calibration_pilot.py 未改 · calibration ledger 未改 · sequence 未改
Risk Layer      : strategy/risk.py 未改（本轮未发现工程错误；若发现本应 HARD STOP 并先报告）
ORDER_SEND      : 0（本任务全程未下单、未进 Shadow/Forward/Demo/Live）
Forward         : V3_FORWARD_READY = FALSE · V3_STRATEGY_FORWARD = NOT_ENABLED（即使有 Candidate 也不得自动开启）
```

## 五、最终状态（§二十六）

```text
V3_ROUND3_COMPLETE_NO_CANDIDATE
```

## 六、结论（§二十八）

> 在当前中国内网可获得、当前 PIT 条件与当前样本范围内，**日线跨市场信息未产出经过成本、OOS、Regime、FDR 检验后仍然成立的 XAUUSD 可交易机制**。
> 更精确地说：本轮观察到的"正净收益"主要可由黄金的无条件上行漂移解释；条件本身没有提供超越基线的证据。
> **0 Candidate 是有效研究结果。** 不是 Alpha 认证，不是 Forward 授权，不是 Live 授权。
> 按 §二十七：**不自动开启 Round 4**。
