# V3 现货黄金数据层正式接入与历史研究重算前置审计

`ts_utc = 2026-09-25T02:19:53.223312+00:00` · **最终状态：`V3_XAU_SPOT_CONDITIONAL`**

```text
V3_ROUND3_COMPLETE_NO_CANDIDATE（保持）· V3_FORWARD_READY = FALSE · V3_STRATEGY_FORWARD = NOT_ENABLED
V3_LIVE_ALLOWED = NO · ORDER_SEND = 0 · FORWARD = 0 · LIVE = 0
本任务未新增假设、未重算、未开启任何后置流程
```

## 一、核心问题的回答

**Q1：这条 20 年 XAUUSD 现货日线能否在不破坏现有研究边界的情况下，正式成为 V3 的主黄金研究序列？**

> **可以成为"研究工作序列"，但状态是 CONDITIONAL，不是 READY。**
> 建立 `V3_XAU_SPOT_DAILY`，designation = **CANDIDATE_PRIMARY (CONDITIONAL)**：
> 数据可用（完整性好、国内可自动获取、20 年、OHLCV），但**定义、PIT、时间口径三项均存在关键不确定性**：
> - `XAU_DEFINITION = CONDITIONAL`（源端无机器可读元数据，无法从源头确认 instrument 定义）
> - `PIT_STATUS = PIT_CONDITIONAL`（任务明令不得升级为 PIT_PASS）
> - `bar_close_definition = UNKNOWN`（提供商未文档化日线切分时点）
> 因此 §18 判定为 **B：V3_XAU_SPOT_CONDITIONAL**，而非 A。

**Q2：哪些既有研究需要重算，哪些完全不需要？**

> **不需要重算：Round 1（12 条）+ Round 2（11 条）= 23 条** —— 它们使用 FXTM venue 自身的盘中数据，与 GC 代理无关。
> **需要（分三类）**：Round 3 的 8 条 —— 7 条 `RECOMMENDED_PENDING_AUTHORIZATION`（黄金腿由 GC 代理换成 XAU 现货），
> 1 条 `ELIGIBLE_NOW_FIRST_TEST`（H27 首次具备检验条件），1 条 `SPECIAL_REVALIDATION`（H30，按 §11 特殊处理）。
> **本任务不执行任何重算**（§19/§20：先冻结资格，下一步单独决定）。

## 二、数据源注册（§4）

```json
{
 "source_id": "SINA_GLOBALFUTURES_XAU_DAILY",
 "source_name": "新浪财经 全球期货/现货日线接口 (GlobalFuturesService.getGlobalFuturesDailyKLine)",
 "instrument": "XAU",
 "venue_or_definition": "commercial portal series; provider category = 全球期货/现货; contract months absent (continuous)",
 "url_or_endpoint": "https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_XAU/GlobalFuturesService.getGlobalFuturesDailyKLine?symbol=XAU",
 "access_method": "HTTPS GET (JSONP); header Referer=https://finance.sina.com.cn",
 "china_intranet_access": "YES (direct; no VPN/proxy/relay)",
 "authentication": "NONE required",
 "frequency": "daily",
 "start_date": "2006-09-25",
 "end_date": "2026-09-25",
 "rows": 5186,
 "timezone": "UNKNOWN (provider does not state bar timezone; bar dates are trading dates)",
 "bar_close_definition": "UNKNOWN (no provider documentation of daily cutoff; must assume end-of-trading-day)",
 "OHLCV_fields": [
  "close",
  "date",
  "high",
  "low",
  "open",
  "position",
  "s",
  "volume"
 ],
 "raw_sha256": "1e946fa8df2a85fd892b62f102b51e86309ca3486da518190e5a6e47e91e3ee7",
 "download_timestamp": "2026-09-25T02:19:53.223312+00:00",
 "http_status": 200,
 "availability_rule": "PIT: daily bar dated D -> available at D+1 00:00:00Z (conservative; same rule as the V3 PIT layer)",
 "PIT_status": "PIT_CONDITIONAL",
 "limitations": [
  "commercial portal, NOT an official venue; restatement risk",
  "no provider metadata confirming instrument definition (see definition audit)",
  "bar timezone/cutoff undocumented",
  "zero volume/position fields (spot-style) - cannot validate traded volume",
  "cross-provider discrepancies vs GC=F up to ~85 USD (see alignment audit)"
 ],
 "must_not_upgrade": "PIT_CONDITIONAL must NOT be upgraded to PIT_PASS by this task",
 "raw_sha256_first_observed": "12e225cc5d4a1d1445e97a47a286a8f16114bf31f673daf4e8d30c2e785a33d8",
 "raw_sha256_previous_run": "1e946fa8df2a85fd892b62f102b51e86309ca3486da518190e5a6e47e91e3ee7",
 "normalized_sha256": "902313acacf0e8ec4eb2256fc1f8f3848a762e07f813f7cfa4e8c8b06451f63b",
 "raw_payload_file": "research/v3_xau_spot_data/raw_sina_xau_daily.jsonp",
 "normalized_file": "research/v3_xau_spot_data/xau_spot_daily_normalized.json",
 "fetch_variance_note": "payload bytes differ between fetches (series updates and/or formatting); identity is anchored on the normalized file + download_timestamp, never on a single raw fetch"
}
```

