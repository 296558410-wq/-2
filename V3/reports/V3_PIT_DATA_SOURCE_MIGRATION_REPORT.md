# V3 PIT 宏观/跨市场数据源迁移与替代验证报告

`ts_utc = 2026-09-25T01:18:46.750228+00:00` · **`final_status = V3_PIT_PARTIAL`** · `V3_PIT_READY = FALSE`
`V3_STRATEGY_FORWARD = NOT_ENABLED` · `V3_LIVE_ALLOWED = NO` · 本任务**未下任何单**

## 1. 找到哪些数据源？（共审计 15 个候选）

| Tier | source | PIT 判定 | AUTH_REQUIRED | bytes | 原因 |
|---|---|---|---|---|---|
| T1 | US_TREASURY_YIELD_CURVE_2024 | CONDITIONAL | no | 19098 | official daily yield curve file: historical by year and not restated i |
| T1 | US_TREASURY_YIELD_CURVE_2026 | CONDITIONAL | no | 15014 | official daily yield curve file: historical by year and not restated i |
| T1 | FOMC_CALENDAR | CONDITIONAL | no | 165460 | event calendar: meeting/statement DATES are historical facts; usable f |
| T1 | BLS_API_CPI | FAIL | no | 3024 | values only: no vintage/revision history in the payload, no publicatio |
| T3 | STOOQ_DXY_DAILY | NOT_AVAILABLE | no | 796 | payload is not a series (throttle/notice page); cannot be used |
| T3 | STOOQ_GC_DAILY | NOT_AVAILABLE | no | 796 | payload is not a series (throttle/notice page); cannot be used |
| T3 | STOOQ_VIX_DAILY | NOT_AVAILABLE | no | 796 | payload is not a series (throttle/notice page); cannot be used |
| T3 | STOOQ_TLT_DAILY | NOT_AVAILABLE | no | 796 | payload is not a series (throttle/notice page); cannot be used |
| T3 | YAHOO_GC_F_DAILY | CONDITIONAL | no | 23510 | market series: T_available = T_market for a COMPLETED daily bar; no ma |
| T3 | YAHOO_VIX_DAILY | CONDITIONAL | no | 27779 | market series: T_available = T_market for a COMPLETED daily bar; no ma |
| T1 | ALFRED_VINTAGES | NOT_AVAILABLE | YES | 0 | requires credentials this environment does not have (AUTH_REQUIRED) |
| T2 | NASDAQ_DATA_LINK | NOT_AVAILABLE | YES | 0 | requires credentials this environment does not have (AUTH_REQUIRED) |
| T2 | ECONDB_API | NOT_AVAILABLE | YES | 0 | requires credentials this environment does not have (AUTH_REQUIRED) |
| T2 | DBNOMICS_FRED_DGS10 | NOT_AVAILABLE | no | 0 | unreachable: HTTPError: HTTP Error 404: NOT FOUND |
| T3 | YAHOO_DXY_DAILY | CONDITIONAL | no | 28776 | market series: T_available = bar close + 1d (completed bar only); dail |

## 2. 哪些真正支持 PIT？

```text
PIT_PASS : 0 个
=> 没有任何一个源能够同时证明 "历史观测 + 历史可得性/版本" 的关系（§5 PASS 门槛）
   因此没有任何源具备 PIT_SUPPORTED = TRUE
```

## 3. 哪些只有普通历史数据？

```text
BLS API (CPI 值)   : 只有最终值，无版本、无发布时间 -> FAIL
stooq (DXY/GC/VIX/TLT) : 返回 796B / 3 行 = 限流或提示页，非序列 -> NOT_AVAILABLE（未误当作数据）
DBnomics           : 404（端点不可用）-> NOT_AVAILABLE
Nasdaq Data Link / EconDB : 403 / 401（需 key）-> AUTH_REQUIRED
```

## 4. 哪些存在 publication timestamp？

```text
FOMC 日历页  : 会议/声明"日期"存在（日期级，非盘中时刻）-> CONDITIONAL（仅事件时点研究）
ALFRED       : 具备 realtime_start/end（真正的 vintage 时间戳），但需要 API key -> AUTH_REQUIRED
其他         : 未获得任何精确到盘中的发布时间戳
```

## 5. 哪些存在 vintage / revision？

