# V3 金十 PIT × 长历史 XAUUSD 数据能力审计报告

`ts_utc = 2026-09-25T09:07:06.449875+00:00`

## Executive Summary

```text
核心问题：中国内网是否存在可 Python 自动化获取、具备长历史覆盖的 XAUUSD 1m/tick 源？
答案    ：【没有】—— 本机【已有】一条 16 年的 1m 本地数据（Dukascopy），但其提供方在中国内网不可达，
          因此链路【不可复现】；其余国内源均无盘中长历史。
最终判定：V3_LONG_XAUUSD_HISTORY_PARTIAL
```

## Jin10 PIT Status

```text
JIN10_EVENT_PIT_FEASIBILITY = PASS（pub_time = Asia/Shanghai，UTC = pub_time - 8h；三点独立校准）
JIN10_LONG_HISTORY_MARKET_PRICE = UNRESOLVED（金十 kline 最多 100 根近期 1m，历史窗口 0 行）
事件层已正式化：V3_JIN10_EVENT_PIT.json · 事件 158 条 · raw_hash=0c9c6ceabdec281d… · 未做任何信号计算
```

## Candidate Sources（15 问记录见 source_registry.json）

| 源 | 类别 | 中国内网 | 自动化 | 历史 | 早→晚 | 频率 | XAU 定义 | 判定 |
|---|---|---|---|---|---|---|---|---|
| DUKASCOPY_XAUUSD | C_LOCAL_ASSET | NO_FOR_NEW_DOWNLOADS(asset is already local) | True | True | 2010-01→2026-08-04 | 1m candles + partial ticks | E_CFD_XAUUSD_DUKASCOPY | PARTIAL |
| FXTM_LIVE_STAGING | C_LOCAL_ASSET(broker venue) | True | True | True | 2026-08-04→2026-09-25 | tick | E_CFD_XAUUSD_FXTM | PARTIAL(short) |
| JIN10_MCP_KLINE | A_CN_OFFICIAL_PLATFORM | True | True | False | n/a→n/a | 1m (100 bars max) | F_OTHER(platform gold quote) | BLOCKED(no history) |
| SINA_MINIKLINE | A_CN_PLATFORM | True | True | False | n/a→n/a | none returned | UNKNOWN | BLOCKED |
| SINA_GLOBALFUTURES_DAILY | A_CN_PLATFORM | True | True | True | 2006-09→2026-09 | 1d | F_OTHER(XAU daily, portal) | BLOCKED(daily only) |
| EASTMONEY | A_CN_PLATFORM | True | False | False | n/a→n/a | n/a | UNKNOWN | BLOCKED(unreliable) |
| STOOQ | OVERSEAS | False | False | False | n/a→n/a | n/a | UNKNOWN | BLOCKED(JS challenge) |
| YAHOO | OVERSEAS | False | False | False | n/a→n/a | 1m only ~7d | C_OTC? (GC=F futures 1m) | BLOCKED(HTTP 403) |
| SHFE | A_CN_OFFICIAL | True | False | False | n/a→n/a | n/a | D_FUTURES_CNY | BLOCKED(404) |
| SGE | A_CN_OFFICIAL | True | False | True | n/a→n/a | 1d (page) | F_OTHER(CNY gold) | BLOCKED(html/daily/CNY) |

## Source Comparison / XAU Definition Audit

```text
DUKASCOPY_XAUUSD : XAU_DEFINITION = E_CFD_XAUUSD_DUKASCOPY（依据本机脚本 dukascopy.py / duka_assemble.py 明确声明）
  · 不是 FXTM venue · 不是 COMEX GC 期货 · 不是 ETF → 严禁与任何其它源拼接（§八/§十六）
  · 价格编码：整数 ×1000（SCALE=1000，见脚本注释）
  · FXTM_LIVE/STAGING = E_CFD_XAUUSD_FXTM（另一券商 CFD，定义不同）
  · 金十/新浪/东财/上金所：品种定义 UNKNOWN 或非 XAUUSD 现货；不得推断
```

