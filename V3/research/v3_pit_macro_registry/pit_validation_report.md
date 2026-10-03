# PIT 数据验证报告

`ts_utc = 2026-09-25T01:18:46.750228+00:00` · `registry_hash = `

## 防未来信息泄漏测试（§9）

```text
[PASS] T1_future_publication_hidden (visible sources=5, withheld=43)
[PASS] T2_future_revision_not_visible (before=0, after=0)
[PASS] T3_replay_determinism (1a80f3320d976991==1a80f3320d976991)
[PASS] T4_hash_integrity (checked=5, mismatches=0)
[PASS] T5_timezone_utc_and_original_kept

=== PIT_LEAKAGE_TEST_COUNT=5 PASS=5 FAIL=0 ===
```

```text
5 项测试全通过 = True
T1 future publication hidden  : 返回结果中不含 availability_time > decision_time 的观测
T2 future revision not visible: 修订时间晚于决策时间的观测不得提前可见（合成 fixture 验证）
T3 replay determinism         : 同一 (registry, T) 两次调用逐字节一致
T4 hash integrity             : 存储序列 sha256 与注册表记录一致（缺失/篡改即 FAIL）
T5 timezone                   : 全部转 UTC，并保留 source_timezone 原值
```

## 可用性规则（保守、已冻结、无 lookahead）

```text
日线市场 bar 日期 D      -> D+1 00:00:00Z 才可用（日线只有收盘后才完全已知）
官方日度收益率 日期 D    -> D+1 00:00:00Z 才可用（官方惯例：当日收盘后发布）
日历事件 日期 D          -> D 23:59:59Z 可用（仅日期级）
禁止使用未完成 bar（unfinished candle）
```

## 已准入序列

| source | status | observation_time | availability_time | hash |
|---|---|---|---|---|
| US_TREASURY_YIELD_CURVE_2024 | CONDITIONAL | date column | None | 6775840b76cd7fd4… |
| US_TREASURY_YIELD_CURVE_2026 | CONDITIONAL | date column | None | 334eed6056c7d01b… |
| YAHOO_GC_F_DAILY | CONDITIONAL | bar close date | bar close (completed bar only; unfinished candles forbidden) | 6e6c84c1a48978ba… |
| YAHOO_VIX_DAILY | CONDITIONAL | bar close date | bar close (completed bar only; unfinished candles forbidden) | 0f862d75e5a211ad… |
| YAHOO_DXY_DAILY | CONDITIONAL | bar close date | bar close + 1 day (conservative: completed bar only) | 04cdad6f642e6004… |

## 状态枚举判定

```text
PASS        : 0 个（无法证明历史可得性/版本）
CONDITIONAL : 6 个
FAIL        : 1 个
NOT_AVAILABLE: 8 个
需要凭据（AUTH_REQUIRED，未使用、未存储任何 key）: ALFRED_VINTAGES, NASDAQ_DATA_LINK, ECONDB_API
```
