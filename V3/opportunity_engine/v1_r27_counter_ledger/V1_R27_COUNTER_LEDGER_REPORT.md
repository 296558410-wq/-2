# R27 SUMMARY

```text
TASK_STATUS = V1_COUNTER_LEDGER_R27_COMPLETE
COMMIT = 43f9b2f
PARENT_COMMIT = ebce041797ec
OLD_RUN_ID = ABSENT
NEW_RUN_ID = V1_RUN_20260924_RESET_01
NEW_RUN_COUNTERS_ZERO = NO
OLD_COUNTERS_BEHAVIOR = PARTIALLY_CLEARED
LOGICAL_COUNTER_RESET = NOT_PROVEN
LEDGER_PARENT_LINES = 30
LEDGER_COMMIT_LINES = 5
LEDGER_LINES_ADDED = 5
LEDGER_LINES_REMOVED = 30
LEDGER_RESET_MODEL = TRUNCATED
PER_RUN_FILE_NAMESPACE = ABSENT
LOGICAL_STATISTICS_ISOLATION = NOT_PROVEN
OLD_COUNTERS_ISOLATION = NOT_PROVEN
OLD_PNL_ISOLATION = NOT_PROVEN
COMMIT_PNL_HANDLING = ABSENT
RESET_BEHAVIOR_MODEL = IN_PLACE_COUNTER_RESET_PLUS_LEDGER_REWRITE
R27_GATE = FAIL
NEW_RUN_STATS_BOUNDARY = NOT_PROVEN
```

## 1. statistics counter diff