## Historical Coverage

```text
candles : 179 个月档 · 2010-01 → 2026-08 · 唯一分钟合计 7233120
  按年分钟：{"2010": 470880, "2011": 462240, "2012": 473760, "2013": 470880, "2014": 470880, "2015": 470880, "2016": 473760, "2017": 470880, "2018": 383040, "2019": 470880, "2020": 473760, "2021": 470880, "2022": 470880, "2023": 286560, "2024": 319680, "2025": 460800, "2026": 132480}
  缺口：2018(81%) · 2023(61%) · 2024(68%) · 2026 至 08-03
ticks   : 147 档 · 31127936 行 · 仅 ['202309', '20230901'] … ['20260803', '20260804']（稀疏，非连续）
```

## Timestamp Audit（本次审计最重要的新发现）

```text
candles : day(YYYY-MM-DD) + sec(日内秒偏移) —— 自明，但 BAR_CLOSE_DEFINITION = UNKNOWN（sec 标的是开盘还是收盘，仓储内无文档）
ticks   : 时间语义【无法用文件名日期 + hour + ms 重建】
  证据：还原后 DUKA ≈ 4480.27 USD vs 同日 FXTM 4051.625 USD → 差 10.58%
  而该价位对应的是【更晚的时期】→ 文件名日期可能是下载日/或 hour 非 UTC 小时
  => TIMESTAMP_SEMANTICS = UNRESOLVED（§九：绝不假定）
  => 该 tick 档【不得用于事件窗口对齐】，直到语义被独立证实
```

## Data Quality

```text
抽样 candles_201803：无 NaN · 无非正价 · 无 OHLC 违规 · 最大间隔 60s · 无周末行 · >1% 跳变 1 次
抽样 ticks_20240106：bid/ask 无 NaN 无 非正价
异常处理：全部【保留 + 标记 + 解释】，未删除、未修复、未插值（§十）
```

## Reproducibility

```text
本地重读：SHA256 稳定（两次读取一致）
网络重下载：【不可能】—— 中国内网对 Dukascopy 三台主机全部 TCP/TLS 超时：
    dukascopy_datafeed : dns=['192.133.77.189', '2001::42dc:9491'] · tcp/tls: TimeoutError: timed out
    dukascopy_main : dns=['108.160.166.61', '2001::1f0d:5709'] · tcp/tls: TimeoutError: timed out
    dukascopy_freeserv : dns=['199.59.148.222', '2001::a2dc:ce2'] · tcp/tls: TimeoutError: timed out
=> 结论：RAW_LOCAL_STABLE_REACQUISITION_IMPOSSIBLE（未伪装成完全稳定，§十二）
```

## FXTM Cross Validation（已修正 v1 的错误）

```text
v1 错误：把未缩放的 Dukascopy 整数价与 FXTM 美元价直接相减 → 均值差 4.45e6（已在 v2 撤回）
v2 修正：应用仓储自述的 SCALE=1000 后对比
  DUKA≈4480.27 · FXTM=4051.625 · 差 428.645 USD (10.58%)
  该差异【不是】可接受的报价差，而是时间对齐未解决的表现 → TIMESTAMP_ALIGNMENT = UNRESOLVED
禁止：任何拼接/合并（定义不同）
```

## Event Coverage Simulation（只做覆盖，不做任何收益统计）

```text
金十事件 158 条 → 市场覆盖检查：
  FXTM_1M 覆盖：158 条（事件窗口 2026-09-21..26 落在 FXTM 覆盖期内）
  DUKASCOPY_1M 覆盖：0 条（Dukascopy candles 只到 2026-08-03，且 tick 语义未解决）
  无任何市场覆盖：0 条
未计算：mean return / win rate / profit factor / Sharpe / alpha（§十四禁止）
```

## Known Gaps

```json
[
 "acquisition_requires_overseas_network",
 "tick_timestamp_semantics_unresolved",
 "coverage_gaps_2018_2023_2024",
 "bar_close_definition_unknown"
]
```

