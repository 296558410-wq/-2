# V3 跨市场长历史数据源发现报告

`ts_utc = 2026-09-25T10:38:52.763780+00:00` · 任务 `V3_CROSSMARKET_LONG_HISTORY_SOURCE_DISCOVERY`

## 1. Executive Summary

```text
是否找到可用的长历史跨市场数据源？——【找到了候选，语义仍有缺口】
最关键的发现：Yahoo（免费·免账号·中国内网可直连）现在提供 1h/2y 的 DXY / VIX / ^TNX，
  配合 HistData XAUUSD M1，可把四市场重叠从 R2 的【24 天】提升到：
    · 5m 四市场：63 天 / 3,600 根（2.6 倍）
    · 1h 三市场(XAU+DXY+VIX)：624 天 / 5,985 根
    · 1h 四市场：需对 ^TNX 做【共同网格规范化】(:20 偏移)，规范化后 624 天 / 2992 根
缺口：UST10Y 目前只有代理(^TNX)，官方 FRED DGS10 本机不可达；Yahoo 的 bar open/close 语义无文档 → UNKNOWN
最终状态：PARTIAL
```

## 2. Source Matrix

| 市场 | 数据源 | 周期 | 起始 | 结束 | 时区 | 定义 | 免费 | PIT | 状态 |
|---|---|---|---|---|---|---|---|---|---|
| XAUUSD | HistData M1(BID) | 1m/5m/1h | 2025-01-01 | 2026-09-18 | EST固定(VERIFIED) | UNKNOWN(vendor says Forex Pair) | FREE | OK | PARTIAL |
| DXY | Yahoo DX-Y.NYB | 5m | 2026-07-17 | 2026-09-25 | epoch UTC | UNKNOWN | FREE | OK | PARTIAL |
| DXY | Yahoo DX-Y.NYB | 1h | 2024-09-25 | 2026-09-25 | epoch UTC | UNKNOWN | FREE | OK | PARTIAL |
| VIX | Yahoo ^VIX | 5m | 2026-07-06 | 2026-09-25 | epoch UTC | UNKNOWN | FREE | OK | PARTIAL |
| VIX | Yahoo ^VIX | 1h | 2024-09-25 | 2026-09-25 | epoch UTC | UNKNOWN | FREE | OK | PARTIAL |
| UST10Y | Yahoo ^TNX(代理) | 5m | 2026-07-16 | 2026-09-24 | epoch UTC | PROXY(非官方) | FREE | OK | PARTIAL |
| UST10Y | Yahoo ^TNX(代理) | 1h | 2024-09-25 | 2026-09-24 | epoch UTC | PROXY(非官方) | FREE | OK | PARTIAL |
| UST10Y | FRED DGS10(官方日频) | - | - | - | - | official | FREE | UNRESOLVED | BLOCKED(unreachable) |

## 3. Overlap Matrix

| 数据组合 | 周期 | 开始 | 结束 | 天数 | Bars | 状态 |
|---|---|---|---|---|---|---|
| XAU+DXY | 5m | 2026-07-17 04:00 | 2026-09-18 20:55 | 63 | 11931 | OK |
| XAU+VIX | 5m | 2026-07-06 07:15 | 2026-09-18 20:10 | 74 | 8524 | OK |
| XAU+UST10Y | 5m | 2026-07-16 12:20 | 2026-09-18 18:55 | 64 | 3680 | OK |
| XAU+DXY+VIX | 5m | 2026-07-17 07:15 | 2026-09-18 20:10 | 63 | 7018 | OK |
| XAU+DXY+UST10Y | 5m | 2026-07-17 12:20 | 2026-09-18 18:55 | 63 | 3600 | OK |
| XAU+UST10Y+VIX | 5m | 2026-07-16 12:20 | 2026-09-18 18:55 | 64 | 3680 | OK |
| XAU+DXY+UST10Y+VIX | 5m | 2026-07-17 12:20 | 2026-09-18 18:55 | 63 | 3600 | OK |
| XAU+DXY | 1h | 2025-01-02 05:00 | 2026-09-18 20:00 | 624 | 9830 | OK |
| XAU+VIX | 1h | 2025-01-02 08:00 | 2026-09-18 20:00 | 624 | 6107 | OK |
| XAU+UST10Y | 1h | 2025-01-02 13:00 | 2026-09-18 18:00 | 624 | 2998 | OK |
| XAU+DXY+VIX | 1h | 2025-01-02 08:00 | 2026-09-18 20:00 | 624 | 5997 | OK |
| XAU+DXY+UST10Y | 1h | 2025-01-02 13:00 | 2026-09-18 18:00 | 624 | 2992 | OK |
| XAU+UST10Y+VIX | 1h | 2025-01-02 13:00 | 2026-09-18 18:00 | 624 | 2996 | OK |
| XAU+DXY+UST10Y+VIX | 1h | 2025-01-02 13:00 | 2026-09-18 18:00 | 624 | 2992 | OK |

