# V3 M03 Cross-Market Shock — 可交易性验证 R1 报告（正式）

`ts_utc = 2026-09-25T12:21:11.545572+00:00` · `version = M03-R1.0.0`

## 第一结论（§18）

```text
M03_TRADABILITY_STATUS = NOT_PROMISING
```

**该结论不是因为 M03 没有统计响应。** 恰恰相反——除频率外全部达标：

```text
gross edge          = 26.7942 bp   （positive）
net edge 1x         = 25.8802 bp   （positive）
net edge 2x/3x      = 24.9662 / 24.0522 bp  （3x 成本后仍为正）
WF                  = CONSISTENT  （8.2659 / 19.1354 / 50.2393）
permutation         = p=0.0065   （significant）
multiple testing    = PASS   （BH-FDR 显著项：VIX/opposite, MULTI_SOURCE/opposite）
effective_n         = 21   （>= 8）
execution rule      = FEASIBLE_UNDER_FROZEN_RULE（FEASIBLE）
frequency           = 0.7753 /week

required             = >= 1.0 /week
=> FREQUENCY_GATE = FAIL
=> NOT_PROMISING
```

## 防止误读（§19）

```text
这不是盈利证明。
这不是未来收益保证。
这不是 Alpha certification。
这不是实盘执行验证。
这不是高频策略。
这不是 63 个独立交易样本。
```

```text
21 macro episodes · 6h response horizon · 0.775 events/week
=> 它实际属于【低频事件响应机制】，不是当前 V3 所追求的高频机会源。
```

## 最终研究定位（§20）

```text
M03 = STATISTICALLY_INTERESTING BUT NOT_HIGH_FREQUENCY_TRADABLE_UNDER_CURRENT_GATE

≠ M03 = BAD
当前数据表明 M03 response ≠ 0；只是 frequency insufficient。这两个结论严格区分。
```

## 关键测量（冻结值，未重算）

```text
M03_INPUT_EVENTS = 63    TESTABLE = 63    NOT_TESTABLE = 0
DXY 13 · VIX 5 · UST10Y_PROXY 10 · MULTI_SOURCE 35
RAW_N = 63    EFFECTIVE_N = 21
MEDIAN_RESPONSE = 15.4088 bp    MEAN_RESPONSE = 26.7942 bp
CI95 = [10.5104, 49.9205] bp（block bootstrap, block=5, 2000 iters）
EVENTS_PER_DAY = 0.1108   EVENTS_PER_MONTH = 3.3671
MEDIAN_HOLDING_TIME = 6 h    NET_EDGE_PER_HOUR = 4.3134 bp
FREEZE_HASH = 2116ec8e812c322a34604e51eaf03b1682f07bbdeae6b8087c94c4f549d75b20
INPUT_HASH  = 202db652b9732aa92feb08666da70914b3c1f4f2e9db282b32d688e476c20be4
OUTPUT_HASH = 43249b90c44ce5f718a35c473a382f78595939a8044cbb8c8762ef5eede15b83
```

## 必须保留的审计限定（§9–§15）

```text
DIRECTION_MIRROR_TEST = ARITHMETIC_IDENTITY
  opposite = -aligned 由构造决定（同一批事件的 ± 符号），因此均值必然互为相反数。
  这不是独立证据，也不是 ASYMMETRY_CONFIRMED。

NEGATIVE_CONTROL = PASS_WITH_LIMITATION
  本轮负控复用置换零分布抽样 → 属一致性检查，不是完全独立的第二层控制实验。

EXECUTION = FEASIBLE_UNDER_FROZEN_RULE
  这不是 MT5 实盘执行验证；|R1| > cost 与 R0 未完全反转 不构成真实成交验证。

TIMESTAMP_SENSITIVITY = POSITIVE_BUT_TIMESTAMP_SENSITIVE
  -1 bar = +31.80 bp · 0 = +25.88 bp · +1 bar = +11.32 bp  → 不得写成 timestamp robust

数据语义（不因结果显著而升级）：
  XAUUSD_DEFINITION = UNKNOWN · BAR_OPEN_CLOSE_SEMANTICS = UNKNOWN · LICENSE = UNKNOWN

^TNX = PROXY（不是官方 UST10Y 收益率）
  去掉 ^TNX 后 GROSS = +30.05 bp / NET_1X = +29.14 bp → TNX_PROXY_DEPENDENCY = NOT_PROXY_DEPENDENT
  只能说明结果不依赖 ^TNX 这一路输入，不能证明 DXY/VIX/XAU 的经济因果关系。
```

