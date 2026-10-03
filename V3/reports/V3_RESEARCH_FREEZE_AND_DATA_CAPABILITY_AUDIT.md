# V3 研究冻结 + 中国内网数据能力升级审计报告

`ts_utc = 2026-09-25T02:11:46.868703+00:00`

**final_status = `V3_DATA_CAPABILITY_UPGRADE_FOUND`**

`V3_ROUND3_COMPLETE_NO_CANDIDATE`（不变）· `V3_FORWARD_READY = FALSE` · `V3_STRATEGY_FORWARD = NOT_ENABLED` · `V3_LIVE_ALLOWED = NO` · `ORDER_SEND = 0`

---

# 目标 A：研究资产冻结审计

```text
git HEAD = 2ac9ea7
24 项资产全部存在并已计算 sha256（无缺失）
冻结资产未提交改动 = []
意外新增研究文件   = []
trader_v3 工作区   = 4 项，均非冻结资产
```

## 关键哈希清单

| 资产 | sha256(前16) | bytes |
|---|---|---|
| round1_registry | `c2290c1042903764` | 9151 |
| round2_registry | `9d6727b8212c59b0` | 9846 |
| round3_registry | `b267ba06415b0c1c` | 11161 |
| round3_hash_file | `f54f309e26f9af08` | 207 |
| round1_report | `8bd15583b79763b9` | 11847 |
| round2_report | `2bb05f261826eea4` | 14818 |
| round3_report | `4f4b08fc937c1786` | 8101 |
| pit_report | `07031b38b42b3fa8` | 7010 |
| jin10_report | `51239cde049eb920` | 6803 |
| calibration_report | `d660f4a3741e9512` | 8295 |
| pit_registry | `c1caaa460a7a6578` | 5445 |
| pit_source_audit | `43412226ff85a1f9` | 17722 |
| jin10_registry | `4151084b88777268` | 6183 |
| risk_layer | `29a0a94aa9cbe1c0` | 8842 |
| execution_adapter | `b207ce1903d1ca6b` | 8148 |
| calibration_pilot | `1b2e91803e7b7169` | 33420 |
| strategy_signals | `066cbb0985de55c2` | 6791 |
| strategy_contracts | `ce58df7721fecbcd` | 2621 |
| strategy_evaluate | `291da65f740c5b94` | 2513 |
| pit_replay | `d1b0eca44e272384` | 5717 |
| entry_exit_interface | `4518aa24d62e068c` | 2180 |
| calibration_ledger | `6dce585100402976` | 43707 |
| round3_results | `f0197f7d21ce9ca6` | 11765 |
| round3_dataset_meta | `1ac2e5b58f48eb97` | 3086 |

## 状态闸门（全部正确）

```text
V3_EXECUTION_MODE=DEMO_CALIBRATION · V3_ORDER_SEND_ALLOWED=YES
V3_LIVE_ALLOWED=NO · V3_FORWARD_ALLOWED=NO · V3_STRATEGY_FORWARD=NOT_ENABLED
```

## 研究资产状态确认

```text
Round1/2/3 registry 未修改 ✓ · H21/H22/H23 仍为 NOT_TESTABLE ✓ · H30 仍为 UNVERIFIED_RESEARCH_DIRECTION ✓
Risk Layer / Execution Adapter / Calibration Ledger 未改变 ✓ · Forward / Live 始终关闭 ✓
```

## §13 V1/V2 隔离

```text
本任务窗口内被改写的 V1/V2 代码 = []
对 trader_v1/trader_v2 的 import = []
未读取 V1/V2 runtime state 作为研究数据 ✓
```

---

# 目标 B：中国内网数据能力审计

```text
候选数 = 17（上限 20，未凑数）
状态分布 = {"ACCESS_BLOCKED": 4, "PIT_CONDITIONAL": 8, "NOT_AVAILABLE": 1, "PIT_FAIL": 2, "AUTOMATION_FAILED": 2}
```

