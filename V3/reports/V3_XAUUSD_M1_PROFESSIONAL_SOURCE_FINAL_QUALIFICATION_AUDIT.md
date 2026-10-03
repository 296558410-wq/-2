# V3 XAUUSD 1m 专业数据源最终资格审计报告

`ts_utc = 2026-09-25T10:06:28.066939+00:00` · 任务 `V3_XAUUSD_M1_PROFESSIONAL_SOURCE_FINAL_QUALIFICATION_AUDIT`

**`QUALIFIED = 0` → `NO_QUALIFIED_COMMERCIAL_SOURCE_FOUND`**

```text
NO PURCHASE · NO PAYMENT · NO SUBSCRIPTION · NO CARD · NO IDENTITY · NO API KEY PURCHASE · NO TRIAL PAYMENT
NO MT5 MODIFICATION · NO ORDER_SEND · NO FORWARD · NO SHADOW · NO LIVE
V3 strategy/adapter/calibration/ledger/Round1-3/H22 = unchanged
```

## §二十六 十三问直答

```text
 1. 是否有真正合格的 XAUUSD 1m 长历史源？      【没有】QUALIFIED = 0
 2. 哪些候选实际存在 XAUUSD Spot/CFD？         AllTick（页面明写 "XAU/USD Commodity Gold Spot"）· iTick（符号表含 XAUUSD）
                                               · OANDA（XAU_USD）· HistData（XAU/USD 'Forex Pair'，已审计）
 3. 哪些至少覆盖到 2020？                     【没有一个已证实】—— 唯一实测过的 HistData 最早仅 2025-01
 4. 哪些能通过中国内网直接访问？               全部候选 WEB 级可达；仅 HistData 达到 DOWNLOAD 级（实际下载成功）
 5. 哪些具有可自动化 API？                     AllTick（REST+WebSocket）· iTick（REST/WS/FIX）· OANDA（v20 REST）
                                               · HistData（公开表单 POST，免密钥，已实测）
 6. 哪些明确 Bid/Ask/Mid/Last？               仅 HistData 明确 =【Bid】（官方 spec + FAQ 明文）；其余 UNKNOWN
 7. 哪些明确 timestamp timezone/DST？         仅 HistData 明确 =【EST, UTC−5, 不做 DST】（官方 FAQ 明文）
 8. 哪些明确 bar open/close？                 【没有一个】——HistData 亦仅有结构推断(INFERRED)，按纪律记 UNKNOWN
 9. 哪些明确允许本地回测/机器学习？            【没有一个】——全部 LICENSE/LOCAL_STORAGE/BACKTEST/ML = UNKNOWN
10. 哪些需要购买才能进一步验证？               AllTick · iTick · 聚合数据 · 掘金 · OANDA · TwelveData
                                               （机构类：通联/万得/iFinD/Choice/聚源 需销售合同）
11. QUALIFIED 数量？                          【0】
12. 若 >0，谁进入人工采购审查？                不适用（QUALIFIED=0）→ 但给出 RECOMMENDED_FOR_MANUAL_PURCHASE_REVIEW = NO
13. 最接近的三个 CONDITIONAL 及各自缺什么？    见下节
```

## §二十三 TOP 3 CONDITIONAL（最接近合格）

### 1) AllTick（grading B）
```text
为什么接近：官方页面明写 "XAU/USD Commodity Gold Spot"（品种存在且偏 spot 措辞）；
            REST + WebSocket 双接口；有公开 pricing 页；中国内网 WEB 可达。
缺什么    ：历史深度/最早日期（≤2020 未证）· timestamp/DST · bar open/close · price type · license(本地存储/回测/ML)
购买后必须验证：XAUUSD 定义书面确认 · 最早可得月份 · 时区与 DST · bar 时间戳语义 · Bid/Ask 语义 · 条款是否允许本地回测与 ML
```

### 2) iTick（grading B）
```text
为什么接近：公开符号表含 XAUUSD；docs 提供 REST/WebSocket/FIX；中国内网 WEB 可达。
缺什么    ：同类全部语义门未证（定义/历史/时区/open-close/价格类型/授权）。
购买后必须验证：与 AllTick 同一清单。
```

### 3) HistData（grading A，已完成完整语义审计）
```text
为什么接近：唯一【实测下载成功】的 1m 源；时区(EST 无 DST)与价格类型(Bid)均已官方验证；两次下载字节级可复现。
缺什么    ：earliest = 2025-01（不满足 ≤2020）· 品种定义(spot/CFD/venue)未声明 · bar open/close 无官方说明 · 无授权条款。
购买后/后续必须验证：厂商书面的 instrument 定义 · 完整年份枚举 · open/close 说明 · 授权条款。
特殊说明  ：免费且无需账号，但仍不能升级为 QUALIFIED——【免费 ≠ 合格】。
```

