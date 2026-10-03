# V3 XAU 重验证：H25 二十年延长窗口（授权下一步的第一次执行）

`ts_utc = 2026-09-25T08:21:16.095330+00:00`

**本轮状态：H25 已执行 → `REJECT`；其余黄金腿假设仍受阻（原因已定位并留证）**

```text
V3_ROUND3_COMPLETE_NO_CANDIDATE（保持）· V3_XAU_SPOT_CONDITIONAL（保持）
V3_FORWARD_READY = FALSE · V3_STRATEGY_FORWARD = NOT_ENABLED · V3_LIVE_ALLOWED = NO
ORDER_SEND = 0 · FORWARD = 0 · LIVE = 0 · 未新增假设 · 未改任何阈值
```

## 一、本轮做了什么

```text
目标：解决上次报告指出的真正瓶颈 —— 触发变量（DXY/VIX）覆盖只有 2 年，导致 20 年 XAU 数据无法在 20 年窗口上检验。
结果：DXY/VIX 的【长历史获取失败】（证据见第二节）；但 UST10Y 通过官方逐年 CSV 已有 20 年，因此 H25（UST→黄金）在延长窗口上是可检验的 → 已执行。
```

## 二、DXY/VIX 获取失败证据（有界尝试，未无限搜索）

```json
{
 "attempts": {
  "query2_yahoo_DXY": {
   "name": "DXY",
   "tag": "query2_yahoo",
   "ok": false,
   "rows": 0,
   "error": "HTTPError: HTTP Error 403: Forbidden"
  },
  "stooq_dx_f_DXY": {
   "name": "DXY",
   "tag": "stooq_dx_f",
   "ok": false,
   "rows": 3,
   "error": null,
   "http": 200
  },
  "query2_yahoo_VIX": {
   "name": "VIX",
   "tag": "query2_yahoo",
   "ok": false,
   "rows": 0,
   "error": "HTTPError: HTTP Error 403: Forbidden"
  },
  "stooq_vi_f_VIX": {
   "name": "VIX",
   "tag": "stooq_vi_f",
   "ok": false,
   "rows": 3,
   "error": null,
   "http": 200
  }
 },
 "final": {
  "EM_DXY_100.UDI": {
   "ok": true,
   "rows": 200,
   "kind": "eastmoney"
  },
  "EM_DXY_100.DINIW": {
   "ok": false,
   "rows": 0,
   "kind": "eastmoney"
  },
  "EM_VIX_100.VIX": {
   "ok": false,
   "rows": 0,
   "kind": "eastmoney"
  },
  "SINA_USDX": {
   "ok": false,
   "rows": 2,
   "kind": "csv"
  }
 }
}
```

```text
新浪 GlobalFuturesService：DXY 符号 'DX' 返回 13 行（2019-04-18~05-07，非目标序列）；'VIX' 返回 0 行；'USDX' 无
Yahoo（query1/query2）：range=1y/2y/5y/10y/max 全部 HTTP 403（本会话高频访问被限流）
stooq：dx.f / vi.f 均返回 798B/3 行（限流页）
东方财富：`100.UDI`（DXY）**返回 200 行可用日线**（受我请求的 lmt=200 限制）→ 这是一个【潜在可用】的 DXY 源，其历史跨度与质量尚待验证；`100.VIX` 返回 0 行 → VIX 仍不可得
=> 结论（据上表）：两年前可得的 Yahoo 路径本次全程 403；stooq 限流；新浪符号不匹配 —— **DXY 出现一条新的潜在路径（东方财富 100.UDI），VIX 仍无可用路径**。两个序列的【20 年】长历史目前仍不可得；且阻塞在触发变量，不是黄金数据。
```

## 三、H25 二十年重验证（已执行）

### 3.1 冻结定义（未改动）与样本计数

```json
{
 "ust10y_change_bp_threshold": 5.0,
 "direction": "inverse",
 "hold_days": 1,
 "entry": "close(t+1)",
 "exit": "close(t+2)"
}
```
```text
raw_rows     : xau=5186  ust10y=3935
aligned_rows : 3738   窗口 2006-09-25 → 2026-09-24（20 年）
eligible_rows: 3734
signal_rows  : 1158
effective_n  : 1158   ← 远超 30 门槛：这是一次【有功效】检验，不是小样本
```

### 3.2 统计输出

