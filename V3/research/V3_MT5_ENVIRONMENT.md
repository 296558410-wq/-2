# V3 MT5 环境清单 — XAUUSD 高频研究（只读）

- 生成: 2026-09-17T11:20:28.750975+00:00
- **verdict: PASS**

## 实例 / 终端
- instance: `fxtm_demo_v3`
- terminal: `C:\AIQuant\mt5_instances\fxtm_demo_v3\terminal64.exe`
- data directory: `C:\AIQuant\mt5_instances\fxtm_demo_v3`  (实际 data_path: `C:\AIQuant\mt5_instances\fxtm_demo_v3`)
- server: `ForexTimeFXTM-Demo01`
- symbol: `XAUUSD`
- Magic Number: **90004** (V1=90002 / V2=90003)
- 创建时间: 2026-09-17T11:20:28.750975+00:00

## 账号（敏感信息不写入）
- login present: True
- 独立账号: NO（复用 FXTM demo 凭据；未获独立账号 → §四 回退：只建实例/只读，永不发单）
- trade_allowed(broker): True
- **order_send: 代码层硬拦截（OrderSendBlocked）**

## symbol_info
```json
{
 "name": "XAUUSD",
 "digits": 2,
 "point": 0.01,
 "spread_current": 13,
 "trade_mode": 4,
 "filling_mode": 1,
 "visible": true,
 "session_deals": 0,
 "volume_min": 0.01,
 "volume_step": 0.01,
 "description": "Gold (Spot)",
 "currency_base": "USD",
 "currency_profit": "USD"
}
```
## 数据能力
```json
{
 "quote_bidask": true,
 "ticks_read": true,
 "raw_tick_storage": true,
 "bars_m1": true,
 "bars_m5": true
}
```
## tick 统计（近 6h）
```json
{
 "spread_points": {
  "p50": 15.0,
  "p90": 18.0,
  "p95": 23.0,
  "p99": 23.0,
  "min": 13.0,
  "max": 60.0,
  "mean": 15.72
 },
 "interval_ms": {
  "p50": 265.0,
  "p90": 621.0,
  "p95": 845.0,
  "p99": 1414.0,
  "min": 0,
  "max": 4200173
 },
 "ticks_per_hour": {
  "2026-09-16T11": 6148,
  "2026-09-16T12": 8904,
  "2026-09-16T13": 8944,
  "2026-09-16T14": 9635,
  "2026-09-16T15": 10525,
  "2026-09-16T16": 12619,
  "2026-09-16T17": 12471,
  "2026-09-16T18": 11781,
  "2026-09-16T19": 9331,
  "2026-09-16T20": 9619,
  "2026-09-16T21": 16965,
  "2026-09-16T22": 15174,
  "2026-09-16T23": 7962,
  "2026-09-17T01": 5428,
  "2026-09-17T02": 7047,
  "2026-09-17T03": 9837,
  "2026-09-17T04": 10918,
  "2026-09-17T05": 9978,
  "2026-09-17T06": 8045,
  "2026-09-17T07": 6662,
  "2026-09-17T08": 8643,
  "2026-09-17T09": 10134,
  "2026-09-17T10": 9815,
  "2026-09-17T11": 9447,
  "2026-09-17T12": 9107,
  "2026-09-17T13": 8369,
  "2026-09-17T14": 3878
 },
 "ticks_per_hour_mean": 9532.8,
 "sessions_gaps_gt_30s": 1,
 "timestamp_resolution_ms_declared": 1,
 "distinct_ms_low3": 1000,
 "flags_seen": [
  1026,
  1028,
  1030,
  1154,
  1158
 ]
}
```
- tick fetch: {"count": 257386, "window_hours": 24, "fetch_ms": 4895.8}
- live quote: {"bid": 4330.8, "ask": 4330.93, "last": 0.0, "spread_points": 13.0, "time": 1789654831, "time_msc": 1789654831512, "volume": 0, "flags": 1030, "roundtrip_ms": 0.048}
- raw tick 样本: {"path": "C:\\AIQuant\\research\\hermes\\trader_v3\\data\\raw_ticks\\20260917T112039Z_xauusd_ticks_sample.jsonl", "rows": 5000, "sha256": "da27084e04faea764bb0d20caafce55694bcc9703c337707a17d14a0eeb19a74"}

