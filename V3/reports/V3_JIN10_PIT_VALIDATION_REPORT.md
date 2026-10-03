# V3 金十数据 PIT 可行性验证报告

`ts_utc = 2026-09-25T01:31:46.566249+00:00` · **最终状态：`JIN10_PIT_FAIL`**

```text
NEWS_PIT_STATUS     = JIN10_PIT_FAIL
MACRO_PIT_STATUS    = JIN10_PIT_FAIL
MARKET_PIT_STATUS   = JIN10_PIT_FAIL
CALENDAR_STATUS     = AUTH_REQUIRED_NOT_OBTAINED
```

## §25 十五问

**1. 中国内网是否可以访问？** **可以。** 从本机（V3/OpenClaw 所在的中国内网机器）直连、无 VPN/代理/海外跳板：
```text
www.jin10.com        DNS ok  TLS1.3  HTTP 200  1569ms
flash.jin10.com      DNS ok  TLS1.3  HTTP 200  2839ms
rili.jin10.com       DNS ok  TLS1.3  HTTP 200  3048ms
mcp.jin10.com/mcp    DNS ok  TLS1.2  HTTP 401  3812ms
flash-api.jin10.com  DNS ok  TLS ok   HTTP 502  2951ms
datacenter-api...    DNS ok  TLS ok   HTTP 502  4068ms
api./m./cdn-rili.    DNS 解析失败
```
`CHINA_NET_ACCESS = PASS`（对可达主机而言）。

**2. 官方 API / MCP 是否可用？** 官方 **MCP 端点存在且可达**（`https://mcp.jin10.com/mcp` → **401**，且
`/.well-known/oauth-authorization-server` → **200**，OAuth 发现文档存在）。**未获得任何无认证即可用的官方数据接口。**

**3. 是否需要 Token？** **需要。** 官方 MCP 走 OAuth（需注册）；`flash-api` 即便带 channel 参数也返回 502。
按 §7：记 `AUTH_REQUIRED`，**未注册、未绕过、未伪造、未借用任何第三方 app-id**。

**4. XAUUSD 是否可获取？** **否（在无凭据条件下）**。官网/快讯页返回 **6254 字节的客户端渲染空壳**（HTML 内只有 `<head>` 元信息，无行情、无时间戳、无历史；数据须由前端 JS 调接口取得）；
`flash-api` 502。未获得 symbol/bid/ask/last/timestamp 任一字段。

**5. K 线是否可获取？** **否**（无 1m/5m/15m/1h/1d 任一可访问接口；无从验证 unfinished_bar）。

**6. 历史行情是否可获取？** **否**（无法调用 latest，更无法测试过去 1/7/30 天或指定历史 timestamp）。

**7. 历史快讯是否可获取？** **否**。`flash.jin10.com` 与 `www.jin10.com` 返回**逐字节相同**的客户端渲染空壳（head 完全一致，证明 HTML 内不含任何新闻内容），
`flash-api.jin10.com/get_flash_list`（含 `?channel=&vip=`）**全部 502**。没有取得任何快讯记录。

**8. 快讯是否存在精确发布时间？** **无法验证**（连一条快讯都取不到）。故不判定为 PASS。

**9. 历史快讯是否可以重放？** **否**（无数据、无 id、无 publication_time，无法构造历史窗口查询）。

**10. 财经日历是否可获取？** **未获得**。`rili.jin10.com` 返回 4260 字节客户端渲染空壳（Nuxt 壳，`data-n-head`），HTML 内无任何数据；日历数据由前端 JS 调接口取得，而该接口需要认证。
`CALENDAR_STATUS = AUTH_REQUIRED_NOT_OBTAINED`。

**11. 宏观 Actual/Forecast 是否有时间戳？** **无**（未获得任何日历数据，无法检查 actual_time/revision).

**12. 是否存在 revision？** **无法验证**（无数据）。

**13. 是否能够建立 `get_information_available_at(T)`？** **不能**。没有具备 `publication_time` 的历史信息可供过滤，
任何实现都会是空壳或伪造 → 按 §22（"如果条件允许"）**未创建 `strategy/jin10_pit_replay.py`**（不制造假的 PIT 适配器）。