```text
COMMON_OVERLAP_START = 2025-01-02 13:00:00+00:00
COMMON_OVERLAP_END   = 2026-09-18 18:00:00+00:00
COMMON_OVERLAP_DAYS  = 624
COMMON_OVERLAP_BARS  = 2992  (1h, grid-normalized)
5m four-market       = 63 days / 3600 bars
```

## 4. 数据语义审计（VERIFIED / UNKNOWN / UNRESOLVED）

```json
{
 "XAUUSD": {
  "source": "HistData.com M1 (BID)",
  "instrument_definition": "vendor label 'Forex Pair XAU/USD'; spot-vs-CFD not stated -> UNKNOWN",
  "asset_class": "UNKNOWN",
  "venue": "UNKNOWN",
  "price_type": "BID (VERIFIED)",
  "timeframe": "1m (5m/1h derived by resampling the same source)",
  "timezone": "EST (UTC-5) FIXED (VERIFIED via official FAQ)",
  "DST": "NOT_APPLICABLE (VERIFIED)",
  "bar_open_close_semantics": "UNKNOWN",
  "PIT_STATUS": "OK (market data; bar close = tradable)",
  "license": "UNKNOWN",
  "free_or_paid": "FREE",
  "authentication_required": false,
  "China_accessibility": "YES (verified download)",
  "reproducibility": "RAW byte-identical on repeat downloads"
 },
 "DXY": {
  "source": "Yahoo chart API",
  "symbol": "DX-Y.NYB",
  "instrument_definition": "ICE US Dollar Index (per symbol metadata)",
  "instrument_definition_status": "UNKNOWN (not vendor-documented in the response)",
  "asset_class": "index",
  "venue": "ICE (per symbol)",
  "price_type": "UNKNOWN",
  "timeframe": "5m / 1h (1d series appears broken: 168 rows for range=max)",
  "timezone": "epoch seconds (UTC)",
  "DST": "not_applicable",
  "bar_open_close_semantics": "UNKNOWN",
  "PIT_STATUS": "OK (market data)",
  "license": "UNKNOWN",
  "free_or_paid": "FREE",
  "authentication_required": false,
  "China_accessibility": "YES (HTTP 200 verified)",
  "reproducibility": "raw JSON hashed; Yahoo may revise history -> not byte-guaranteed"
 },
 "VIX": {
  "source": "Yahoo chart API",
  "symbol": "^VIX",
  "instrument_definition": "CBOE VIX (per symbol metadata)",
  "instrument_definition_status": "UNKNOWN (not vendor-documented in the response)",
  "asset_class": "index",
  "venue": "CBOE",
  "price_type": "UNKNOWN",
  "timeframe": "5m / 1h / 1d",
  "timezone": "epoch seconds (UTC)",
  "DST": "not_applicable",
  "bar_open_close_semantics": "UNKNOWN",
  "PIT_STATUS": "OK",
  "license": "UNKNOWN",
  "free_or_paid": "FREE",
  "authentication_required": false,
  "China_accessibility": "YES",
  "reproducibility": "not byte-guaranteed"
 },
 "UST10Y_PROXY_TNX": {
  "source": "Yahoo chart API",
  "symbol": "^TNX",
  "instrument_definition": "CBOE 10-Year Treasury Note Yield Index = PROXY, NOT the official Treasury constant-maturity yield",
  "instrument_definition_status": "PROXY (explicitly labelled; must not be called official UST10Y)",
  "asset_class": "index (yield)",
  "venue": "CBOE",
  "price_type": "UNKNOWN",
  "timeframe": "5m / 1h",
  "timezone": "epoch seconds (UTC)",
  "DST": "not_applicable",
  "bar_open_close_semantics": "UNKNOWN",
  "grid_offset_note": "^TNX intraday bars land at :20 offset, which breaks exact-timestamp alignment with XAUUSD bars at :00",
  "PIT_STATUS": "OK",
  "license": "UNKNOWN",
  "free_or_paid": "FREE",
  "authentication_required": false,
  "China_accessibility": "YES",
  "official_alternative": "FRED DGS10 (official, daily) - but fred.stlouisfed.org is currently UNREACHABLE from this host (timeouts)"
 },
 "EXCLUDED": {
  "GC=F / COMEX gold futures": "class E futures - NOT XAUUSD spot/CFD",
  "yahoo_daily_DXY_TNX": "range=max returned only 168 rows (1985-2026) -> not a usable daily series",
  "stooq": "HTTP 200 but returns a JS challenge page - unusable without a browser",
  "FRED": "unreachable from this host at task time"
 }
}
```