## 高频研究限制（§四）
```json
{
 "true_trade_direction": "PARTIAL — tick.flags 有 BUY/SELL 标志(成交方向, broker侧)，非真实 aggressor",
 "aggressor_side": "UNRESOLVABLE — MT5 无 order book，无 aggressor",
 "market_depth": "UNRESOLVABLE — MT5 零售数据无 DOM/L2",
 "queue_position": "UNRESOLVABLE — 无 queue 信息",
 "only_bidask_quote": "YES — 仅 Bid/Ask(+broker 聚合 last/volume)",
 "broker_side_aggregation": "LIKELY — 零售 broker tick 为聚合流，非交易所逐笔",
 "timestamp_resolution": "声明 ms(time_msc)；实际分辨率受 broker 聚合影响，通常 >1ms",
 "supports_100ms": "PARTIAL — 可聚合到 100ms，但非真实 100ms 事件序列",
 "supports_500ms": "PARTIAL",
 "supports_1s": "YES(聚合)",
 "supports_2s": "YES(聚合)"
}
```
## DUKA 对照
```json
{
 "duka_dir": "C:\\AIQuant\\data\\staging_duka",
 "ticks_files": 140,
 "latest_tick_file": "ticks_20260804.parquet",
 "overlap_window": "NONE — DUKA 最新 2026-08-04，MT5 窗口 2026-09 无重叠",
 "status": "DATA_GAP",
 "note": "无时间重叠 → 无法逐 tick 对照；仅能做价格量级/spread 分布参照（见 tick_stats）",
 "duka_cols": [
  "ms",
  "ask",
  "bid",
  "ask_vol",
  "bid_vol",
  "hour"
 ],
 "duka_rows": 216572,
 "duka_price_scale": "ask/bid /1000 (推断)",
 "mt5_tick_window": {
  "from": 1789557631,
  "to": 1789654835
 }
}
```
## 安全闸门
```json
{
 "V3_LIVE_ALLOWED": "NO",
 "V3_ORDER_SEND_ALLOWED": "NO",
 "V3_FORWARD_ALLOWED": "NO"
}```

## V1/V2 隔离证明
- V1: `C:\Program Files\ForexTime (FXTM) MT5\terminal64.exe` — 未连接、未修改
- V2: `C:\AIQuant\mt5_instances\fxtm_demo_01` — 未连接、未修改
- V3 只用独立 data dir: `C:\AIQuant\mt5_instances\fxtm_demo_v3`（data_path 断言含 fxtm_demo_v3）
- order_send/order_check 代码层 raise；三个安全闸门均为 NO

## 数据缺口 / FAIL
- (无)
- HF: true_trade_direction=PARTIAL — tick.flags 有 BUY/SELL 标志(成交方向, broker侧)，非真实 aggressor
- HF: aggressor_side=UNRESOLVABLE — MT5 无 order book，无 aggressor
- HF: market_depth=UNRESOLVABLE — MT5 零售数据无 DOM/L2
- HF: queue_position=UNRESOLVABLE — 无 queue 信息
- HF: supports_100ms=PARTIAL — 可聚合到 100ms，但非真实 100ms 事件序列
- HF: supports_500ms=PARTIAL

## 关键文件 SHA256
```json
{
 "config\\v3_config.json": "8f576abdf0f62b78db26ab5b16d27f380ff1a37f6be6666699670bfe9b57ccb8",
 "mt5\\v3_adapter.py": "aa30d674c40abd076a9cce16ea0e9cb418abb628f25533630d486bc730d70124",
 "tools\\v3_capability_audit.py": "c47d5125a351fd10f4a3a50da34ee12c6ddc1fa928704618c5a5459d491d8168",
 "state\\V3_LIVE_ALLOWED": "23794d91c53ae875c8e247d72561e35d9d06ee07c70c9e0dbcc977a6d161504a",
 "state\\V3_ORDER_SEND_ALLOWED": "23794d91c53ae875c8e247d72561e35d9d06ee07c70c9e0dbcc977a6d161504a",
 "state\\V3_FORWARD_ALLOWED": "23794d91c53ae875c8e247d72561e35d9d06ee07c70c9e0dbcc977a6d161504a"
}
```