## 验证与收口

```json
{
 "test_status": "PASS",
 "tests_passed": "26/26",
 "v1_source_modified": 0,
 "v2_source_modified": 0,
 "strategy_or_v1v2_git_changes": [
  "M research/hermes/trader_v1/run_state/plan_ledger.jsonl",
  " M research/hermes/trader_v1/run_state/state_package_latest.json",
  " M research/hermes/trader_v1/run_state/statistics.json",
  " M research/hermes/trader_v1/run_state/tmp/append_summary_0302.py",
  " M research/hermes/trader_v1/run_state/tmp/append_summary_1017Z.py",
  " M research/hermes/trader_v1/run_state/tmp/append_summary_1217Z.py",
  " M research/hermes/trader_v1/run_state/tmp/append_summary_1247Z.py",
  " M research/hermes/trader_v1/run_state/tmp/append_summary_1447Z.py",
  " M research/hermes/trader_v1/run_state/tmp/append_summary_1502Z.py",
  " M research/hermes/trader_v1/run_state/tmp/append_summary_1547Z.py",
  " M research/hermes/trader_v1/run_state/tmp/append_summary_1632Z.py",
  " M research/hermes/trader_v1/run_state/tmp/append_summary_1647Z.py",
  " M research/hermes/trader_v1/run_state/tmp/append_summary_1817Z.py",
  " M research/hermes/trader_v1/run_state/tmp/probe_0547Z.py",
  " M research/hermes/trader_v1/run_state/tmp/probe_0602Z.py",
  " M research/hermes/trader_v1/run_state/workflow_history.jsonl",
  " M research/hermes/trader_v1/run_state/workflow_latest.json",
  " M research/hermes/trader_v2/config/v2_config.json",
  " M research/hermes/trader_v2/dashboard/acc_probe.py",
  " M research/hermes/trader_v2/dashboard/datasource.py",
  " M research/hermes/trader_v2/dashboard/static/app.js",
  " M research/hermes/trader_v2/dashboard/static/index.html",
  " M research/hermes/trader_v2/dashboard/static/style.css",
  " M research/hermes/trader_v2/data_sources/mt5_market.py",
  " M research/hermes/trader_v2/execution/fxtm_demo_adapter.py",
  " M research/hermes/trader_v2/hermes/context.py",
  " M research/hermes/trader_v2/research/PRICE_SPACE_AUDIT.md",
  " M research/hermes/trader_v2/research/V2_G3_FINAL_SHADOW_REPORT_20260917.md",
  " M research/hermes/trader_v2/runtime/shadow_run.py",
  " M research/hermes/trader_v2/runtime/v2_scheduled_cycle.py",
  " M research/hermes/trader_v2/state/agent1_latest.json",
  " M research/hermes/trader_v2/state/agent2_latest.json",
  " M research/hermes/trader_v2/state/agent2_trigger.json",
  " M research/hermes/trader_v2/state/evidence_registry.jsonl",
  " M research/hermes/trader_v2/state/macro_releases.jsonl",
  " M research/hermes/trader_v2/state/paper_account.json",
  " M research/hermes/trader_v2/state/paper_executions.jsonl",
  " M research/hermes/trader_v2/state/v2_run_health.json",
  " M research/hermes/trader_v2/tests/_tmp/S1_techUp_macroUp_a1.json",
  " M research/hermes/trader_v2/tests/_tmp/S1_techUp_macroUp_a2.json",
  " M research/hermes/trader_v2/tests/_tmp/S2_techUp_macroDown_a1.json",
  " M research/hermes/trader_v2/tests/_tmp/S2_techUp_macroDown_a2.json",
  " M research/hermes/trader_v2/tests/_tmp/S3_breakout_pricedIn_a1.json",
  " M research/hermes/trader_v2/tests/_tmp/S3_breakout_pricedIn_a2.json",
  " M research/hermes/trader_v2/tests/_tmp/S4_geo_noFollow_a1.json",
  " M research/hermes/trader_v2/tests/_tmp/S4_geo_noFollow_a2.json",
  " M research/hermes/trader_v2/tests/_tmp/S5_divergence_a1.json",
  " M research/hermes/trader_v2/tests/_tmp/S5_divergence_a2.json",
  " M research/hermes/trader_v2/tests/_tmp/S6_staleData_a1.json",
  " M research/hermes/trader_v2/tests/_tmp/S6_staleData_a2.json",
  " M research/hermes/trader_v2/tests/_tmp/S7_conflict_a1.json",
  " M research/hermes/trader_v2/tests/_tmp/S7_conflict_a2.json",
  " M research/hermes/trader_v2/tests/_tmp/S8_badRR_a1.json",
  " M research/hermes/trader_v2/tests/_tmp/S8_badRR_a2.json",
  " M research/hermes/trader_v2/tests/_tmp/z_a2.json",
  " M research/hermes/trader_v2/tests/test_v2_repair.py",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-2026-09-22T0417Z-20260922053448.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260908T0532Z-20260908060402.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260908T063856-20260908080419.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260908T092012-20260908094850.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260908T100753-20260908103425.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260908T105022-20260908111826.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260908T113739-20260908121823.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260908T131419-20260908134842.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260908T140456-20260908154821.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260908T142140-20260908150341.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260908T152001-20260908153345.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260908T163554-20260908183329.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260908T185008-20260908193340.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260908T233624-20260909000439.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260909T002041-20260909014847.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260909T0402Z-20260909053318.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260909T0547Z-20260909134621.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260909T1532Z-20260909170510.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260909T1547Z-20260909190814.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260909T2202Z-20260910000322.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260910T0202Z-20260910044741.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260910T0502Z-20260910053241.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260910T0732Z-20260910081743.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260910T0917Z-20260910101929.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260910T1102ZB-20260910120409.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260910T133408-20260910180332.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260910T1902Z-20260911010534.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260911T0132Z-20260911033417.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260911T0432Z-20260911055102.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260911T0547Zb-20260911075001.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260911T0802Z-20260911110441.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260911T1117Z-20260911121901.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260911T1302Z-20260911140431.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260911T1432Z-20260911163321.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260911T1632Z-20260911200314.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260913T2217Z-20260914000316.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260914T001808-20260914011904.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260914T0117Z-20260914030250.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260914T031902-20260914074855.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260914T090414-20260914124908.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260914T1247Z-20260914131750.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260914T1447Z-20260914161822.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260914T1502Zb-20260914164835.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260914T1517Z-20260914153353.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260915T0002Z-20260915020338.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260915T0032Z-20260915012010.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260915T0217Z-20260915054755.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260915T0632Z-20260915074754.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260915T0917Z-20260915130557.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260915T1317Z-20260915181811.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260915T230323-20260916023330.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260916T0302Z-20260916131823.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260916T1417Z-20260916154733.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260916T1917Z-20260917001855.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260917T0017Z-20260917072121.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260917T0847Z-20260917105028.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260917T1047Z-20260917123559.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260917T1302Z-20260917203420.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260917T2232Z-20260918010335.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260918T0347Z-20260918060358.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260918T0647Z-20260918094904.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260918T1102Z-20260918123630.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260918T1302Z-20260918140348.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260918T1417Z-20260918161910.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260918T1747Z-20260918184903.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260918T1847Z-20260920230306.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260920T2317Z-20260921011817.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260920T2332Z-20260921001906.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260921T0132Z-20260921023306.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260921T0248Z-20260921053700.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260921T053913-20260921063453.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260921T0702Z-20260921093431.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260921T0717Z-20260921074936.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260921T1017Z-20260921110703.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260921T1132Z-20260921115100.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260921T1147Z-20260921133523.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260921T1232Z-20260921125026.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260921T1410Z-20260921145045.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260921T1502Z-20260921173503.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260921T1732Z-20260921225115.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260921T233510-20260922000546.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260922T000546-20260922002017.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260922T003534-20260922010443.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260922T011958-20260922020450.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260922T024745-20260922042017.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260922T053448-20260922055137.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260924T003339-20260924014830.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260924T0202Z-20260924024751.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260924T0347Z-20260924044829.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260924T1017Z-20260924105025.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260924T1047Z-20260924113401.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260924T1132Z-20260924121908.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260924T1234Z-20260924140455.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260924T1532Z-20260924160407.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260924T1732Z-20260924183517.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260924T1802Z-20260925010708.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260925T010908-20260925040352.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260925T043902-20260925084843.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260925T050604-20260925061827.json",
  "?? research/hermes/trader_v1/memory/reviews/RV-TP-20260925T090551-20260925102155.json",
  "?? research/hermes/trader_v1/run_state/decisions/2026-09-25T1047Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0032Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0048Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0103Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0117Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0132Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0147Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0202Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0217Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0232Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0247Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0302Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0317Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0332Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0347Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0402Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0417Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0432Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0447Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0502Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0517Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0532Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0547Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0602Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0938Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T0947Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1003Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1017Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1032Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1047Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1102Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1117Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1132Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1147Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1202Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1217Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1234Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1247Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1302Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1317Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1332Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1347Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1402Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1417Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1432Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1447Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1502Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1517Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1532Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1547Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1602Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1617Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1632Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1647Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1702Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1717Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1732Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1747Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1802Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1817Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1832Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1847Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1902Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1917Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1932Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T1947Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T2002Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T2017Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T2032Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T2047Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T2102Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T2117Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T2132Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T2147Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T2202Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T2217Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T2232Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T2247Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T2302Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T2317Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T2332Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260924T2347Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0002Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0017Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0032Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0047Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0102Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0117Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0132Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0147Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0232Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0247Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0402Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0434Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0447Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0502Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0517Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0532Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0547Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0602Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0617Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0632Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0647Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0702Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0717Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0736Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0747Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0802Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0817Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0832Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0847Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0902Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0917Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0932Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T0947Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T1002Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T1017Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T1032Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T1047Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T1102Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T1117Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T1132Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T1147Z.json",
  "?? research/hermes/trader_v1/run_state/decisions/20260925T1202Z.json",
  "?? research/hermes/trader_v1/run_state/positions/",
  "?? research/hermes/trader_v1/run_state/tmp/_probe_1317Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/_probe_2202Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/_probe_2217Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/_summ_1317Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/_write_dec_2147Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/active_1932Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/analyze_0602Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/analyze_0938Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/analyze_0947Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/analyze_1002Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/analyze_1003Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/analyze_1017Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/analyze_1032Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/analyze_1217Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/analyze_1247Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/analyze_1532Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_0017Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_0032Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_0047Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_0132Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_0202Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_0317Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_0332Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_0547Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_0602Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_0938z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_1003z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_1032Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_1047Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_1117z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_1234Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_1302Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_1517Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_1532Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_1702Z_cycle.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_1732Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_1802Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_1832Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_1847Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_1902Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_1917Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_1932Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_1947Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_2002Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_2017Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_20260924T1332Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_20260924T1417Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_20260924T1617Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_2032Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_2047Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_2102Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_2117Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_2132Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_2217Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_2232Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_2247Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_2302Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_2332Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/append_summary_2347Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/build_dec_1017Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/build_dec_1032Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/fix2_1717z.py",
  "?? research/hermes/trader_v1/run_state/tmp/fix3_1717z.py",
  "?? research/hermes/trader_v1/run_state/tmp/fix_1717z.py",
  "?? research/hermes/trader_v1/run_state/tmp/fix_2102Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/fix_a14_1017Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/fix_a14b_1017Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/fix_dec_0302.py",
  "?? research/hermes/trader_v1/run_state/tmp/fix_json_1047Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/fix_null_0938z.py",
  "?? research/hermes/trader_v1/run_state/tmp/fix_pct_1003z.py",
  "?? research/hermes/trader_v1/run_state/tmp/mk_dec_0047Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/mk_dec_0132Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/mk_dec_1547Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/mk_dec_1632Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/mk_dec_1647Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/patch_a14_2117.py",
  "?? research/hermes/trader_v1/run_state/tmp/peek_1047Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/peek_1632Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/plan1747_1932Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_0517z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_0532z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_0938Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_0947Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_1002Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_1003Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_1017Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_1032Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_1047Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_1102Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_1117Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_1202Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_1217Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_1302Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_1647Z.json",
  "?? research/hermes/trader_v1/run_state/tmp/probe_1817z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_20260924T1817Z.json",
  "?? research/hermes/trader_v1/run_state/tmp/probe_flat_20260924T1632Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_m15_0302.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_m15_0317b.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_m15_0317b_out.json",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_0147Z_err.txt",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_1832Z_err.txt",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_1847Z_err.txt",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_1917Z_err.txt",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_1932Z_err.txt",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_1947Z_err.txt",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_2002Z_err.txt",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1332Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1417Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1447Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1502Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1517Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1547Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1602Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1632Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1647Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1702Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1717Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1732Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1817Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1832Z.json",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1832Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1847Z.json",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1847Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1902Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1917Z.json",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1917Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1932Z.json",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1932Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1947Z.json",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T1947Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T2002Z.json",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T2002Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T2017Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T2032Z.json",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T2032Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T2047Z.json",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T2047Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T2102Z.json",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T2102Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T2117Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T2132Z.json",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T2132Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T2147Z.json",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T2147Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T2232Z.json",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T2232Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T2247Z.json",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T2247Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T2302Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T2317Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T2332Z.json",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T2332Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260924T2347Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260925T0002Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260925T0017Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260925T0032Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260925T0047Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260925T0047Z_out.json",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260925T0102Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260925T0102Z_out.json",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260925T0117Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260925T0117Z_out.json",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260925T0132Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260925T0132Z_out.json",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260925T0147Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260925T0147Z_out.json",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260925T0202Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260925T0217Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_20260925T0217Z_out.json",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_2032Z_err.txt",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_2047Z_err.txt",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_2102Z_err.txt",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_2117Z_err.txt",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_2132Z_err.txt",
  "?? research/hermes/trader_v1/run_state/tmp/probe_ro_2147Z_err.txt",
  "?? research/hermes/trader_v1/run_state/tmp/scan_1717z.py",
  "?? research/hermes/trader_v1/run_state/tmp/scan_1717z2.py",
  "?? research/hermes/trader_v1/run_state/tmp/schema_0938Z.txt",
  "?? research/hermes/trader_v1/run_state/tmp/sum_1802Z.txt",
  "?? research/hermes/trader_v1/run_state/tmp/summary_1717z.py",
  "?? research/hermes/trader_v1/run_state/tmp/verify_20260925T0117Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/verify_20260925T0132Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/verify_20260925T0132Z_out.json",
  "?? research/hermes/trader_v1/run_state/tmp/verify_20260925T0147Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/write_dec_0017Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/write_dec_0317z.py",
  "?? research/hermes/trader_v1/run_state/tmp/write_dec_0332z.py",
  "?? research/hermes/trader_v1/run_state/tmp/write_dec_0532z.py",
  "?? research/hermes/trader_v1/run_state/tmp/write_dec_0547z.py",
  "?? research/hermes/trader_v1/run_state/tmp/write_dec_0602z.py",
  "?? research/hermes/trader_v1/run_state/tmp/write_dec_0938z.py",
  "?? research/hermes/trader_v1/run_state/tmp/write_dec_1003z.py",
  "?? research/hermes/trader_v1/run_state/tmp/write_dec_1117z.py",
  "?? research/hermes/trader_v1/run_state/tmp/write_dec_1217Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/write_dec_2247Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/write_dec_2347Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/write_decision_0432.py",
  "?? research/hermes/trader_v1/run_state/tmp/write_decision_1947Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/write_decision_2032Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/write_decision_2047Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/write_decision_2102Z.py",
  "?? research/hermes/trader_v1/run_state/tmp/write_decision_2117Z.py",
  "?? research/hermes/trader_v1/run_state/trader_summary.txt",
  "?? research/hermes/trader_v1/tmp/",
  "?? research/hermes/trader_v1/trader_summary.txt",
  "?? research/hermes/trader_v2/execution/execution_guard.py",
  "?? research/hermes/trader_v2/observations/",
  "?? research/hermes/trader_v2/research/V2_BROKER_DEMO_ENABLE_20260918.md",
  "?? research/hermes/trader_v2/research/V2_G3_EXECUTION_INCIDENT_20260918.md",
  "?? research/hermes/trader_v2/research/V2_G3_FAIL.md",
  "?? research/hermes/trader_v2/research/V2_G3_FINAL_SHADOW_REPORT_20260918.md",
  "?? research/hermes/trader_v2/research/V2_G3_FINAL_SHADOW_REPORT_20260919.md",
  "?? research/hermes/trader_v2/research/V2_G3_VERDICT.json",
  "?? research/hermes/trader_v2/research/V2_LONG_RUN_AUDIT_20260918.md",
  "?? research/hermes/trader_v2/research/V2_RUNTIME_PROCESS_NETWORK_AUDIT_20260918.md",
  "?? research/hermes/trader_v2/research/V2_RUNTIME_PROCESS_NETWORK_AUDIT_20260919.md",
  "?? research/hermes/trader_v2/research/V2_SHADOW_HEALTH_20260917_0417.md",
  "?? research/hermes/trader_v2/research/V2_SHADOW_HEALTH_20260917_0822.md",
  "?? research/hermes/trader_v2/research/V2_SHADOW_HEALTH_20260917_1237.md",
  "?? research/hermes/trader_v2/research/V2_SHADOW_HEALTH_20260917_1637.md",
  "?? research/hermes/trader_v2/research/V2_SHADOW_HEALTH_20260917_2052.md",
  "?? research/hermes/trader_v2/research/V2_SHADOW_HEALTH_20260918_0052.md",
  "?? research/hermes/trader_v2/research/V2_SHADOW_HEALTH_20260918_0507.md",
  "?? research/hermes/trader_v2/research/V2_SHADOW_HEALTH_20260918_0907.md",
  "?? research/hermes/trader_v2/research/shadow_guardian.jsonl",
  "?? research/hermes/trader_v2/research/shadow_guardian_state.json",
  "?? research/hermes/trader_v2/runtime/atomic_io.py",
  "?? research/hermes/trader_v2/state/FORWARD_VALIDATION_ALLOWED",
  "?? research/hermes/trader_v2/state/SHADOW_ALLOWED",
  "?? research/hermes/trader_v2/state/V2_G3_EXECUTION_INCIDENT.json",
  "?? research/hermes/trader_v2/state/decision_contexts/",
  "?? research/hermes/trader_v2/state/hermes_decision_latest.json",
  "?? research/hermes/trader_v2/state/hermes_state.json",
  "?? research/hermes/trader_v2/state/v2_observe_only.json",
  "?? research/hermes/trader_v2/state/v2_scheduler_state.json",
  "?? research/hermes/trader_v2/tests/engine_harness/",
  "?? research/hermes/trader_v2/tests/test_execution_guard.py",
  "?? research/hermes/trader_v2/tests/test_mt5_only_source.py",
  "?? research/hermes/trader_v2/tests/test_run_lifecycle_fix.py"
 ],
 "v3_flags": {
  "V3_LIVE_ALLOWED": "NO",
  "V3_STRATEGY_FORWARD": "NOT_ENABLED",
  "V3_FORWARD_ALLOWED": "NO"
 },
 "BOUNDARY_VIOLATION": 1
}
```