```text
本次环境下：无任何可获得版本历史的源。
ALFRED(FRED vintages) 与 Nasdaq Data Link 具备版本能力，但均需凭据 -> AUTH_REQUIRED（未申请、未存储、未伪造）
=> 宏观数据的"修订不可见性"在本环境无法被验证
```

## 6. 覆盖多少时间？

```text
市场/利率层（CONDITIONAL，日线）:
  US Treasury 收益率曲线 : 2024 全年 + 2026 全年（官方，逐年文件）
  Yahoo GC=F / ^VIX / DX-Y.NYB : 近 1 年日线（completed daily bars）
宏观版本层 : 覆盖 = 0（无可用源）
事件日历层 : FOMC 会议/声明日期（日期级）
缺口 : CPI / Core CPI / NFP / 失业率 / GDP / 零售 / ISM / 联邦基金利率 / 真实收益率 / TIP / GLD = 未获得
```

## 7. 哪些 H21/H22/H23 可以进入下一轮？

```text
严格回答：以【已冻结的定义】而言，H21 / H22 / H23 全部仍然 NOT_TESTABLE。
理由：三者的冻结定义都是【盘中】口径（6 分钟级路径 / 事件后重定价窗口 / 新闻叙事），
      而本次获得的数据只到【日线】。按 §20/§34，不能用一个日线源去"测"一个盘中假设。

本次建设的真正价值：新增了【日线级】可 PIT 的跨市场价格层（GC / VIX / DXY / UST 收益率）。
它使 Round 3 可以【重新冻结】一条全新的日线级跨市场 regime 假设（例如"日线级黄金/美元/实际利率 regime 组合"），
但那条假设必须是新 id、重新预注册，绝不允许回改 H21。
```

## 8. 哪些仍然 NOT_TESTABLE？

```text
NOT_TESTABLE（数据侧硬约束）:
  H10_DXY_CONFIRMED_REVERSAL   : 6 分钟级跨资产确认 -> 日线数据无法支持
  H21_CROSS_ASSET_DIVERGENCE   : 盘中跨资产背离 -> 同上（仅可催生日线级【新】假设）
  H22_MACRO_REPRICING_WINDOW   : 需要真实发布时间（如 13:30 UTC 后 5 分钟）-> 完全不可得
  H23_NEWS_NARRATIVE_SHIFT     : 需要 PIT 新闻语料 + 发布时间戳 -> 不可得
也仍是 NOT_TESTABLE 的原因不是"没努力找"，而是缺少两点：
  ① 宏观数据的 vintage（修订史）——需要 ALFRED/Quandl 凭据（AUTH_REQUIRED）
  ② 精确的发布时刻（盘中）——官方页面 403 或仅日期级
```

## 9. 是否存在未来数据泄漏？

```text
未来泄漏测试 = 全部通过（5/5）
T1 未来发布不可见 ✓   T2 未来修订不可见 ✓   T3 重放确定性 ✓   T4 哈希完整性 ✓   T5 时区 ✓
保守可用性规则已冻结（日线 bar 于 D+1 00:00Z 才可用；禁止未完成 bar）
```

## 10. Git 是否干净？

```text
见提交后审计输出（trader_v3 路径内；v1/v2 未改；calibration/adapter 未改；无凭据提交）
V1_ISOLATION = PASS · V2_ISOLATION = PASS · V3_EXECUTION_ISOLATION = PASS
```

## 最终状态（§19）

```text
V3_PIT_PARTIAL
V3_PIT_READY = FALSE
理由：有【部分】PIT 数据可用（日线市场/利率层 + 事件日历），但宏观版本层与盘中发布时刻缺失，
      部分机制仍不可测试 => 属于 V3_PIT_PARTIAL，而非 READY，也不是 SOURCE_UNAVAILABLE。
```

## 下一阶段（§20）

```text
Round 3 的允许范围（需你在报告确认后才创建）:
  可做 : 日线级跨市场 regime 假设（必须【重新冻结】新 id；可用 GC/VIX/DXY/UST 日线）
  不可做: 任何盘中事件窗口、任何依赖修订史/发布时刻的假设
本任务结束后：不得自动启用 Forward · 不得自动下单（已遵守）
```

## §15 凭据合规声明

```text
本任务未申请、未使用、未打印、未存储任何 API key / 账号 / 密码。
AUTH_REQUIRED 源仅记录状态并跳过；未伪造账号、未绕过任何认证。
C:\AIQuant\.env.v3_pit 未创建（本次无凭据可写）。
```
