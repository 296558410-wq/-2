# V3 全球 XAUUSD 1m 数据源重新发现与验证报告

`ts_utc = 2026-09-25T09:47:15.545056+00:00` · 任务 `V3_GLOBAL_XAUUSD_1M_DATA_SOURCE_REDISCOVERY`

**未购买 · 未付款 · 未注册 · 未提交证件 · 未创建交易账户 · 未改 MT5 · 未下单**

## §二十五 十问直答

```text
1. 之前 BLOCKED 的源恢复情况？        多数恢复：dukascopy_www/stooq/yahoo/databento/truefx 均 200；
                                      但【datafeed.dukascopy.com 仍 TCP 超时】→ 真正的数据端点未恢复
2. 是否发现新的 XAUUSD 1m 源？        【是】HistData.com 免费 XAUUSD M1（无需账号/无需付费）
3. 是否实际成功下载 1m？              是 —— 3 个月共 79,285 行（2026-07/08/09）
4. 最长历史是多少？                   完整跨度【未核实】（厂商页有 2020/2022/2026 年份链接，未逐一枚举）
5. 哪些是真正 XAUUSD Spot/CFD？       HistData 的 XAUUSD 经验上与 FXTM 高度一致（0.966），但厂商未发布定义 → 归 H
6. 哪些其实是 GC/ETF？                Yahoo GC=F（class E）· Databento=COMEX GC（E）· GLD/ETF（F）→ 全部排除
7. 哪些 timestamp 已获官方定义？      无（HistData 官方 FAQ/terms/license 全部 404）
8. 哪些可 Python 自动化？             HistData【已验证可自动化】（tk+POST+ZIP+CSV，无认证）
9. 哪些 license 允许本地量化研究？    未确认（LICENSE_STATUS = UNKNOWN）
10. 是否出现至少一个 QUALIFIED？      【否】(定义/授权/绝对时区/完整跨度 四项未落实)
```

## 一、网络与路径（§四）

```text
实际路径 = DIRECT · proxy_used = False · vpn_used = False（未启用任何代理/VPN/跳板）
恢复：6/6 之前受阻主机恢复可达；仍阻：datafeed.dukascopy.com(TCP 超时) · yahoo XAUUSD=X(404) · fxcm(403) · tickstory(403)
```

## 二、新发现候选：HistData（唯一实际取到 1m 的）

```text
下载方式：GET 下载页取 tk → POST /get.php → ZIP → DAT_ASCII_XAUUSD_M1_<YYYYMM>.csv
格式    ：YYYYMMDD HHMMSS;open;high;low;close;volume
实测    ：2026-07 (31,414) · 2026-08 (29,437) · 2026-09 (19,164) = 79,285 行
          2026-07-01 00:00:00 → 2026-09-18 16:58:00
认证    ：无（无账号、无 key）· 采购要求：无（免费）
```

## 三、与 FXTM 交叉验证（§十八，最关键）

```json
{
 "best": {
  "offset_hours": 7,
  "n": 45482,
  "mean_diff": -0.3359,
  "median_diff": -0.335,
  "std_diff": 0.3423,
  "p01": -1.0506,
  "p99": 0.065,
  "max_abs_diff": 31.635,
  "return_corr": 0.96566
 },
 "minute_refinement": {
  "offset_minutes": 0,
  "n": 45482,
  "corr": 0.96566,
  "mean_diff": -0.3359
 },
 "verdict": "ALIGNED"
}
```

```text
结论：HistData 时间戳 +7 小时 与本地 FXTM 序列对齐，收益相关性 0.96566，分钟级最佳位移 0 分钟，价格均值差仅 -0.3359 USD。
说明：不同 CFD 经纪商报价不要求逐笔一致；−0.34 USD 的均值差远小于品种噪声 → 与「同一品种的两家报价」一致。
保留：+7h 是【相对】本地 FXTM ts_utc 序列测得的；若该序列实为服务器时间(UTC+3)，则 HistData 为 UTC−4(EDT)，
      与厂商常见说法(EST/EDT 不做 DST 调整)吻合。本任务【未完成】该绝对时区的最终消歧。
```

## 四、质量测试（§十七）

```json
{
 "rows": 79285,
 "duplicate_ts": 0,
 "nan": 0,
 "zero_or_neg_price": 0,
 "high_lt_low": 0,
 "high_lt_oc": 0,
 "low_gt_oc": 0,
 "median_step_s": 60.0,
 "gaps_gt_1h": 57,
 "jumps_gt_1pct": 5,
 "jumps_gt_3pct": 0
}
```
```text
0 重复 · 0 NaN · 0 非正价 · 0 OHLC 违规 · 步长 60s 严格 · 57 个 >1h 断档（周末休市）· 5 个 >1% 跳变（未删除，仅标记）
```

## 五、Dukascopy 重新审计（§六）

```text
datafeed.dukascopy.com → 仍 TCP/TLS 超时（无法重新下载小段做对照）
因此 DUKASCOPY_CANDLE_TIMESTAMP = UNRESOLVED 保持 · DUKASCOPY_16Y = REFERENCE_ONLY 保持
网络恢复 ≠ timestamp 自动 RESOLVED（按任务 §六 严格执行）
```

## 六、资格与采购闸门（§二十一/§二十三）

```text
QUALIFIED 0 · CONDITIONAL 4 · BLOCKED 2 · REJECTED 4
HistData = CONDITIONAL（1m 真实存在且可自动化；缺：官方定义/授权/绝对时区/open-close/完整跨度）
PURCHASE_REQUIRED = NO（免费）· PURCHASE = DO_NOT_PURCHASE
```

## 七、最终状态（§二十六）

```text
QUALIFIED = 0  →  V3_LONG_XAUUSD_HISTORY_PARTIAL 【保持不变】
V3_PROJECT_STATUS = CLOSED_NO_VALIDATED_EDGE · V3_DATA_STATUS = PARTIAL 保持
JIN10_EVENT_PIT = PASS 保持 · XAUUSD_LONG_1M = NOT_AVAILABLE 保持
DUKASCOPY_16Y = REFERENCE_ONLY 保持 · DUKASCOPY_TIMESTAMP = UNRESOLVED 保持
V3_FORWARD = OFF · V3_SHADOW = OFF · V3_LIVE = OFF · ORDER_SEND = 0 保持
```

## 八、人工下一步（不自动接入 V3）

```text
① 确认 HistData 的 instrument 定义与 price type（是否 XAUUSD Spot/CFD）
② 确认时间戳绝对时区与 DST、以及 bar 是 open 还是 close
③ 阅读并确认授权是否允许本地量化研究/回测/机器学习
④ 枚举 XAUUSD 最早可得的月份（判断能否满足 2020 甚至 2015）
以上四项落实前，HistData 只能是 CONDITIONAL，不得进入 V3 正式使用。
```