**14. 未来信息泄漏测试是否 PASS？** **N/A —— 无源可测**。既有 V3 PIT 层（Round 3 前建立）的 5 项泄漏测试仍为 5/5 PASS，
但**金十未提供任何可纳入该层的数据**，因此不能声称"金十通过了泄漏测试"。

**15. 最终 PIT 状态是什么？** **`JIN10_PIT_FAIL`**。

## 为什么不是 `JIN10_UNAVAILABLE`？

```text
金十主机是中国内网可直连的（DNS/TLS/HTTP 均正常）。
失败发生在"能力"而非"连通"：每一个承载数据的端点要么是 SPA 空壳，要么需要 OAuth（401），要么 502。
```

## GitHub 开源资料考察（§5）

```text
仓库搜索可用（code search 需登录 → 401，未使用凭据）：
  djp440/jin10-mcp ★3                    "通过金十数据官方MCP查询金融行情、K线数据、快讯、文章和经济日历"
  echosongg/jin10-market-analysis-skill ★3 "Hermes Agent skill for Jin10 financial market data analysis via MCP"
  brucelau1987cn/jin10-mcp-proxy ★0        "Jin10 MCP server HTTP proxy for Cloudflare Pages Functions"
  yyqq188/jinshidata_api ★0                "金十数据对外的api"
来源分类（§6）：以上全部为【第三方包装/代理】或【未官方确认】→ DO NOT TREAT AS OFFICIAL。
未据其声称的"支持历史数据"认定 PIT（§5 末条）。
```

## 接口来源分类（§6）

| endpoint | source_type | access_status |
|---|---|---|
| https://www.jin10.com/ | OFFICIAL_WEB | REACHABLE（客户端渲染空壳，无服务端数据） |
| https://flash.jin10.com/ | OFFICIAL_WEB | REACHABLE（客户端渲染空壳，与 www 逐字节相同） |
| https://rili.jin10.com/ | OFFICIAL_WEB | REACHABLE（客户端渲染空壳，无数据） |
| https://mcp.jin10.com/mcp | **OFFICIAL_MCP** | **REACHABLE_AUTH_REQUIRED (401, OAuth)** |
| https://flash-api.jin10.com/get_flash_list | UNOFFICIAL_API / REVERSE_ENGINEERED | HTTP 502 |
| https://datacenter-api.jin10.com/ | UNOFFICIAL_API / UNKNOWN | HTTP 502 |

## §24 真实历史事件验证

**未执行。** 前提是"金十理论上有快讯且可历史查询"。本次**连一条快讯都取不到**（502 + SPA 空壳），
按 §24 无法选取事件进行 T−5/T/T+1/T+5/T+15 分钟的信息重建。
**不伪造**：不构造假事件、不用当前页面冒充历史信息。

## 结论（§28）

> 金十在中国内网**可访问**，但在**无凭据**条件下**不提供可审计、可重放、PIT 安全的行情/快讯/日历数据**。
> 因此：**JIN10_PIT_FAIL**，立即停止，**不为获得 Candidate 降低 PIT 标准**。

## 唯一可能的继续路径（需你决定，本任务不做）

```text
1) 你本人注册金十官方 MCP（OAuth）并把 token 写入 C:\AIQuant\.env.v3_jin10
   -> 之后重跑本探针（probe.py 会从 os.getenv("V3_JIN10_TOKEN") 读取，绝不落盘）
   -> 才能进入 PIT-T1..T5 与 §24 事件重建
2) 若 MCP 也不提供历史 publication_time，则 NEWS/MACRO 仍为 FAIL
```

## 合规声明（§4/§7/§27）

```text
ORDER_SEND = 0 · FORWARD = 0 · LIVE = 0 · 未建 H24+ · 未跑 Round 3
未改 H01–H12 / H13–H23 / v3_adapter.py / calibration / calibration ledger / sequence / V1 / V2 / V3 执行参数
未把普通历史新闻冒充 PIT · 未把"当前可见历史"当成"当时可见"
未在 git/报告/JSON/代码/日志中写入任何真实凭据 · 未自动注册 · 未绕过验证 · 未伪造凭据
```
