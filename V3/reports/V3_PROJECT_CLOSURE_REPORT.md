# V3 项目结题报告

`ts_utc = 2026-09-25T08:29:56.364681+00:00`

**`V3_PROJECT_STATUS = CLOSED_NO_VALIDATED_EDGE`**

```text
平台：已建成并验证        （执行隔离 · 标定闭环 · 独立风控层 · PIT 数据层 · 假设注册表 · 事件账本）
研究：34 个假设已检验，候选 = 0
结论：V3 目前【不存在】可重复、成本后仍成立的可交易机制
状态：V3_LIVE_ALLOWED=NO · V3_STRATEGY_FORWARD=NOT_ENABLED · ORDER_SEND 未用于任何策略信号
```

## 一、平台交付物（已建成、已验证）

```text
执行隔离     3 个独立 MT5 实例（V1 160759434 / V2 160761384 / V3 160766418），magic 90002/90003/90004，互不干扰
标定闭环     V3 demo 标定 20/20 往返 PASS · HEDGE 生命周期（open→close→flat）已验证 · MT5↔账本对账残差 0
              ledger 哈希链 verify=ok · AUTH_SOURCE=SAVED_SESSION（无凭据落盘）
风控层       strategy/risk.py 独立模块：ALLOW/NO_TRADE/BLOCK，方向不可改写，确定性可重放，零 broker 调用
             （16 个单元用例 + 4 项附加检查全绿）
数据层       PIT 登记表 + 防未来信息泄漏 5 项测试全过 + XAU 现货日线 20 年（PIT_CONDITIONAL）
研究治理     假设注册表（冻结先于数据）· 成本/分块OOS/Regime/FDR 协议 · 事件账本 · 不可变历史（immutable rounds）
交易纪律     1R 止损 / 0.01 手固定 / 永不 LIVE
```

## 二、执行与标定状态

```json
{
 "V3_EXECUTION_MODE": "DEMO_CALIBRATION",
 "V3_ORDER_SEND_ALLOWED": "YES",
 "V3_LIVE_ALLOWED": "NO",
 "V3_FORWARD_ALLOWED": "NO",
 "V3_STRATEGY_FORWARD": "NOT_ENABLED"
}
```
```json
{
 "calibration_status": "DEMO_CALIBRATION_COMPLETE",
 "account": 160766418,
 "magic": 90004,
 "round_trips": 20,
 "net_pnl": -6.98,
 "ledger_net": -6.98,
 "auth_source": "SAVED_SESSION",
 "not_equal_to": [
  "STRATEGY_VALIDATED",
  "ALPHA_VALIDATED",
  "FORWARD_VALIDATED",
  "PROFITABLE"
 ]
}
```

## 三、研究账本（全部 34 个假设）

```text
Round 1   H01–H12   12 个  盘中 FXTM 数据（价格结构类）
Round 2   H13–H23   11 个  盘中 + 状态转换/流动性/执行制度类
Round 3   H24–H31    8 个  日线跨市场（DXY/UST/VIX → 黄金）
重验证    H25/H27/H30 3 个  换用 XAUUSD 现货后重测（其中 H25 延长到 20 年）
累计检验  34 个假设；候选 0 个
```

### 判定分布

```json
{
 "REJECT": 16,
 "INSUFFICIENT_SAMPLE": 9,
 "REJECT_DUPLICATE_HYPOTHESIS": 1,
 "NOT_TESTABLE": 3,
 "EDGE_UNCERTAIN": 5
}
```

### 各轮账面