```text
CANDIDATE_RESEARCH = 0（即使统计结果漂亮，也不得自动进入 Candidate / Forward / Shadow / Live）
测试为 READ/VERIFY ONLY：结果 JSON 未被测试修改，OUTPUT_HASH 可复算一致。
```

## 不提出补救措施（§21）

```text
本报告【不】提出以下任何一项作为本任务内的补救：降低频率门 / 延长历史 / 扩大定义 /
增加相邻事件 / 降低阈值 / 扩大持有时间 / 增加更多市场 / 调参数。
若要研究高频版本 M03，必须新建独立任务。
```

## 归档处置（§28/§29）

```text
M03 → RESEARCH_ARCHIVE，保留历史证据：
  63 events · 21 effective episodes · positive response · positive net edge · frequency gate failure
V3 主线机制状态更新：
  M01 = REJECTED · M02 = REJECTED · M03 = NOT_PROMISING_FOR_CURRENT_HIGH_FREQUENCY_GATE · M08 = REJECTED
=> 当前 Opportunity → Mechanism → Tradability 路线上，M03 也不能成为 V3 的高频候选。
下一阶段应回到 MARKET OPPORTUNITY DISCOVERY，寻找新的更高频且可执行的机会机制。
```

## SELF_CORRECTION_LOG（§69/§70）

