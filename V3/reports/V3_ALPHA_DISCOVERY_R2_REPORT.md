# V3 高频 Alpha Discovery R2 — 事件冲击 × 跨市场信息滞后

`ts_utc = 2026-09-25T10:30:10.099612+00:00` · 任务 `V3_HIGH_FREQUENCY_ALPHA_DISCOVERY_R2_EVENT_CROSSMARKET`

**最终状态：`COMPLETE_NO_CANDIDATE`**

## 数据

```text
XAUUSD：HistData M1 BID · 607,992 根 · 2025-01-01 → 2026-09-18 21:58 UTC（EST 固定 +5h=UTC）
Jin10 ：list_calendar 仅 2026-09-21 07:01 → 09-26 01:00（158 事件）· search_flash 最早 09-24 · search_news 最早 09-23
DXY   ：Yahoo DX-Y.NYB 5m · 覆盖窗内 4,711 行 · 2026-08-25 10:25 → 09-18 20:55 UTC
UST10Y：Yahoo ^TNX 5m（收益指数代理，非官方 CMT 收益率）· 覆盖窗内 1,440 行 · 2026-08-25 12:20 → 09-18 18:55
VIX   ：Yahoo ^VIX 5m · 覆盖窗内 2,870 行 · 2026-08-25 10:25 → 09-18 20:10
公共 5m 网格（三源+黄金取交集）：1,440 行 · 窗口 2026-08-25 12:20 → 2026-09-18 18:55 UTC
各源独立成列，未拼接、未合成 DXY；原始 JSON 已落盘并记 sha256
```

## PIT

```text
可用事件：0（与 XAUUSD 窗口无重叠）
可用跨市场数据：DXY / VIX / ^TNX 的【5m】在重叠窗内可用（1m 不可用：Yahoo 1m 仅最近 5 天，从 09-21 起）
NOT_TESTABLE：E 事件族（§29 STOP_EVENT_BRANCH）· F 的 1 分钟粒度
SEMANTICS_BLOCKED：无（XAUUSD 走 ±1 bar 敏感性；外部源为 epoch UTC，PIT 清晰）
```

## 机制

```text
事件机制：E 族未测试（NOT_TESTABLE，无重叠，未凑数据）
跨市场机制：8 个 F 族，测试前冻结 registry_hash=e0178021b111）
   F1/F2 DXY 冲击延续/反转 · F3/F4 VIX 冲击延续/反转 · F5/F6 TNX 冲击延续/反转
   F7/F8 DXY 冲击后 XAUUSD 未调整的补涨/补跌（§36 核心机制）
   ★ 方向未预设：每个源的延续与反转都作为独立冻结假设各自测试（§13）
总测试数：8
```

## 结果

```json
{
 "INSUFFICIENT_SAMPLE": 6,
 "EDGE_UNCERTAIN": 1,
 "COST_INSUFFICIENT": 1
}
```

| 机制 | raw | uniq | eff | gross | net1x | net2x | perm p | 状态 |
|---|---|---|---|---|---|---|---|---|
| F1_DXY_SHOCK_CONT | 29 | 29 | 29 | -0.7709 | -1.6849 | -2.5989 | 0.6353 | **INSUFFICIENT_SAMPLE** |
| F2_DXY_SHOCK_REV | 29 | 29 | 29 | 0.7709 | -0.1431 | -1.0571 | 0.62781 | **INSUFFICIENT_SAMPLE** |
| F3_VIX_SHOCK_CONT | 26 | 26 | 26 | -8.9711 | -9.8851 | -10.7991 | 0.84763 | **INSUFFICIENT_SAMPLE** |
| F4_VIX_SHOCK_REV | 26 | 26 | 26 | 8.9711 | 8.0571 | 7.1431 | 0.67777 | **INSUFFICIENT_SAMPLE** |
| F5_TNX_SHOCK_CONT | 38 | 38 | 38 | 2.2872 | 1.3732 | 0.4592 | 0.85512 | **EDGE_UNCERTAIN** |
| F6_TNX_SHOCK_REV | 38 | 38 | 38 | -2.2872 | -3.2012 | -4.1152 | 0.14321 | **COST_INSUFFICIENT** |
| F7_DXY_LAG_CATCHUP_CONT | 2 | 2 | 2 | 1.6972 | 0.7832 | -0.1308 | None | **INSUFFICIENT_SAMPLE** |
| F8_DXY_LAG_CATCHUP_REV | 2 | 2 | 2 | -1.6972 | -2.6112 | -3.5252 | None | **INSUFFICIENT_SAMPLE** |