**关键诚实记录**：原始载荷**逐次取数并不字节稳定**（首次观测 `12e225cc…`，本轮 `1e946fa8df2a85fd892b62f102b51e86…`），
因此身份锚定在**规范化文件 + 下载时间戳**，而不是某一次 raw 抓取。

## 三、XAUUSD 定义审计（§5）

```json
{
 "symbol": "XAU",
 "display_name": "现货黄金 / 伦敦金 (per provider category listing; not machine-readable)",
 "source_description": "endpoint family 'GlobalFuturesService'; provider pages list XAU under spot metals/precious metals. The quote endpoint hf_XAU returns a realtime quote block.",
 "instrument_type": "SPOT_LIKELY (no contract months; no volume; price level matches London gold spot)",
 "quote_field_sample": "var hq_str_hf_XAU=\"4289.35,4273.760,4289.35,4289.70,4295.66,4264.30,10:18:00,4273.76,4273.12,0,0,0,2026-09-25,伦敦金（现货黄金）\";\n",
 "quote_http_status": 200,
 "evidence": {
  "price_level_2006_09_25": "590.800",
  "reference_london_gold_spot_2006_09": "~580-600 USD/oz (consistent)",
  "price_level_last": "4294.430",
  "contract_months_present": false,
  "volume_nonzero_rows": 0,
  "position_nonzero_rows": 0
 },
 "XAU_DEFINITION": "CONDITIONAL",
 "why": "the provider exposes no machine-readable instrument metadata; definition is inferred from naming, category listing, absence of contract months and price-level consistency. Not confirmable from the source itself -> per task §5 the definition is recorded as CONDITIONAL."
}
```

**结论：`XAU_DEFINITION = CONDITIONAL`** —— 从命名、"现货/贵金属"类目、无合约月份、价格水平与伦敦金一致的**间接证据**看，
最可能是 **XAU/USD 现货**；但**源端没有可机读的定义元数据**，因此不认定为 CONFIRMED。

## 四、时间与价格完整性（§6）

```text
行数 5186 · 起止 2006-09-25 → 2026-09-25
重复日期 0 · 周末行 0 · 非正价格 0
OHLC 异常：open 越界 128 行（其中 open == 前收 2 行）· close 越界 9 行
跳点(>8%) 3 个 · 长断档(>5天) 2 个
分段计数：{
 "2006-2010": 1101,
 "2011-2015": 1302,
 "2016-2020": 1300,
 "2021-2026": 1483
}
```

```json
[
 {
  "date": "2012-12-25",
  "open": 1660.69,
  "low": 1656.51,
  "high": 1657.01,
  "open_eq_prev_close": false
 },
 {
  "date": "2013-01-01",
  "open": 1660.84,
  "low": 1654.73,
  "high": 1655.23,
  "open_eq_prev_close": false
 },
 {
  "date": "2013-03-29",
  "open": 1596.71,
  "low": 1608.2,
  "high": 1608.7,
  "open_eq_prev_close": false
 },
 {
  "date": "2012-12-25",
  "close": 1658.79,
  "low": 1656.51,
  "high": 1657.01
 },
 {
  "date": "2013-01-01",
  "close": 1660.84,
  "low": 1654.73,
  "high": 1655.23
 },
 {
  "date": "2013-03-29",
  "close": 1596.95,
  "low": 1608.2,
  "high": 1608.7
 }
]
```