```json
[
 {
  "what": "stray decorator line and incomplete tail in the first runner draft",
  "when": "before the first execution",
  "affected_data": false,
  "affected_method": false,
  "fix": "rewrote the runner completely",
  "rerun": "first execution"
 },
 {
  "what": "loader matched event members on cluster_key, which the R1 opportunity ledger does not persist -> 0/63 loaded; the INVALID_INPUT guard fired as designed",
  "when": "first execution of the corrected runner (before any result was computed)",
  "affected_data": false,
  "affected_method": false,
  "fix": "resolve members by rebuilding events exactly as R4 did and using the event's own member list",
  "rerun": "full re-run from the freeze gate"
 },
 {
  "what": "pandas unit mismatch: the state index is datetime64[us] while the derived null timestamps became ns -> searchsorted raised 'Cannot losslessly convert units'",
  "when": "execution, inside the null-redraw section (after responses were computed, before any result file was written)",
  "affected_data": false,
  "affected_method": false,
  "fix": "align query timestamps to the index unit with as_unit() before searchsorted",
  "rerun": "full re-run from the freeze gate"
 },
 {
  "what": "used random.Random for the block bootstrap but called numpy's .integers() -> AttributeError",
  "when": "execution, in the block-bootstrap section (no result file written yet)",
  "affected_data": false,
  "affected_method": false,
  "fix": "switched the bootstrap RNG to np.random.default_rng(SEED)",
  "rerun": "full re-run from the freeze gate"
 }
]
```