## 成本

```text
0x/1x/2x/3x 逐机制见 crossmarket_results.json 的 cost_stress；摘要：
  F5_TNX_SHOCK_CONT 是唯一 eff≥30 的机制：0x +2.29 → 1x +1.37 → 2x +0.46 → 3x −0.46
  F6_TNX_SHOCK_REV 被标记 COST_INSUFFICIENT（gross −2.29 < 0.914bp 门槛）
  其余 6 个因 eff<30 归档 INSUFFICIENT_SAMPLE（成本记录仍完整）
```

## 频率

```json
[
 {
  "hypothesis_id": "F1_DXY_SHOCK_CONT",
  "signals_per_day": 1.195,
  "signals_per_hour": 0.0498,
  "net_edge_per_trade_bp": -1.6849,
  "net_edge_per_hour_bp": -0.0839,
  "avg_holding_time_min": 15,
  "status": "INSUFFICIENT_SAMPLE"
 },
 {
  "hypothesis_id": "F2_DXY_SHOCK_REV",
  "signals_per_day": 1.195,
  "signals_per_hour": 0.0498,
  "net_edge_per_trade_bp": -0.1431,
  "net_edge_per_hour_bp": -0.0071,
  "avg_holding_time_min": 15,
  "status": "INSUFFICIENT_SAMPLE"
 },
 {
  "hypothesis_id": "F3_VIX_SHOCK_CONT",
  "signals_per_day": 1.071,
  "signals_per_hour": 0.0446,
  "net_edge_per_trade_bp": -9.8851,
  "net_edge_per_hour_bp": -0.4412,
  "avg_holding_time_min": 15,
  "status": "INSUFFICIENT_SAMPLE"
 },
 {
  "hypothesis_id": "F4_VIX_SHOCK_REV",
  "signals_per_day": 1.071,
  "signals_per_hour": 0.0446,
  "net_edge_per_trade_bp": 8.0571,
  "net_edge_per_hour_bp": 0.3596,
  "avg_holding_time_min": 15,
  "status": "INSUFFICIENT_SAMPLE"
 },
 {
  "hypothesis_id": "F5_TNX_SHOCK_CONT",
  "signals_per_day": 1.565,
  "signals_per_hour": 0.0652,
  "net_edge_per_trade_bp": 1.3732,
  "net_edge_per_hour_bp": 0.0896,
  "avg_holding_time_min": 15,
  "status": "EDGE_UNCERTAIN"
 },
 {
  "hypothesis_id": "F6_TNX_SHOCK_REV",
  "signals_per_day": 1.565,
  "signals_per_hour": 0.0652,
  "net_edge_per_trade_bp": -3.2012,
  "net_edge_per_hour_bp": -0.2088,
  "avg_holding_time_min": 15,
  "status": "COST_INSUFFICIENT"
 },
 {
  "hypothesis_id": "F7_DXY_LAG_CATCHUP_CONT",
  "signals_per_day": 0.082,
  "signals_per_hour": 0.0034,
  "net_edge_per_trade_bp": 0.7832,
  "net_edge_per_hour_bp": 0.0027,
  "avg_holding_time_min": 15,
  "status": "INSUFFICIENT_SAMPLE"
 },
 {
  "hypothesis_id": "F8_DXY_LAG_CATCHUP_REV",
  "signals_per_day": 0.082,
  "signals_per_hour": 0.0034,
  "net_edge_per_trade_bp": -2.6112,
  "net_edge_per_hour_bp": -0.009,
  "avg_holding_time_min": 15,
  "status": "INSUFFICIENT_SAMPLE"
 }
]
```