| JSON Path | OLD | NEW | Classification |
|---|---:|---:|---|
| `$.counters.decisions` | 77 | 4 | DECREASED |
| `$.counters.observations` | 87 | 4 | DECREASED |
| `$.counters.plans_cancelled` | 4 | 1 | DECREASED |
| `$.counters.plans_registered` | 8 | 4 | DECREASED |
| `$.counters.reconcile_closed` | 1 | 0 | ZEROED |
| `$.counters.trades_closed` | 1 | 0 | ZEROED |
| `$.counters.trades_opened` | 1 | 0 | ZEROED |
| `$.counters.triggers` | 1 | 0 | ZEROED |
| `$.integrity.ledger_head.len` | 29 | ABSENT | REMOVED |
| `$.waits.consecutive_waits` | 16 | 0 | ZEROED |
| `$.waits.wait_reasons.12:15实体大阴首次实测4400-4405支撑、live反弹至4409.3显示承接, 但无收盘级确认且12:30/45` | 2 | ABSENT | REMOVED |
| `$.waits.wait_reasons.12:30反弹已完全回吐(live 4403.07), 现处4400-4405汇合支撑二次测试, 但13:00/13:1` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.12:30反弹收4409.6未站上M15 MA50且live回落至4405.5, 证实仅为下沿支撑的区间反弹而非趋势转多` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.13:45收4391.72下探4390未收破, live反抽4393.86; H1超卖(RSI28.3)仍空, D1/H` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.14:00收4393.95反抽后live再探4389.08, 未收破4390亦无企稳K; H1空超卖, D1/H4中性,` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.14:15收4389.82仅微破4390且z0.59无放量, 非有效破位; live4387.6探入企稳带前; H1空势` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.20:45收4406.99以收确认下破墙底4411/MA20, rollover兑现, 但价贴MA50 4404压缩待方` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.21:00收4404.825 rollover延伸贴MA50, RSI34.9空动能确认, 正测4400-4405支撑;` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.2h磨顶floor4411已破(mid4408.34, 回摆第3轮低); 在册TP-1732Z retest短[4409` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.4411-4416墙三触未破(4416→4413.16→4414.365), M15动量衰减, 触墙后live回落钉44` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.4413-4416双头(RSI86.8)后动量衰减阴跌, 现4406.61中带钉住30min, live<H1 MA20` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.4413.82在4411-4415带第4轮磨高未破帽; 在册1517Z(≤4407.5空止4415)+1525Z(≥44` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.4416急落11pt后仅浅回抽至4406.61, 仍居破位floor4411与H1MA20下方, rollover未反转` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.4416急落11pt后横盘压缩于4406.6中带, 未收复floor4411/H1MA20墙且H4空排, 下行概率占优;` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.6叩墙动量三轮衰减(er0.39, RSI69.6退烧)空侧逻辑完好, 但19:30收回升未确认rollover; 在册` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.7叩墙后首收跌4414.385→4412.06, rollover初现但未破4411未确认; RSI65.5/er0.3` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.7触墙19:45收4414.385仍未破, er/RSI微复燃但4416双压+D1/H4空排约束未变; 在册双书已覆盖,` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.MTF冲突+价格中带无结构触发+追多追空EV均≤0, 低成本不足以转正EV; 纪律性等待关键阻力/边界, 不降门槛` | 2 | ABSENT | REMOVED |
| `$.waits.wait_reasons.floor4411破位后live续滑至4406.36(第4轮低), 在册TP-1732Z retest[4409,441` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.live 4392.35逼近4390破位哨兵与4378.4区间底, 但13:45/14:00 bar滞后无收盘确认; 空` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.live 4394.21阴跌逼近4378.4区间底与4390破位哨兵, 但13:45 bar未入缓存(滞后已知), 无收` | 2 | ABSENT | REMOVED |
| `$.waits.wait_reasons.live 4397.47虽已下破4400-4405三重汇合支撑, 但13:15/13:30 bar未入缓存(前几轮已证缓` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.live 4409 仍处MA20(4403)-MA50(4413)窄带中带: 上沿4411-4415两次压制但无新确认K` | 2 | ABSENT | REMOVED |
| `$.waits.wait_reasons.quote三连lower-high(4412.66→4409.09→4407.57)确证墙压+反弹衰竭, 支撑簇4404` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.quote二动4412.66回落-3.6pt确证4411-4416墙压, 但无新边际setup: 墙fade双书zomb` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.quote层首动4412.66入双fade带[4411,4415.5]/[4409,4416]→在册墙fade空将自动f` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.三档在册空单全覆盖回落/触帽/破墙且互斥; 中段新增单必叠单且止损窄EV≈-0.4R; 远区4443fade超engin` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.价处 H4 MA20/M15 MA50 汇合下沿但无确认K线, MTF 仍冲突(D1/H4 中性 vs H1 空但超卖)` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.价处中带无结构触发, MTF冲突无共振, 现价双向追单EV≈0/负且低成本无法转正; M15压缩方向未明, 纪律性等待边` | 2 | ABSENT | REMOVED |
| `$.waits.wait_reasons.在册三档空单全覆盖回落/触帽/破墙且互斥(距触发带1.9-5.9pt); 中段空EV负、4411抢先空叠单双重暴露、追多` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.在册三空单距触发-5.3~+6.2pt全覆盖回踩/触顶/rollover互斥; 贴墙fade与1617Z同波叠单=变相加` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.在册三空单距触发0.41-7.09pt全覆盖触顶/回踩/rollover互斥; 中段叠单=变相加仓拒; 追多逆H1结构拒` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.多周期方向冲突; 当前 EV 不足以覆盖成本` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.持仓管理: LONG 0.01@4425.46(POS-2355Z) mid4438.7浮盈+1.33R, 第4次int` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.持仓管理: LONG 0.01@4425.46(POS-2355Z) quote4429.38浮盈+0.39R, M15` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.持仓管理: LONG 0.01@4425.46(POS-2355Z) quote4433.44浮盈+0.80R, M15` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.持仓管理: LONG 0.01@4425.46(POS-2355Z) quote4434.33浮盈+0.89R, 第三次` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.持仓管理: LONG 0.01@4425.46(POS-2355Z), quote4423.62浮亏-0.18R, 回踩` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.持仓管理: LONG 0.01@4425.46(POS-2355Z)quote 4425.25近成本; M15上破旧墙4` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.持仓管理: LONG 0.01@4425.46(POS-2355Z)现quote 4425.2近成本, 回踩墙4423.` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.持仓管理: LONG 0.01@4425.46浮盈+10.42pt(+1.05R), quote4435.88距TP1 ` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.持仓管理: LONG 0.01@4425.46浮盈+2.02pt(+0.20R), 高位回撤8.4pt回踩突破墙4424` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.持仓管理LONG@4425.46浮盈+1.44R, mid4439.83距TP1 0.67pt第5次上攻(V型收复拒收)` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.持仓管理期: LONG 0.01@4425.46, mid4421.25浮亏-4.21pt; 硬止4415.5余5.75` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.持仓管理期: LONG 0.01@4425.46, mid4421.99浮亏-3.47pt; 硬止4415.5余6.5p` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.持仓管理期: LONG 0.01@4425.46, mid4424.01浮亏-1.45pt; 硬止4415.5余8.51` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.持仓管理期: LONG 0.01@4425.46浮盈+10.46pt(+1.05R), quote4435.92距TP1` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.持仓管理期: LONG 0.01@4425.46浮盈+9.42pt(+0.95R), quote4434.88距TP1 ` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.持仓管理期: LONG 0.01@4425.46转盈+3.54pt(+0.36R), mid4429.0站稳4424突破` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.数据修正: quote 4406.61钉60min判定stall, bar源真实=19:00收4415.55第4触墙且收` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.数据冻结(quote钉4406.61约195min, bar止21:00收4404.825), 与21:32Z同态零新增` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.数据冻结加深(live_ticks +0/15min, bar止21:00收4404.825, quote钉4406.6` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.现价4386.7贴M15 low60支撑: 追空R≈0.56倒挂且H1/M15深度超卖; D1/H4中性无共振, 破位未` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.现价4411.32处三档互斥空单中间带(距-3.8/+3.7/+7.7pt); cap第8次失败回摆第2轮+H1下行MA` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.现价4412.49停滞于4411-4415供应带中段, 上侧4419-4424(1525Z)与下侧4404-4407(1` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.现价4412.79横于4411-4415供应带第三轮, 在册1517Z(≤4407.5空止4415)与1525Z(≥44` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.第四leg三连升4412.03上穿墙底,第10测live;fade双书在册且现价在带内本轮自动fire勿叠、floor≤` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.第四leg两连升4410.85贴墙0.15pt,第10测即临;fade双书在册勿叠、floor≤4401.5在册、承接多` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.第四leg止跌回弹4408.82距墙4411仅2.2pt;fade区zombie在册勿叠、floor≤4401.5在册、` | 1 | ABSENT | REMOVED |
| `$.waits.wait_reasons.首收跌后20:15收4412.27墙底企稳未给方向票; RSI67.6/er0.352微回升但D1/H4空排+7叩墙约束` | 1 | ABSENT | REMOVED |

non-numeric changes: [{"path": "$.counters", "OLD": "<obj>", "NEW": "<obj>", "classification": "NON_NUMERIC_CHANGED"}, {"path": "$.integrity", "OLD": "<obj>", "NEW": "ABSENT", "classification": "NON_NUMERIC_CHANGED"}, {"path": "$.last_invariants", "OLD": "<obj>", "NEW": "<obj>", "classification": "NON_NUMERIC_CHANGED"}, {"path": "$.note", "OLD": "ABSENT", "NEW": "NEW_RUN_ZERO_STATE", "classification": "NON_NUMERIC_CHANGED"}, {"path": "$.run_id", "OLD": "ABSENT", "NEW": "V1_RUN_20260924_RESET_01", "classification": "NON_NUMERIC_CHANGED"}, {"path": "$.run_start_utc", "OLD": "ABSENT", "NEW": "2026-09-23T23:39:46.457357+00:00", "classification": "NON_NUMERIC_CHANGED"}, {"path": "$.waits", "OLD": "<obj>", "NEW": "<obj>", "classification": "NON_NUMERIC_CHANGED"}]

counts: {"DECREASED": 4, "ZEROED": 5, "REMOVED": 61}

## 2. logical counter reset conclusion

```text
NEW_RUN_COUNTERS_ZERO = NO
OLD_COUNTERS_BEHAVIOR = PARTIALLY_CLEARED
LOGICAL_COUNTER_RESET = NOT_PROVEN
note: counter reset alone does NOT prove per-run namespace isolation
```

## 3. ledger diff

```text
parent_lines = 30
commit_lines = 5
added = {"registered": 4, "cancelled": 1}
removed = {"registered": 13, "cancelled": 12, "triggered": 3, "filled": 1, "closed": 1}
LEDGER_RESET_MODEL = TRUNCATED
run binding: parent=ABSENT commit=ABSENT
```

## 4. legacy lifecycle impact

```text
{"LEGACY_ENTRY_CHANGED": "NOT_FOUND", "LEGACY_TRIGGER_CHANGED": "NOT_FOUND", "LEGACY_FILL_CHANGED": "NOT_FOUND", "LEGACY_EXIT_CHANGED": "NOT_FOUND", "LEGACY_PNL_CHANGED": "NOT_FOUND"}
parent legacy lines = {}
commit legacy lines = {}
```

## 5. PnL handling

```text
COMMIT_PNL_HANDLING = ABSENT
{"added_records_matching_pnl_keywords": 0, "added_records_with_pnl_like_fields": 0}
```

## 6. logical vs file isolation

```text
PER_RUN_FILE_NAMESPACE = ABSENT
LOGICAL_STATISTICS_ISOLATION = NOT_PROVEN
OLD_COUNTERS_ISOLATION = NOT_PROVEN
OLD_PNL_ISOLATION = NOT_PROVEN
```

## 7. R26 corrections retained

```text
archive NOT created by this commit; statistics was MODIFIED in place (not archived+recreated);
no reset script in the commit; RUN_META.json CREATED.
```

## 8. R27 gate

```text
gate = FAIL
{"RESET_RUN_CREATION": false, "STATISTICS_INITIALIZATION": true, "LOGICAL_COUNTER_RESET": false, "OLD_COUNTERS_ISOLATION": false, "OLD_PNL_ISOLATION": false}
NEW_RUN_STATS_BOUNDARY = NOT_PROVEN
```

## 9. safety

```text
{"AUTOMATION_ENABLED": false, "V1_ENGINE_PROCESS": "NOT_RUNNING", "RESET": 0, "NEW_RUN": 0, "V1_START": 0, "AUTOMATION_ENABLE": 0, "MT5_ACCESS": 0, "ORDER_SEND": 0, "POSITION_CLOSE": 0, "POSITION_MODIFY": 0, "ORDER_CANCEL": 0, "LEDGER_WRITE": 0, "STATE_WRITE": 0, "SOURCE_WRITE": 0, "CONFIG_WRITE": 0, "GIT_COMMIT": "NONE", "BOUNDARY_VIOLATION": 0}
```

## 10. hashes

```text
before = {"ENGINE": "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d", "LEDGER": "0b90493cae0cdf7b73056bc72b1e5752f35c3eb20f9306c098d26f4bec819261", "STATISTICS": "ca42f624fde50df375dc877750e121e8d2d313986ea6d953766d5247ab76ee84", "RUN_META": "597bd76970412c107c96475dfe8d5093ff7840aba73cb4ab65318f2b0f358950"}
after  = {"ENGINE": "7d95645678cf0615c77c0d1c91177cf1652ca1fa6b1f509ec99e415dba55c25d", "LEDGER": "0b90493cae0cdf7b73056bc72b1e5752f35c3eb20f9306c098d26f4bec819261", "STATISTICS": "ca42f624fde50df375dc877750e121e8d2d313986ea6d953766d5247ab76ee84", "RUN_META": "597bd76970412c107c96475dfe8d5093ff7840aba73cb4ab65318f2b0f358950"}
match = YES
```