```text
mean_return   = 0.143 bp      median = 1.988 bp
win_rate      = 0.5147      gross = 165.62 bp
profit_factor = 1.004      max_dd = -5227.79 bp
cost 0x/1x/2x/3x = 1.057 / 0.143 / -0.771 / -1.685 bp
walk_forward  = 1.971 / 2.743 / -4.881
CI95          = [-6.351, 5.947]      permutation_p = 0.78681
t_stat        = 0.045
final_status  = REJECT   (原因：2x 成本下已转负 → 成本脆弱)
```

### 3.3 分段稳定性（§15，不得择优）

```json
{
 "2006-2010": {
  "n": 242,
  "mean_bp": 0.896,
  "insufficient": false
 },
 "2011-2015": {
  "n": 251,
  "mean_bp": 2.222,
  "insufficient": false
 },
 "2016-2020": {
  "n": 245,
  "mean_bp": 5.843,
  "insufficient": false
 },
 "2021-2026": {
  "n": 420,
  "mean_bp": -4.858,
  "insufficient": false
 }
}
```

### 3.4 直说

```text
20 年、1,158 个信号、有效样本充足 —— 结论仍是 REJECT：
  · 1x 成本后均值 +0.143bp ≈ 0（毛 +165.62bp / 1158 笔）
  · 2x 成本即转负（−0.771bp）→ 成本脆弱
  · 最大回撤 −5,227.79bp 远大于全部毛收益 → 路径不可接受
  · 三折中最后一折 −4.881bp；CI95 跨 0；置换检验 p=0.787
  · 分段显示 2021-2026 为负（−4.858bp, n=420）—— 揭示时代依赖，未做任何择优
=> 这不是「差一点」，是【没有证据】。规则不得因任何单折漂亮而放松。
```

## 四、其余黄金腿假设的状态（未执行，原因明确）

```json
{
 "H24_DXY_INVERSE_STATE": "needs DXY daily (long history unavailable: sina 'DX'=13 rows; yahoo 403; stooq/stooq-alternates blocked)",
 "H26_VIX_RISK_STATE": "needs VIX daily (sina 'VIX'=0 rows; yahoo 403)",
 "H28_DXY_UST_DOUBLE_STATE": "needs DXY",
 "H29_DXY_VIX_STRESS_COMBO": "needs DXY + VIX",
 "H30_CROSS_MARKET_AGREEMENT": "needs DXY + UST + VIX",
 "H31_CROSS_MARKET_STATE_TRANSITION": "needs DXY"
}
```
```json
{
 "H27_GC_XAUUSD_CONFIRMATION": "frozen definition has no operational trigger; needs a NEW pre-registered hypothesis id"
}
```

## 五、多重检验与分离

```text
累计：Round1 12 + Round2 11 + Round3 8 + 上次重验证 2 + 本次 1 = 34
本次进入 FDR 阶段 0 个（H25 在成本关卡即被 REJECT）；BH q=0.05
research/v3_strategy_round3/ 未改动 ✓   旧 GC 代理结果未合并 ✓
```

## 六、数据版本与哈希

```json
{
 "xau_frozen_normalized_sha256": "902313acacf0e8ec4eb2256fc1f8f3848a762e07f813f7cfa4e8c8b06451f63b",
 "panel_v2_freeze": "7c9b94cff9340016",
 "h25_result_hash": "bdc60a60ab3f32c1199bbf6cabb88e9c"
}
```

## 七、合规与停止

```text
未新增假设 ✓ 未改阈值/lookback/持有/entry-exit/成本锚 ✓ 未用替代变量冒充 DXY/VIX ✓
未删除困难样本 ✓ 未选择最佳年份 ✓ 未删除负分段 ✓
FORWARD = OFF · LIVE = OFF · ORDER_SEND = 0 ✓
```

## 八、结论与下一步

> 本轮把上次报告指出的瓶颈推进到底：**DXY/VIX 的长历史在本环境下不可得（已留证），而 UST10Y 已有的 20 年让我们得以真正检验 H25 —— 结论是 REJECT（成本脆弱 + 回撤不可接受 + 近期转负）。**
>
> 仍待解决的两件事（都需你决定，我不擅自动手）：
```text
1) DXY/VIX 长历史：需要换源（付费数据商 / 官方接口 / 代理），当前三个免凭据路径全部失败
2) H27：需要一个新 hypothesis_id 的预注册定义（分歧度量+lookback+阈值+方向）
```