## 稳定性

```text
WF：仅 F5 具备可切分样本（38）；其 fold 结果见 JSON，未通过一致性要求 → EDGE_UNCERTAIN
Block：全部 block bootstrap CI 见 JSON（多数跨 0）
Permutation：p ∈ [0.14, 0.86] → 全部不显著；F5 p=0.855（观察值比多数随机抽样更差）
FDR：BH q=0.05 → 阳性 0
```

## 执行敏感性（0m/1m/2m/3m/5m 入场延迟）

```json
{
 "F1_DXY_SHOCK_CONT": {
  "0m": {
   "n": 29,
   "net_edge_bp": -1.6849
  },
  "1m": {
   "n": 29,
   "net_edge_bp": -2.7203
  },
  "2m": {
   "n": 29,
   "net_edge_bp": -2.8604
  },
  "3m": {
   "n": 29,
   "net_edge_bp": -3.9146
  },
  "5m": {
   "n": 29,
   "net_edge_bp": -5.9979
  }
 },
 "F2_DXY_SHOCK_REV": {
  "0m": {
   "n": 29,
   "net_edge_bp": -0.1431
  },
  "1m": {
   "n": 29,
   "net_edge_bp": 0.8923
  },
  "2m": {
   "n": 29,
   "net_edge_bp": 1.0324
  },
  "3m": {
   "n": 29,
   "net_edge_bp": 2.0866
  },
  "5m": {
   "n": 29,
   "net_edge_bp": 4.1699
  }
 },
 "F3_VIX_SHOCK_CONT": {
  "0m": {
   "n": 26,
   "net_edge_bp": -9.8851
  },
  "1m": {
   "n": 26,
   "net_edge_bp": -13.9206
  },
  "2m": {
   "n": 26,
   "net_edge_bp": -13.3428
  },
  "3m": {
   "n": 26,
   "net_edge_bp": -11.7145
  },
  "5m": {
   "n": 26,
   "net_edge_bp": -14.3588
  }
 },
 "F4_VIX_SHOCK_REV": {
  "0m": {
   "n": 26,
   "net_edge_bp": 8.0571
  },
  "1m": {
   "n": 26,
   "net_edge_bp": 12.0926
  },
  "2m": {
   "n": 26,
   "net_edge_bp": 11.5148
  },
  "3m": {
   "n": 26,
   "net_edge_bp": 9.8865
  },
  "5m": {
   "n": 26,
   "net_edge_bp": 12.5308
  }
 },
 "F5_TNX_SHOCK_CONT": {
  "0m": {
   "n": 38,
   "net_edge_bp": 1.3732
  },
  "1m": {
   "n": 38,
   "net_edge_bp": 1.4439
  },
  "2m": {
   "n": 38,
   "net_edge_bp": 0.8581
  },
  "3m": {
   "n": 38,
   "net_edge_bp": 0.719
  },
  "5m": {
   "n": 38,
   "net_edge_bp": -3.5763
  }
 },
 "F6_TNX_SHOCK_REV": {
  "0m": {
   "n": 38,
   "net_edge_bp": -3.2012
  },
  "1m": {
   "n": 38,
   "net_edge_bp": -3.2719
  },
  "2m": {
   "n": 38,
   "net_edge_bp": -2.6861
  },
  "3m": {
   "n": 38,
   "net_edge_bp": -2.547
  },
  "5m": {
   "n": 38,
   "net_edge_bp": 1.7483
  }
 },
 "F7_DXY_LAG_CATCHUP_CONT": {
  "0m": {
   "n": 2,
   "net_edge_bp": 0.7832
  },
  "1m": {
   "n": 2,
   "net_edge_bp": -1.6169
  },
  "2m": {
   "n": 2,
   "net_edge_bp": -4.711
  },
  "3m": {
   "n": 2,
   "net_edge_bp": -6.4125
  },
  "5m": {
   "n": 2,
   "net_edge_bp": -9.4946
  }
 },
 "F8_DXY_LAG_CATCHUP_REV": {
  "0m": {
   "n": 2,
   "net_edge_bp": -2.6112
  },
  "1m": {
   "n": 2,
   "net_edge_bp": -0.2111
  },
  "2m": {
   "n": 2,
   "net_edge_bp": 2.883
  },
  "3m": {
   "n": 2,
   "net_edge_bp": 4.5845
  },
  "5m": {
   "n": 2,
   "net_edge_bp": 7.6666
  }
 }
}
```