**处理规则（确定性，不删除任何行）**：全部保留并标记；open 越界的成因（提供商 open 口径 vs 数据错误）记
**UNRESOLVED**；无周末行、无重复、无非正价格，故不需要任何删除型规则。

**分段稳定性审计框架（§14）**：2006–2010 / 2011–2015 / 2016–2020 / 2021–2026 的分段计数已记录（见上），
仅作**稳定性审计**使用；**不得用于事后挑选最佳区间**；样本不足的分段将来只能记 `INSUFFICIENT_SAMPLE`，不得删除。

## 五、与 GC=F 的数据层对齐（§7）

```json
{
 "n": 400,
 "mean": -19.41,
 "min": -123.8,
 "max": 115.29,
 "stdev": 29.24
}
```

```text
共同日期 vs GC=F: 2514 · 日收益相关性: 0.9017
日收益差: {
 "n": 2513,
 "mean": -0.073,
 "stdev_bp": 46.57
}
已知个案 2026-09-16: {
 "date": "2026-09-16",
 "xau_close": 4263.94,
 "gc_f_close": 4387.5,
 "diff": -123.56
}
```

**个案调查结论：`UNRESOLVED_DEFINITION_DIFFERENCE`** —— 该差异（以及 −124 ~ +115 USD 的整体离散）**不能**由已知的
合约换月窗口、结算快照、连续合约构造或时区规则解释；按 §7 **不强行解释**。
**后果**：XAU 现货与 GC=F 被当作**两条不同序列**，永不混用、永不在同一信号中相减，跨源比较必须披露。

## 六、新的黄金主数据集（§8）

```json
{
 "schema": "v3_xau_spot_dataset_manifest/1",
 "ts_utc": "2026-09-25T02:18:14.000857+00:00",
 "dataset_id": "V3_XAU_SPOT_DAILY",
 "designation": "CANDIDATE_PRIMARY (CONDITIONAL)",
 "status_reason": "established as the working gold RESEARCH series, but NOT unconditionally 'PRIMARY_READY' because XAU_DEFINITION=CONDITIONAL, bar timezone/cutoff UNKNOWN, and PIT=PIT_CONDITIONAL",
 "rows": 5186,
 "start": "2006-09-25",
 "end": "2026-09-25",
 "availability_rule": "PIT: daily bar dated D -> available at D+1 00:00:00Z (conservative; same rule as the V3 PIT layer)",
 "raw_sha256": "1e946fa8df2a85fd892b62f102b51e86309ca3486da518190e5a6e47e91e3ee7",
 "normalized_sha256": "902313acacf0e8ec4eb2256fc1f8f3848a762e07f813f7cfa4e8c8b06451f63b",
 "gc_f_role": "SEPARATE_VARIABLE (gold futures); GC=F is no longer used as the XAUUSD substitute",
 "no_mixing_rule": "XAU spot and GC=F must never be mixed in one signal definition; never differenced for signals",
 "qualification": "RESEARCH_ONLY; not an execution-venue series; must not be used for order pricing",
 "raw_payload_file": "research/v3_xau_spot_data/raw_sina_xau_daily.jsonp",
 "normalized_file": "research/v3_xau_spot_data/xau_spot_daily_normalized.json",
 "download_timestamp": "2026-09-25T02:19:53.223312+00:00"
}
```

```text
数据集: V3_XAU_SPOT_DAILY（CANDIDATE_PRIMARY, CONDITIONAL）
  raw      : research/v3_xau_spot_data/raw_sina_xau_daily.jsonp  sha256=1e946fa8df2a85fd892b62f102b51e86…
  normalized: research/v3_xau_spot_data/xau_spot_daily_normalized.json  sha256=902313acacf0e8ec4eb2256fc1f8f384…
可用性规则: PIT: daily bar dated D -> available at D+1 00:00:00Z (conservative; same rule as the V3 PIT layer)
GC=F 角色 : 独立黄金期货变量（不再作为 XAUUSD 替代序列）
```

## 七、历史重算矩阵（§9–§11）

```json
{
 "no_recompute": 23,
 "eligible_now_first_test": 1,
 "special_revalidation": 1,
 "recommended_pending": 6,
 "total": 31
}
```