```json
{
 "round1": {
  "H01_1M_SIGMA_FADE": "REJECT",
  "H02_5M_RANGE_BREAKOUT": "REJECT",
  "H03_LONDON_OPEN_MOMENTUM": "INSUFFICIENT_SAMPLE",
  "H04_LOWVOL_SIGMA_FADE": "REJECT",
  "H05_SPREAD_SPIKE_FADE": "REJECT",
  "H06_EMA_TREND_PULLBACK": "REJECT",
  "H07_ROUND_LEVEL_REJECTION": "REJECT",
  "H08_SQUEEZE_BREAKOUT": "REJECT",
  "H09_ROLLOVER_REVERSAL": "REJECT",
  "H10_DXY_CONFIRMED_REVERSAL": "INSUFFICIENT_SAMPLE",
  "H11_TICKRATE_SPIKE_FADE": "REJECT",
  "H12_DAILY_GAP_FADE": "INSUFFICIENT_SAMPLE"
 },
 "round2": {
  "H13_EXEC_REGIME_GATED_BREAKOUT": "REJECT",
  "H14_LIQUIDITY_VACUUM_REVERSAL": "REJECT",
  "H15_VOL_TRANSITION_EXPANSION": "INSUFFICIENT_SAMPLE",
  "H16_VOL_TRANSITION_CONTRACTION": "REJECT",
  "H17_SESSION_HANDOFF_CONTINUATION": "INSUFFICIENT_SAMPLE",
  "H18_ASIA_RANGE_FAKEBREAK": "REJECT",
  "H19_COST_GATED_MOMENTUM": "REJECT",
  "H20_CTRL_RANGE_BREAKOUT_RETEST": "REJECT_DUPLICATE_HYPOTHESIS",
  "H21_CROSS_ASSET_DIVERGENCE": "NOT_TESTABLE",
  "H22_MACRO_REPRICING_WINDOW": "NOT_TESTABLE",
  "H23_NEWS_NARRATIVE_SHIFT": "NOT_TESTABLE"
 },
 "round3": {
  "H24_DXY_INVERSE_STATE": "EDGE_UNCERTAIN",
  "H25_UST_YIELD_STATE": "EDGE_UNCERTAIN",
  "H26_VIX_RISK_STATE": "EDGE_UNCERTAIN",
  "H27_GC_XAUUSD_CONFIRMATION": "INSUFFICIENT_SAMPLE",
  "H28_DXY_UST_DOUBLE_STATE": "EDGE_UNCERTAIN",
  "H29_DXY_VIX_STRESS_COMBO": "REJECT",
  "H30_CROSS_MARKET_AGREEMENT": "INSUFFICIENT_SAMPLE",
  "H31_CROSS_MARKET_STATE_TRANSITION": "EDGE_UNCERTAIN"
 },
 "revalidation": {
  "H27_GC_XAUUSD_CONFIRMATION": "INSUFFICIENT_SAMPLE",
  "H30_CROSS_MARKET_AGREEMENT": "INSUFFICIENT_SAMPLE",
  "H25_UST_YIELD_STATE": "REJECT"
 }
}
```

## 四、被证伪的机制（重要负面知识，勿重复挖）

```text
· UST 收益率 → 黄金（H25）：20 年、1,158 信号、有效样本充足 → REJECT
    1x 后 +0.143bp ≈ 0；2x 转负；最大回撤 −5,227.79bp 远超毛收益；末折 −4.881bp；CI95 跨 0；p=0.787
    分段：2006-10 +0.90 / 2011-15 +2.22 / 2016-20 +5.84 / 2021-26 −4.86（时代依赖，近期为负）
· 盘中 1m σ-fade / 区间突破 / EMA 回踩 / 整数关 / tick 率脉冲 / 点差脉冲：全部 REJECT（成本后无净边）
· 日线三变量宏观一致态（H30）：2 年窗口仅 13 个信号 → 样本不足，无法判定（非「有效」）
· GC/现货基差（H27）：定义不可操作化，无法检验
=> 这批负面知识本身是资产：它把「看似有希望」的方向从候选池里排除掉了。
```

## 五、数据资产

```json
{
 "xau_spot": {
  "rows": 5186,
  "start": "2006-09-25",
  "end": "2026-09-25",
  "designation": "CANDIDATE_PRIMARY (CONDITIONAL)",
  "pit": "PIT_CONDITIONAL",
  "raw_sha256": "1e946fa8df2a85fd",
  "normalized_sha256": "902313acacf0e8ec"
 },
 "ust10y": "官方 Treasury CSV 2006-2026（20 年，免凭据，可自动化）",
 "gc_f_dxy_vix": "各约 2 年（2024-09→2026-09）",
 "jin10": "JIN10_PIT_FAIL（可达但无可 PIT 数据；详见前报告）",
 "macro_pit_vintage": "不可得（需 ALFRED/付费 key）"
}
```