## 最重要的反证（§13/§24）

```text
① 【样本量是决定性约束】—— 冲击事件只有 26–38 个（约占样本 1.8%–2.6%），8 个机制中 6 个 eff<30，
   因此本轮【不能】证明跨市场滞后不存在，只能说【在这个 24 天窗口里样本不足】(与 R1 的 608k 根完全不同)。
② 【最像样的数字经不起检验】—— F4_VIX_SHOCK_REV 毛边 +8.97bp / 2x 后 +7.14bp 看似可观，
   但 eff=26<30 且 perm p=0.678 → 按 §22 门槛直接归档 INSUFFICIENT_SAMPLE，不得因数字好看而升级。
③ 【§36 核心机制几乎不触发】—— F7/F8（外部已动、黄金未调整）在此窗口【仅 2 次】→ 高频信息滞后套利的前提
   在样本上得不到支持（不是「不存在」，而是「频率极低」，需要在更长窗口复检）。
④ 【方向性无稳定证据】—— 每个源的延续与反转互为镜像（gross 正负对称），说明毛边基本来自单笔噪声而非系统性传导。
⑤ 【唯一 eff≥30 的 F5】perm p=0.855，成本后虽微正但无统计显著性 → EDGE_UNCERTAIN，非 Candidate。
```

## 问题 A / 问题 B 分别回答（§27）

```text
问题A（统计上是否存在关系？）：本窗口【无法判定】——样本不足，且现有信号 p 值全不显著。
问题B（是否足以覆盖成本并形成高频机会？）：【否】——唯一过成本的 F5 p=0.855；
                                     样本频率下 net_edge_per_hour 极小（见频率表）。
```

## 与 R1 的隔离（§28）

```text
未复用/未重新优化 A1…D2；本轮全部机制以【外部信息源触发】为条件，机制边界与 R1 纯价格机制不同。
未改阈值/未事后挑窗口；窗口 T+15m 与 z>=2.0 在测试前冻结。
```

## 安全与边界（§30/§31/§32）

```text
NO_PURCHASE · NO_PAYMENT · NO_NEW_ACCOUNT · ORDER_SEND=0 · V3_FORWARD=OFF · V3_SHADOW=OFF · V3_LIVE=OFF
未改 calibration / execution adapter / risk layer / MT5 / V1 / V2（见 _git_audit.json）
所有新代码仅落在 research/v3_alpha_discovery_r2/
```

## 最终状态（§34）

```text
COMPLETE_NO_CANDIDATE
附：E 事件族 = NOT_TESTABLE（无重叠）；F 跨市场族 = 样本受限，0 Candidate
```

## 下一步（不自动执行）

```text
若要让 F 族真正可判，需要【与 XAUUSD 长时间窗重叠的 5m/1m 外部数据】——
当前免凭据可得的跨市场盘中数据只有最近 1 个月，这是唯一瓶颈；需人工决定是否扩展数据来源。
```