```text
READY 九项核对：{"china_intranet": false, "automatable": true, "xau_definition_clear": true, "at_least_2020": true, "has_1m_or_tick": true, "timestamp_clear": false, "quality_auditable": true, "raw_savable": true, "repeatable": false}
未满足：china_intranet(再获取) · timestamp_clear · repeatable
```

## Final Verdict

```text
V3_LONG_XAUUSD_HISTORY_PARTIAL
```

**对下一阶段的直接回答**：以【当前】数据基础，V3 可以做的事件窗口研究仅限于
【2026-08-04 → 2026-09-25 的 FXTM venue 数据】；无法做多年事件窗口研究，
因为长历史本地资产（Dukascopy）无法再获取、且其 tick 时间语义尚未解决。

## 合规（§二十/§二十一）

```text
未创建新假设 · 未重算 H22 · 未 Round4 · 未 Forward/Shadow/Live · 未下单
未修改 H01–H31 · 未修改 V1/V2/V3 数据 · 未修改 execution adapter / calibration ledger / Round1-3 结果
未拼接不同定义数据源 · 未删除异常 · 未用最终修订值冒充历史实时值 · 未忽略 timestamp 定义
未为扩大样本人为复制事件 · 未计算任何收益/胜率/Sharpe/alpha
```

---

## 更正（重要）：MT5 原生历史深度

本报告早期版本称「MT5 原生历史在全部周期返回 0 行」——**这是错的**，原因是我探针的两个 bug：

```text
① 对【非 portable】的 V1 主终端误传 portable=True（其数据实际在 AppData，我据此扫错了目录）
② count 请求 100,000–300,000 时 MT5 静默返回 0 行（本 build 的 API 特性）
```

修正后实测（FXTM 终端，只读）：

| 周期 | 可得深度 | 证据 |
|---|---|---|
| D1 | **22.3 年** | 5,729 根，2004-06-11 → 2026-09-25 |
| H1 | **10.7 年** | range from 2016-01-04 → 61,316 根 |
| M5 | 0.7 年 | 50,000 根 → 2026-01-12 |
| M1 | **仅 ~7 周** | 50,000 根 → 2026-08-05；range from 2026-01-01 → 0 行 |

```text
对核心问题的修正回答：
  长历史 1m / tick  ✗ 本 venue 不可得（仅约 7 周）
  长历史 H1 / D1    ✓ 【可得】· venue 正确（FXTM 自身）· 中国内网可达 · 可自动化 · 无需新依赖
对 V3 的含义：
  · 多年研究在 H1/D1 尺度上【是可行的】，且用的是执行 venue 自己的数据（此前只能用 Dukascopy/GC 代理）
  · 分钟级事件窗口研究仍受限于最近约 7 周
  · 结论等级仍为 PARTIAL（长历史 1m 未解决），但 PARTIAL 的性质已改变：不再是「只能靠代理」，
    而是「1m 不行、H1/D1 可以」
```

同时撤回探针早期把 V1 本地历史库判为「0 个 XAUUSD 目录」的结论：V1 的 XAUUSD 历史文件实际约 1.5 GB（在 AppData 路径下），我当时扫的是 exe 目录。


---

## 后续：Dukascopy M1 时间语义审计结论

```text
DUKASCOPY_CANDLE_TIMESTAMP_SEMANTICS = UNRESOLVED
  A 时区：代码断言 UTC，但独立交叉验证失败（三种方法均无法与 FXTM 对齐）
  B 分钟身份：RESOLVED（day+sec；1440 根/日；00:00..23:59；全为 60 的倍数）
  C bar open/close：UNKNOWN（无文档；结构证据仅倾向区间起点；无分钟级独立源）
  附加：2025 年 32.5% 行为平盘占位 bar，46/320 天完全平盘
=> 该资产降级为 REFERENCE_ONLY，禁止进入 V3 正式事件研究
=> V3 长历史 M1 缺口仍然存在
```
