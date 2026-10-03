# V3 金十 MCP 接入与 PIT 复评报告

`ts_utc = 2026-09-25T08:38:47.037692+00:00`

**`JIN10_STATUS = JIN10_PIT_CONDITIONAL`（凭据可用后，由此前的 `JIN10_PIT_FAIL` 升级）**

```text
V3 其余状态不变：V3_LIVE_ALLOWED=NO · V3_STRATEGY_FORWARD=NOT_ENABLED · ORDER_SEND=0 · FORWARD=0
```

## 一、接入结果（标准 MCP 流程）

```json
{
 "server_info": {
  "name": "jin10-mcp",
  "title": "金十数据智能开放平台",
  "description": "基于MCP协议的智能数据服务，为您提供实时、准确、全面的金融与市场数据接口。",
  "version": "1.0.0",
  "websiteUrl": "https://mcp.jin10.com/app/",
  "icons": [
   {
    "src": "https://cdn.jin10.com/assets/img/commons/favicon.ico",
    "mimeType": "image/x-icon"
   }
  ]
 },
 "negotiated_protocol": "2025-11-25",
 "tools": [
  "get_kline",
  "get_news",
  "get_quote",
  "list_calendar",
  "list_flash",
  "list_news",
  "search_flash",
  "search_news"
 ],
 "resources": [
  "quote://codes"
 ]
}
```

流程：`initialize` → `notifications/initialized` → `tools/list` / `resources/list` / `resources/read` → `tools/call`；
结果优先读 `structuredContent`（实测所有工具都返回它），`content` 仅作可读补充；分页统一 `cursor → data.next_cursor/has_more`。

## 二、PIT 复评（凭据下）

```json
{
 "MARKET_PIT_STATUS": "JIN10_PIT_CONDITIONAL",
 "MARKET_detail": {
  "n": 100,
  "min": "2026-09-25T06:59:00+00:00",
  "max": "2026-09-25T08:38:00+00:00",
  "span_hours": 1.65,
  "requested": 200,
  "returned": 100,
  "interval_seconds": 60,
  "fields": [
   "close",
   "high",
   "low",
   "open",
   "time",
   "volume"
  ]
 },
 "MARKET_history": "requesting a past window (time param) returned 0 rows -> historical market windows NOT retrievable",
 "NEWS_PIT_STATUS": "JIN10_PIT_CONDITIONAL",
 "NEWS_detail": {
  "n": 150,
  "min": "2026-09-17T11:43:36+00:00",
  "max": "2026-09-25T06:01:36+00:00",
  "span_hours": 186.3,
  "fields": [
   "content",
   "time",
   "title",
   "url"
  ],
  "sample_times": [
   "2026-09-25T14:01:36+08:00",
   "2026-09-25T13:32:46+08:00",
   "2026-09-25T11:59:55+08:00"
  ]
 },
 "CALENDAR_PIT_STATUS": "JIN10_PIT_CONDITIONAL",
 "CALENDAR_detail": {
  "rows": 158,
  "pub_time_min": "2026-09-21 07:01",
  "pub_time_max": "2026-09-26 01:00",
  "revised_non_null": 14,
  "note": "window is ~1 week around now; no date params are declared -> history not provable"
 },
 "MACRO_PIT_STATUS": "JIN10_PIT_CONDITIONAL",
 "MACRO_detail": {
  "pub_time": true,
  "revised_rows": 14,
  "window": [
   "2026-09-21 07:01",
   "2026-09-26 01:00"
  ]
 }
}
```

```text
NEWS     : 150 条 · 跨 186.3 小时（~7.8 天）· 真实 ISO+08:00 发布时间戳 → CONDITIONAL
CALENDAR : pub_time 真实存在（2026-09-21 → 09-26）· revised 14 行非空 → CONDITIONAL
MACRO    : actual / consensus / previous / revised + pub_time 齐全 → CONDITIONAL
MARKET   : 1m bar 最多 100 根（≈1.65 小时）· 请求历史窗口返回 0 行 → CONDITIONAL（仅近期/实时）
```

## 三、我自己纠正的两处误判（否则会得出错误结论）

```text
1) NEWS 一度被判 FAIL —— 实为【我的解析假阴性】：快讯 time 是 ISO-8601 字符串（+08:00），
   我按 epoch 整数转换 → 时间全为 null → 误判「无发布时间戳」。改正解析后：时间戳真实存在。
2) kline 的 span 一度算出 −1.65 小时 —— 实为【返回顺序是新→旧】，我未排序。改正后 span = +1.65 小时。
```

## 四、这次解锁了什么 / 没解锁什么

```text
解锁（条件性）：
  H23 新闻叙事类 —— 有 PIT 发布时间戳的快讯/资讯可检索（~1 周窗口）
  H22 宏观重定价 —— 日历带 pub_time + actual/consensus/previous/revised（~1 周窗口）
  H10/H21 跨资产确认 —— 可用 quote 实时报价做近期事件窗口验证
未解锁：
  历史行情窗口（time 参数返回 0 行）→ 不能作为市场历史数据源
  长历史宏观（日历窗口仅约 1 周，且未声明日期参数）→ 不能做 20 年宏观回溯
  修订体系不完整（revised 仅 14/158 行非空）
=> 可用于【近期事件窗口】研究；不可用于长历史宏观/行情回溯。
```

## 五、安全与用量

```text
Token 只写入 C:\AIQuant\.env.v3_jin10（.gitignore 的 .env.* 覆盖）—— 未入库、未写入报告/JSON/日志、未复述
客户端源码已通过断言检查：不含任何 sk- 形态字符串
本次共调用 16 次（每工具每日上限 1500，远未触及）
提示：该 Token 曾出现在对话记录中；如需谨慎，可在金十侧轮换一次（轮换后只需更新 .env.v3_jin10）
```

## 六、下一步（需你决定）

```text
1) 用金十日历的 pub_time + revised 做一次【真实事件窗口 PIT 研究】（H22 类，近期窗口）
2) 用快讯 PIT 做 H23 类（叙事/情绪）可行性验证
3) 若要长历史宏观/行情：金十不提供，仍需 ALFRED/付费源
```