| source_id | category | 中国内网 | 历史 | 状态 | 说明 |
|---|---|---|---|---|---|
| NBS_API | CN_OFFICIAL | TCP/TLS_FAIL | false | ACCESS_BLOCKED | URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certif |
| NBS_SITE | CN_OFFICIAL | TCP/TLS_FAIL | false | PIT_CONDITIONAL | reachable HTTP 200 with default TLS (first-pass SSL error was tr |
| PBOC_SITE | CN_OFFICIAL | TCP/TLS_FAIL | false | PIT_CONDITIONAL | reachable HTTP 200; gold-reserve pages are documents, no API/pub |
| SAFE_SITE | CN_OFFICIAL | TCP/TLS_FAIL | false | PIT_CONDITIONAL | reachable HTTP 200; monthly reserve documents, no API/publicatio |
| CHINABOND | CN_OFFICIAL | TCP/TLS_FAIL | false | PIT_CONDITIONAL | reachable HTTP 200; CNY yield curves exist but no API/publicatio |
| SGE_SITE | CN_OFFICIAL | TCP/TLS_FAIL | false | PIT_CONDITIONAL | reachable HTTP 200; daily quotes exist; no API/publication_time  |
| SGE_QUOTES | CN_OFFICIAL | TCP/TLS_FAIL | false | ACCESS_BLOCKED | URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certif |
| SHFE_DAILY | CN_OFFICIAL | HTTP_404 | false | NOT_AVAILABLE | HTTP 404 |
| SHFE_SITE | CN_OFFICIAL | DNS_OK | true | PIT_CONDITIONAL | market/page data reachable, but no publication_time and no vinta |
| CFFEX | CN_OFFICIAL | TCP/TLS_FAIL | false | ACCESS_BLOCKED | timed out on repeat (kept BLOCKED) |
| CHINAMONEY | CN_OFFICIAL | DNS_OK | true | PIT_CONDITIONAL | market/page data reachable, but no publication_time and no vinta |
| SINA_QUOTE | CN_COMMERCIAL | DNS_OK | false | PIT_FAIL | reachable but no historical series in payload (quote/page only) |
| SINA_KLINE | CN_COMMERCIAL | DNS_OK | true | PIT_CONDITIONAL | verified: 2,262 daily rows since 2006-09-25 for spot XAU; automa |
| EM_KLINE_XAU | CN_COMMERCIAL | DNS_OK | true | AUTOMATION_FAILED | connection closed without response on verification; not confirme |
| EM_KLINE_GC | CN_COMMERCIAL | DNS_OK | true | AUTOMATION_FAILED | connection closed without response on verification; not confirme |
| TX_KLINE | CN_COMMERCIAL | TCP/TLS_FAIL | false | ACCESS_BLOCKED | DNS resolution failed for web.ifzq.gtimg.cn |
| TX_QUOTE | CN_COMMERCIAL | DNS_OK | false | PIT_FAIL | reachable but no historical series in payload (quote/page only) |

## 首轮误判与修正（诚实记录）

```text
1) 官方站点（统计局/央行/外管局/中债/上金所）首轮报 SSL 失败，复核后默认 TLS 下全部 HTTP 200 -> 瞬态误报，已改判
2) 东方财富 K 线首轮宽松判据误报 hist=true；复核 RemoteDisconnected -> 改判 AUTOMATION_FAILED
3) 我自己的 cross-check 首次因变量作用域错误空跑 -> 本报告已修正并重跑
```

## 交叉验证（修复后）

```json
[
 {
  "date": "2026-09-16",
  "sina_GC_close": 4302.4,
  "yahoo_GC_F_close": 4387.5,
  "diff": -85.1
 },
 {
  "date": "2026-09-17",
  "sina_GC_close": 4380.6,
  "yahoo_GC_F_close": 4399.7,
  "diff": -19.1
 },
 {
  "date": "2026-09-18",
  "sina_GC_close": 4415.9,
  "yahoo_GC_F_close": 4424.9,
  "diff": -9.0
 },
 {
  "date": "2026-09-21",
  "sina_GC_close": 4380.8,
  "yahoo_GC_F_close": 4383.9,
  "diff": -3.1
 },
 {
  "date": "2026-09-22",
  "sina_GC_close": 4395.8,
  "yahoo_GC_F_close": 4376.4,
  "diff": 19.4
 },
 {
  "date": "2026-09-23",
  "sina_GC_close": 4322.7,
  "yahoo_GC_F_close": 4318.4,
  "diff": 4.3
 },
 {
  "date": "2026-09-24",
  "sina_GC_close": 4310.0,
  "yahoo_GC_F_close": 4298.0,
  "diff": 12.0
 },
 {
  "date": "2026-09-25",
  "sina_GC_close": 4323.8,
  "yahoo_GC_F_close": 4327.8,
  "diff": -4.0
 }
]
```


**实测结论（非模板假设）**：多数交易日差异在 -19 ~ +19 USD 之间，但 **2026-09-16 差 -85.1 USD** → 两者存在**合约换月/收盘快照口径差异**，并非同一定义序列。
因此：该端点可用于**日线尺度研究**；**不得**当作精密价格源，也不得与其它供应商序列直接混算价差；跨源差异必须显式披露。

---

# 核心发现：P0「现货黄金历史日线」已解决（市场价层面）

```text
source  : SINA_KLINE (GlobalFuturesService.getGlobalFuturesDailyKLine, symbol=XAU)
序列    : XAU 现货黄金日线 OHLCV（USD）
行数    : 5186
覆盖    : 2006-09-25 -> 2026-09-25（约 20 年）
末行    : open 4273.120 / high 4295.660 / low 4264.300 / close 4294.430
可行性  : 中国内网直连 ✓ · 无 VPN/代理 ✓ · Python 自动获取 ✓ · 无凭据 ✓
PIT     : PIT_CONDITIONAL（市场序列，availability=bar 收盘；日线粒度）
raw_sha256 : 12e225cc5d4a1d1445e97a47a286a8f16114bf31f673daf4e8d30c2e785a33d8
```

## 边界（否则就是过度声称）

```text
1) 商业门户序列，非官方交易所；复述/调整风险；不得与 FXTM 执行 venue 混用而不披露
2) 只解决【现货黄金日线历史】；宏观 PIT / vintage / 新闻 PIT / 日历 PIT 仍全部未解决
3) 它是市场价序列，不是宏观 PIT 源，不能冒充发布时刻可得性
4) 不构成任何交易机制、Candidate、Forward 或 Live 许可
5) 跨源校验显示换月/快照口径差异（最大 85 USD）→ 日线研究可用，精密定价不可用
```

## §15 最终判定

```text
V3_DATA_CAPABILITY_UPGRADE_FOUND
依据：存在至少一个真正显著改善『现货黄金历史数据』缺口的源（SINA XAU 日线，20 年，中国内网可自动获取）
同时：宏观 PIT 类缺口（P0/P1）仍全部未解决
```

## §16 停止条件

```text
未继续 Round 4。研究状态保持 V3_ROUND3_COMPLETE_NO_CANDIDATE / FORWARD_READY=FALSE / FORWARD=NOT_ENABLED / LIVE=NO
未下单、未进 Shadow/Forward/Demo/Live、未新增交易假设、未修改任何冻结资产
```

## 结论

> 冻结审计干净；现货黄金日线（20 年）能力缺口已由国内可达、免凭据、可自动化的端点解决；宏观 PIT / vintage / 新闻 / 日历四类缺口仍然存在。部分升级 + 明确剩余缺口，不是继续研究的通行证。