| 研究 | 黄金腿依赖 | 判定 |
|---|---|---|
| Round 1 H01–H12（12 条） | NO（FXTM 盘中） | **不需重算** |
| Round 2 H13–H23（11 条） | NO（H21 仍缺 PIT 宏观，非黄金数据阻塞） | **不需重算** |
| Round 3 H24/H25/H26/H28/H29/H31（6 条） | YES（GC 代理） | RECOMMENDED_PENDING_AUTHORIZATION |
| Round 3 H27 | YES（目标序列此前缺失） | **ELIGIBLE_NOW_FIRST_TEST** |
| Round 3 H30 | YES（GC 代理） | **SPECIAL_REVALIDATION**（§11） |

### H27 特别处理（§10）
```text
保持 H27 原 hypothesis / signal / threshold / 成本规则【不变】；
仅替换此前因数据不足而等待的数据基础（XAU 现货日线现已存在）。
"重新评估资格" ≠ Candidate。
```

### H30 特别处理（§11）
```text
阈值不得修改；若重算：须新冻结数据版本 + 重算 effective_n + 时间序列验证 + 成本压力 + FDR。
旧的 GC 代理结果（+91.19 bp, n=13）作为历史结果保存，【不得】与新结果合并。
```

## 八、Round 3 旧结论保护（§12）

```text
research/v3_strategy_round3/ 未改动（immutable）；Round 3 结果仍在 round3_results.json
新计算目录已预备：research/v3_strategy_revalidation_xau/（含 protocol + data_version_freeze，未执行重算）
```

## 九、统计规则冻结（§13）与 20 年数据要求（§14）

```json
{
 "schema": "v3_revalidation_protocol/1",
 "ts_utc": "2026-09-25T02:18:14.000857+00:00",
 "scope": "prepared for a future, separately-authorised recomputation; NOT executed by this task",
 "methods_must_equal_round3": {
  "cost": "0.914 bp anchor; stress 0/1/2/3x",
  "oos": "time-ordered 3-fold walk-forward (0-40/40-70/70-100%)",
  "bootstrap": "block bootstrap (block=5, 2000 iters) CI95",
  "permutation": "1500 iters vs unconditional pool",
  "regime": "volatility tercile + weekday",
  "multiple_testing": "BH-FDR q=0.05, cumulative count preserved",
  "entry_exit": "signal from bar t (available t+1 00:00Z) -> entry close(t+1) -> exit close(t+2)"
 },
 "forbidden": [
  "parameter re-tuning",
  "threshold re-selection",
  "cost-anchor changes",
  "adding favourable regimes",
  "deleting unfavourable years"
 ],
 "segment_stability_audit": [
  "2006-2010",
  "2011-2015",
  "2016-2020",
  "2021-2026"
 ],
 "segment_policy": "stability audit ONLY; segments are never used to cherry-pick; insufficient segments are reported as INSUFFICIENT_SAMPLE, never deleted",
 "output_dir": "research/v3_strategy_revalidation_xau/"
}
```

## 十、质量与市场结构变化记录（§15）

```text
报价体系变化 / 数据源格式变化 / 交易时间变化 : UNKNOWN（提供商不发布元数据）
异常年份/极端事件 : 已记录 3 个 >8% 单日跳点（未删除）
结构性断点 : 已记录 2 个 >5 天断档（未删除）
禁止行为 : 未为消除不利结果删除任何年份 ✓
```

## 十一、禁止事项核查（§16）

```text
未开 Round 4 ✓ · 未新增假设 ✓ · 未做参数搜索/阈值优化 ✓ · 未进 Forward/Shadow/Demo/Live ✓ · ORDER_SEND=0 ✓
未修改 Risk Layer / Execution Adapter / Calibration / Calibration Ledger / V1 / V2 ✓
```

## 十二、最终状态（§18）与停止条件（§19）

```text
V3_XAU_SPOT_CONDITIONAL
（可研究，但 instrument definition / PIT / 时间口径仍有关键不确定性；不得升级 PIT 等级）
未自动开启 Round 4 / Forward / Shadow / 下单。
下一步（是否按冻结协议执行重算）需单独授权。
```

## 十三、最终原则（§20）

> 本任务不寻找 Candidate。它回答的是：**我们是否拥有一条足够可靠、20 年长度、国内可自动化的 XAUUSD 现货研究序列，
> 以及哪些既有研究因此获得重新验证资格。**
> 答案：**"有一条可用的（CONDITIONAL）序列，并冻结了重算资格与协议"** —— 记录能力升级、冻结结果、停止。