## 六、阻塞清单（按可解性排序）

```json
{
 "1_vix_dxy_long_history": {
  "blocker": "VIX/DXY 20 年日线不可得",
  "evidence": {
   "100.UDI": {
    "error": "RemoteDisconnected: Remote end closed connection without response"
   },
   "100.UDI2": {
    "error": "RemoteDisconnected: Remote end closed connection without response"
   },
   "100.USDX": {
    "error": "RemoteDisconnected: Remote end closed connection without response"
   },
   "VIX_100.VIX": {
    "error": "RemoteDisconnected: Remote end closed connection without response"
   },
   "VIX_101.VIX": {
    "error": "RemoteDisconnected: Remote end closed connection without response"
   },
   "VIX_100.VX": {
    "error": "RemoteDisconnected: Remote end closed connection without response"
   },
   "VIX_100.VIX2": {
    "error": "RemoteDisconnected: Remote end closed connection without response"
   }
  },
  "verdict": "东方财富路径不可靠（7/7 RemoteDisconnected）；Yahoo 403；stooq 限流；新浪符号不匹配",
  "unblocks": [
   "H24",
   "H26",
   "H28",
   "H29",
   "H30",
   "H31"
  ],
  "requires": "付费数据商 / 官方接口 / 带凭据的 API（需你决定是否投入）"
 },
 "2_macro_pit_vintage": {
  "blocker": "宏观 PIT + 修订史不可得",
  "unblocks": [
   "H10",
   "H21",
   "H22"
  ],
  "requires": "ALFRED/FRED API key 或等价付费源"
 },
 "3_news_calendar_pit": {
  "blocker": "新闻/日历 PIT 不可得",
  "unblocks": [
   "H23"
  ],
  "requires": "金十官方 MCP OAuth（你本人注册）或等价源"
 },
 "4_h27_definition": {
  "blocker": "H27 冻结定义缺可操作触发规则",
  "requires": "以新 hypothesis_id 预注册定义（不需新数据）"
 }
}
```

## 七、完整性审计（本次结题时）

```json
{
 "v3_adapter.py": "UNCHANGED",
 "calibration_pilot.py": "UNCHANGED",
 "risk.py": "UNCHANGED",
 "hft_ledger": "UNCHANGED",
 "v3_strategy_round3": "UNCHANGED"
}
```

```text
冻结资产未改动 ✓ · Round 3 历史 immutable ✓ · 旧 GC 代理结果未合并 ✓ · 未新增假设 ✓ · 未调参 ✓
ORDER_SEND=0（策略侧）· FORWARD=OFF · LIVE=OFF ✓
```

## 八、项目结论与决策点

> **V3 = 一个已建成、已验证、纪律严明的量化研究平台，但在 34 个假设的检验中没有找到任何可交易机制。**
>
> 这不是失败——它意味着：我们已经用真成本、分块 OOS、Regime、多重检验控制，把「看起来能赚钱」的东西一条条排除掉了。
> 剩下的所有「可能」，都被数据可得性挡在门外（VIX/DXY 长历史、宏观 PIT、新闻 PIT）。

### 三个可选方向（请你选其一，我按你的选择继续）

```text
A) 投入数据：解决 VIX/DXY 长历史 + 宏观 PIT（付费/官方 key）→ 才能继续 H24/H26/H28/H29/H30/H31 与宏观类假设
B) 换机制族：不再依赖外部宏观数据，改为纯市场微结构/执行成本优势方向（但需明确新数据需求与预期）
C) 收尾：接受「无验证机制」结论，V3 保持 RESEARCH 状态，把资源转向 V1/V2 的 forward 观察
```

**我的建议（仅供参考，不代替你决策）**：在没有任何 PIT 宏观源的前提下，继续生成跨市场假设的边际价值很低；
**若不愿投入数据预算，C 是诚实且成本最低的选择**；若愿意投入，优先买 VIX/DXY 长历史（一次投入可解锁 6 条假设）。

```text
V3_PROJECT_STATUS = CLOSED_NO_VALIDATED_EDGE
V3_FORWARD_READY = FALSE · V3_STRATEGY_FORWARD = NOT_ENABLED · V3_LIVE_ALLOWED = NO
```