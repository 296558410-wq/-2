# V3 中国内网商业 XAUUSD 1m 数据源采购前审计报告

`ts_utc = 2026-09-25T09:38:29.912900+00:00` · 任务类型 `DATA_SOURCE_DISCOVERY_AND_PRE_PURCHASE_AUDIT`

**未购买 · 未付款 · 未注册付费套餐 · 未提交任何证件/银行卡 · 未获取任何凭据**

## §23 十问直答

```text
1. 是否找到中国内网可直连 XAUUSD 1m？        没有【可验证合格】的；有【未验证商业候选】
2. 是否可以 Python 自动化？                  候选页面均提及 API，但取数需账号 → 购买前【无法验证】
3. 最早可到哪一年？                          全部 UNVERIFIED（无账号无法取数）
4. XAUUSD 品种定义是什么？                    全部 UNKNOWN/H（未见公开明确 spot/CFD 定义）
5. timestamp 是什么时区？                     全部 UNKNOWN（公开页未说明）
6. timestamp 是 open 还是 close？             全部 UNKNOWN（无文档，不得假设）
7. 数据是 Bid/Ask/Mid/Last 哪一种？            UNKNOWN
8. 是否允许量化研究本地存储？                 LICENSE_STATUS = UNKNOWN（未见可读授权条款）
9. 是否需要付费？                             【是】PURCHASE_REQUIRED = YES
10. 是否值得进入下一阶段采购评估？             PROCEED_TO_MANUAL_PURCHASE_REVIEW
```

## 一、执行前/后快照

```text
HEAD_before = 1a0...（见 git_audit.json）
HEAD_after  = 59b1433
```

## 二、发现与资格状态（不做优劣排名）

| 候选 | 类别 | 网页可达 | 中国直连 | 自动化 | 定义 | 结论 |
|---|---|---|---|---|---|---|
| 掘金量化 myquant | domestic quant platform | True | YES | UNVERIFIED | H | **CONDITIONAL** |
| 聚合数据 juhe.cn | domestic API marketplace | True | YES | UNVERIFIED | H | **CONDITIONAL** |
| iTick | domestic/global market data API | True | YES | UNVERIFIED | H(页面出现 XAUUSD/gold 关键词) | **CONDITIONAL** |
| AllTick | market data API | True | YES | UNVERIFIED | H(页面出现 spot/gold) | **CONDITIONAL** |
| 通联数据 DataYes | institutional data vendor | True | YES | UNVERIFIED | H | **BLOCKED** |
| 同花顺 iFinD | institutional terminal/API | True | YES | UNVERIFIED | H | **BLOCKED** |
| 万得 Wind | institutional terminal/API | True | YES | UNVERIFIED | H | **BLOCKED** |
| 东方财富 Choice | institutional terminal/API | True | YES | UNVERIFIED | H | **BLOCKED** |
| 恒生聚源 gildata | institutional data vendor | True | YES | UNVERIFIED | H | **BLOCKED** |
| 聚宽 JoinQuant | quant platform | True | YES | UNVERIFIED | H | **BLOCKED** |
| 米筐 RiceQuant | quant platform | None | NO | UNVERIFIED | H | **BLOCKED** |
| 国泰安 CSMAR | academic data vendor | None | NO | UNVERIFIED | H | **BLOCKED** |
| 锐思 RESSET | academic data vendor | True | YES | UNVERIFIED | H | **BLOCKED** |
| 优矿 Uqer | quant platform | None | NO | UNVERIFIED | H | **REJECTED** |
| 金投网 cngold | gold portal (content only) | True | YES | UNVERIFIED | H | **REJECTED** |
| Databento | overseas market data | True | YES | UNVERIFIED | E | **REJECTED** |
| TrueFX | overseas FX tick | True | YES | UNVERIFIED | H | **REJECTED** |
| Dukascopy (as a purchase path) | overseas broker feed | None | NO | UNVERIFIED | B | **BLOCKED** |

```text
QUALIFIED 0 · CONDITIONAL 4 · BLOCKED 9 · REJECTED 5
```

## 三、关键证据

```text
· 聚宽 JoinQuant：HTTP 200 但页面标题为「当前地区暂不支持访问」→ 地区封锁 → BLOCKED
· 米筐 / 国泰安：本机 TLS 证书验证失败 → 未确认可达 → BLOCKED
· 优矿 Uqer：DNS 不解析 → REJECTED
· 掘金量化：门户可达，但其 API 文档路径返回 HTTP 502
· iTick / AllTick / 聚合数据：门户与文档页可达，公开页提及 XAUUSD·分钟·tick·API key·试用/套餐
  → 取数必须账号+密钥；本任务禁止注册/付费 → 一切来源在购买前不可验证
· 机构厂商（通联/万得/iFinD/Choice/聚源）→ 需销售合同 → BLOCKED
· 海外 Databento = COMEX GC 期货（class E）→ 按 §5 不得登记为 XAUUSD → REJECTED
· TrueFX = FX 主要货币对，XAUUSD 未确立（且此前审计已记录 off-tick 质量问题）→ REJECTED
```

## 四、伪 XAUUSD 排除（§5）

```text
已明确排除且不得登记为 XAUUSD：GC(COMEX 期货) · GLD/IAU(ETF) · SGE Au9999/上海金/XAU-CNY · 任何只有日线的黄金序列
```

## 五、已复核的本机既有结论（不得改变）

```text
V3_LONG_XAUUSD_HISTORY_PARTIAL   ← 保持
DUKASCOPY_16Y = REFERENCE_ONLY · DUKASCOPY_TIMESTAMP = UNRESOLVED  ← 保持
JIN10_EVENT_PIT = PASS · XAUUSD_LONG_1M = NOT_AVAILABLE  ← 保持
未因发现候选而把任何状态改成 READY
```

## 六、结论与停止

```text
最终状态：V3_LONG_XAUUSD_COMMERCIAL_CANDIDATE
含义：存在技术上值得人工评估的商业候选，但【未购买、未接入、未验证】
PURCHASE_REQUIRED = YES · PURCHASE_STAGE = NOT_STARTED
NO PURCHASE / NO PAYMENT / NO SUBSCRIPTION / NO H22 / NO ROUND4 / NO FORWARD / NO SHADOW / NO LIVE / NO ORDER
```

### 人工采购前必须完成的验证清单（否则不付款）

```text
① 书面确认 XAUUSD Spot/CFD 定义  ② 证明 1m 可得  ③ 证明最早可得日期
④ 书面说明 bar timestamp 是 open 还是 close  ⑤ 说明价格类型(Bid/Ask/Mid/Last)
⑥ 条款明确允许本地量化研究存储与回测
```

### 交付物

```text
research/v3_long_history_data/commercial_candidates/candidate_registry.json · coverage_matrix.json ·
  api_capability_matrix.json · license_matrix.json · cross_validation_matrix.json · purchase_gate.json
reports/V3_COMMERCIAL_XAUUSD_1M_PREPURCHASE_AUDIT.md
```