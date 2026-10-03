# 04_DATA_BLINDSPOT — 数据层级与 TOP1 盲点（2026-09-06）
## 数据层级(信息价值↑)
OHLC/M1/M5 < tick(bid/ask) < spread < volume(毛量) < 事件/日历 < 期权代理(GVZ) < 跨资产 < **signed flow/aggressor** < L2/深度 < 队列 < 执行反馈(fill/拒单/排队)
## TOP 1 DATA BLIND SPOT
**signed/aggressor order flow（主动成交方向流）——不是 L2。**
理由:
1. 它是"谁在推动"的唯一直接观测; 我们全部数据(DUKA/FXTM)只有 quote updates 与毛量, volume≠signed flow(已立纪律), 因此过去 12 轮实验**从未直接观测过信息是否来自买方还是卖方**;
2. 它决定 adverse selection/flow toxicity——执行层唯一可能藏"每日可重复"钱的机制;
3. 一旦拥有它, L2 深度/队列只是锦上添花(很多结论可由 T&S+深度重构近似), 反之不成立;
4. 获得路径: GC T&S(CME 经 Databento, $25 门)或 ECN/真 broker 的 tick-by-tick 成交流(免费 demo 也可能给 trades) —— 成本低于曲面, 信息价值高于曲面(对本目标)。
## 说明
L2 深度列第二: 对方向/流推断价值高, 但无 signed trades 时深度动态难解读(闪烁污染, HERMES-10)。
执行反馈列最高: 因为"能不能成交/以什么价成交"是 EV 的最终裁决者; 但它不是信息盲点而是工程缺口(免费可解)。
