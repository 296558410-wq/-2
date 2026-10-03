# V3 Dukascopy M1 Candle 时间语义追溯审计报告

`ts_utc = 2026-09-25T09:29:43.831903+00:00` · 任务等级 `DATA_AUDIT_ONLY` · 纯只读

## 最终裁决

```text
DUKASCOPY_CANDLE_TIMESTAMP_SEMANTICS = UNRESOLVED
资产状态 = REFERENCE_ONLY（禁止进入 V3 正式事件研究；不得与 FXTM/GC 序列拼接）
```

## 三件事必须分开（§13）

| 项 | 结论 | 证据 |
|---|---|---|
| **A. 时区** | 代码断言 UTC，**独立验证未通过** | 多个解析器用 `to_datetime(day, utc=True)`；但三种方法的交叉验证均无法对齐 |
| **B. 分钟身份** | **RESOLVED** | `sec ∈ {0,60,…,86,340}`，每日恰好 1,440 根，逐分钟连续，无 86,400 |
| **C. bar open/close** | **UNKNOWN** | 无离线文档、解析器未声明；结构证据倾向「区间起点」但非证明；分钟级独立源不存在 |

## 追溯链（§四/§五/§六/§七）

```text
Dukascopy datafeed (HTTP, bi5/lzma)  →  scripts/dukascopy.py  decode_candles(>iiiiii) = t,open,close,low,high,vol
                                     →  scripts/duka_download.py  列名 sec/open/close/low/high/vol/side/day
                                        （day 取自 URL 请求日期；无任何时区转换；价格按 raw int 存盘）
                                     →  scripts/duka_assemble.py  ts = to_datetime(day, utc=True) + to_timedelta(sec,'s')
                                        SCALE=1000 应用于 mid/OHLC/spread；M1 不做 ±1min、不做 resample(label/closed) 改写
                                        （resample 仅用于派生 M5/H1）
git : 引入提交 04dfc40（单一提交，之后无提交改动 timestamp 构造）
```

## 结构验证（§八/§九）

```json
{
 "n": 187200,
 "unique_offsets": 1440,
 "min": 0,
 "max": 86340,
 "all_multiples_of_60": true,
 "contains_86400": false,
 "contains_0": true,
 "contains_86340": true,
 "interpretation_if_1440_per_day": "offsets 0..86340 with exactly 1440 per day means each calendar day carries bars stamped at 00:00..23:59 -> the stamp coincides with the INTERVAL START of the final bar of the day (a close-stamp series would need a 24:00/86400 stamp for its last bar)"
}
```

三个年代抽样（2010-01-01 / 2018-03-25 / 2026-07-01）：BID、ASK 各 1,440 根；首根 sec=0、末根 sec=86,340；逐分钟连续 ✓

## 独立交叉验证（§十二）——**失败**

```text
对象：2025 年 DUKA 真实 M1 → 小时收益  vs  FXTM MT5 H1 收益（MT5 时间为服务器时间，按偏移重贴标签换算 UTC）
结果：偏移 −6h … +7h 全部相关性 ≈ 0（最佳 +3h = 0.0224）
方法史：三次尝试——①子集后 pct_change（方法缺陷）②值位移（产生 NaN，无效）③索引重贴标签 + 各序列自算收益（方法正确）→ 仍为 0
纪律：按 §12【不】据此判定时间错误；仅如实记录『独立验证未能成功』
```

价格水平与波动量级（说明两边「像」同一品种，但不能据此断言对齐）：
```json
{
 "duka_2025_mean": 3512.66,
 "mt5_2025_mean": 3442.38,
 "duka_h1_vol_bp": 24.92,
 "mt5_h1_vol_bp": 23.96
}
```

## 数据完整性发现（附带，但重要）

```json
{
 "rows": 1272960,
 "flat_rows": 413512,
 "flat_pct": 32.484,
 "real_rows": 859448,
 "days_total": 320,
 "days_with_real_bars": 274,
 "fully_flat_days": 46
}
```

含义：约 1/3 的行是【平盘占位 bar】（O=H=L=C 且 vol=0），2025 年 320 个日历日中有 46 天完全平盘。
任何使用者必须先过滤这些行，否则所有统计量都会被稀释。

## SCALE 复核（§十四）

```text
raw_price 示例（2018-03-25 BID 首根）= 1,331,609 → /1000 = 1,331.609 USD（与当日金价量级相符）
SCALE = 1000 · 由 dukascopy.py / duka_download.py 明确声明 · duka_assemble.py 已正确应用
本任务【未】做任何新的收益计算
```

## 结论与后果（§十七）

```text
14 项判定要件中：B 通过、parser/git 通过；A 未获独立确认、C 为 UNKNOWN、独立样本验证未通过
=> DUKASCOPY_CANDLE_TIMESTAMP_SEMANTICS = UNRESOLVED
=> 资产保留为 REFERENCE_ONLY；禁止进入 V3 正式事件研究；原始数据未做任何修改
=> 所以 V3 的长历史 M1 缺口【仍然存在】（无论数据定义是否可解）
```

## 合规（§二/§十九）

```text
未重新下载 · 未访问海外源 · 未用 VPN/代理 · 未人工复制 · 未购买 · 未拼接其它 XAUUSD
未修改/覆盖/删除原始数据 · 未创建/修改/重算 H22 · 未计算事件收益/胜率/Sharpe/alpha
未 Round4 · 未 Forward · 未 Shadow · 未 Live · 未任何订单 · 未改 V1/V2/V3 adapter/ledger/Round1-3 结果
所有脚本：先 compile 再运行；并做 secret scan / path boundary scan / git diff / git status
```