## 5. 推荐进入 R3 的数据组合（仅数据基础设施层面）

```json
[
 {
  "rank": 1,
  "combo": "XAUUSD + DXY + VIX",
  "timeframe": "1h",
  "overlap_days": 624,
  "bars": 5997,
  "why": "largest clean 3-market overlap; all three series are free, automatable and China-accessible",
  "gaps": [
   "Yahoo bar open/close semantics UNKNOWN",
   "Yahoo history may be revised"
  ]
 },
 {
  "rank": 2,
  "combo": "XAUUSD + DXY + UST10Y(proxy) + VIX",
  "timeframe": "5m",
  "overlap_days": 63,
  "bars": 3600,
  "why": "four-market 5m overlap, 2.6x the R2 window",
  "gaps": [
   "^TNX is a proxy"
  ]
 },
 {
  "rank": 3,
  "combo": "XAUUSD + DXY + VIX + UST10Y(proxy)",
  "timeframe": "1h",
  "overlap_days": 624,
  "bars": 2992,
  "why": "four-market long overlap under grid normalization",
  "gaps": [
   "UST10Y is a proxy",
   "grid normalization required for ^TNX (:20 offset)"
  ]
 }
]
```

## 6. 未解决问题

```json
{
 "schema": "v3_crossmarket_unresolved/1",
 "ts_utc": "2026-09-25T10:38:52.763780+00:00",
 "missing_history": [
  "XAUUSD has no data before 2025-01 (HistData XAUUSD starts 2025-01)",
  "DXY/VIX/^TNX intraday from Yahoo: 5m only 60 days, 1h only 2 years"
 ],
 "unknown_semantics": [
  "XAUUSD bar open/close",
  "Yahoo bar open/close for DXY/VIX/^TNX",
  "price_type for DXY/VIX/^TNX"
 ],
 "license_uncertainty": [
  "HistData terms not published",
  "Yahoo data licensing/redistribution UNKNOWN"
 ],
 "timestamp_uncertainty": [
  "^TNX intraday :20 grid offset",
  "Yahoo bar boundary convention"
 ],
 "PIT_uncertainty": [
  "Yahoo intraday is market data (PIT OK) but revision behaviour is undocumented",
  "no official UST10Y intraday source currently reachable"
 ],
 "source_accessibility": [
  "FRED unreachable from this host",
  "stooq JS-challenge blocked",
  "Dukascopy datafeed still TCP-blocked"
 ],
 "official_vs_proxy": [
  "UST10Y currently only available as the ^TNX proxy; the official FRED DGS10 daily series is unreachable"
 ]
}
```

## 附：本任务未做的事（§十二/§十八）

```text
NO_ALPHA_CONCLUSION · NO_PARAMETER_OPTIMIZATION · NO_TRADING · NO_DATA_PURCHASE · NO_V1_CHANGE · NO_V2_CHANGE
未修改 F1~F8 · 未新增假设 · 未按 R2 的 F4/F5 结果选取数据 · 未拼接不同源制造连续历史 · 未删数据制造重叠
唯一规范化：将各序列 floor 到其名义 bar 网格（用于对齐 ^TNX 的 :20 偏移）——已在报告中显式披露，非隐藏平移
```