## 一、十二道硬门汇总

| 候选 | 定义 | 1m | ≤2020 | 时区 | open/close | 价格类型 | 授权 | 中国 | API | 状态 |
|---|---|---|---|---|---|---|---|---|---|---|
| ALLTICK | spot-like (page wo | UNK | UNK | UNK | UNK | UNK | UNK | WEB_PASS (4/ | documented REST  | **CONDITIONAL** |
| ITICK | UNKNOWN | UNK | UNK | UNK | UNK | UNK | UNK | WEB_PASS (8/ | documented REST  | **CONDITIONAL** |
| JUHE | UNKNOWN | UNK | UNK | UNK | UNK | UNK | UNK | WEB_PASS (4/ | documented marke | **CONDITIONAL** |
| MYQUANT | UNKNOWN | UNK | UNK | UNK | UNK | UNK | UNK | WEB_PASS (4/ | platform SDK (CN | **CONDITIONAL** |
| TUSHARE | UNKNOWN | UNK | UNK | UNK | UNK | UNK | UNK | WEB_PASS (2/ | REST + Python SD | **BLOCKED** |
| DATAYES | UNKNOWN | UNK | UNK | UNK | UNK | UNK | UNK | WEB_PASS (2/ | institutional AP | **BLOCKED** |
| IFIND | UNKNOWN | UNK | UNK | UNK | UNK | UNK | UNK | WEB_PASS (2/ | openapi.10jqka ( | **BLOCKED** |
| TWELVEDATA | UNKNOWN | UNK | UNK | UNK | UNK | UNK | UNK | WEB_PASS (2/ | documented REST/ | **CONDITIONAL** |
| TRUEFX | FX spot | UNK | UNK | UNK | UNK | UNK | UNK | WEB_PASS (2/ | historical downl | **REJECTED** |
| DATABENTO | futures | UNK | UNK | UNK | UNK | UNK | UNK | WEB_PASS (2/ | documented | **REJECTED** |
| HISTDATA | UNKNOWN (vendor ne | VERIFIED | FAIL | VERIFIED | UNK | VERIFIED | UNK | DOWNLOAD_PAS | public form POST | **CONDITIONAL** |
| DUKASCOPY | CFD | UNK | UNK | UNK | UNK | UNK | UNK | BLOCKED (dat | HTTP bi5 (unreac | **BLOCKED** |
| OANDA | CFD (broker) | UNK | UNK | UNK | UNK | UNK | UNK | WEB_PASS | documented v20 R | **CONDITIONAL** |

## 二、关键阻断原因（不升级的理由）

```text
① 历史覆盖门：没有任何候选提供【可验证的 ≤2020】证据；唯一实测的 HistData 是 2025-01 → 直接 FAIL
② 授权门：全部候选的 license/local_storage/backtest/ML 均无法确认 → 按 §十四 不得 QUALIFIED
③ bar open/close 门：全部候选无官方说明 → 按 §九 不得 QUALIFIED
④ 品种定义门：AllTick/iTick 只证明符号存在，未证明 spot/CFD/venue → 按 §五 记 UNKNOWN
=> 四道硬门同时未过，QUALIFIED 必然为 0
```

## 三、未重复已完成的工作（§二十四）

```text
未重做：HistData 完整语义审计 · Dukascopy timestamp 审计/网络恢复 · Jin10 事件 PIT · SINA XAU 验证
        Round1/Round2/Round3 · H27/H30
（HistData 与 Dukascopy 仅作为【既有结论】引用纳入本矩阵，未重新取证）
```

## 四、安全审计（§二十五）

```text
HEAD_before/after 见 _git_audit.json · compile check ✓ · secret scan ✓ · path boundary scan ✓
V1/V2/V3 strategy/adapter/calibration/ledger/Rounds 未改动
未注册账号 · 未产生任何付费行为 · 未提交证件/银行卡 · 未取得付费 API Key
```

## 五、最终状态（§二十七）与 STOP（§二十八）

```text
V3_PROJECT_STATUS = CLOSED_NO_VALIDATED_EDGE（保持）
V3_FORWARD = OFF · V3_SHADOW = OFF · V3_LIVE = OFF · ORDER_SEND = 0
XAUUSD_LONG_1M = NOT_AVAILABLE
NO_QUALIFIED_COMMERCIAL_SOURCE_FOUND
STOP —— 不自动进入 Round4 / H22 / Alpha / Strategy / Forward / Shadow / Live
```