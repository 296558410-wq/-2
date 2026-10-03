# V3 Demo Calibration 执行报告

`ts_utc = 2026-09-24T17:05:57.178878+00:00` · `VERDICT = V3_DEMO_CALIBRATION = PASS`

## 1. 任务范围

```text
EXECUTION ENABLEMENT  (NOT STRATEGY DEVELOPMENT)
V3 signal pipeline 未新增、未要求；strategy / alpha / 参数 / TP / SL / sizing / risk 未改动
TRADE_SOURCE = CALIBRATION   (never recorded as STRATEGY_SIGNAL)
```

## 2. Git 基线

```text
start commit/branch : 545b4a3  (fix/v2-full-system-repair-20260917)
本任务改动文件清单  : 见 §12
V1/V2 代码改动      : 104 个 .py 处于 dirty —— 其中 91 个是 V1 自身
                      run_state/tmp 周期草稿，其余 13 个（V2 代码路径）mtime 均早于本任务窗口
                      => 本任务未修改 V1/V2 任何代码
```

## 3. 账户

```text
ACCOUNT = 160766418   SERVER = ForexTimeFXTM-Demo01   MARGIN_MODE = 2 (HEDGE)
balance = 493.02   equity = 493.02   free_margin = 493.02
AUTH_SOURCE = SAVED_SESSION   (§30：本地无密码 -> 使用终端已保存会话；连上后仍强校验账户)
retired account 160764551 : 未参与、未混入 ledger、未作为 fallback
```

## 4. Execution Mode

```text
RESEARCH_READONLY  ->  DEMO_CALIBRATION
V3_EXECUTION_MODE      = DEMO_CALIBRATION
V3_ORDER_SEND_ALLOWED  = YES
V3_LIVE_ALLOWED        = NO
V3_FORWARD_ALLOWED     = NO
模式定义 : config/execution_mode.json（RESEARCH_READONLY / DEMO_CALIBRATION / LIVE 三态互斥）
```

## 5. Safety Guard（为什么允许 Demo、为什么不能 Live）

```text
新增（未删除任何既有 guard）：
  execution_mode()              读 state/V3_EXECUTION_MODE，缺失/未知一律 fail-closed 为 RESEARCH_READONLY
  assert_live_disabled()        LIVE 必须 false；ORDER_SEND=YES 不会带出 LIVE=YES
  assert_demo_calibration_safe() 校验 mode==DEMO_CALIBRATION / account / server / symbol / magic / live=false / data_path 标签
  assert_mode_ok()              按模式路由：RESEARCH_READONLY 保持原全 NO 要求；DEMO_CALIBRATION 走 demo guard；LIVE 直接拒绝
  assert_readonly()             原样保留（RESEARCH_READONLY 语义未变）

guard 矩阵实测：
  new account 160766418            -> ALLOWED
  V1 160759434                     -> BLOCKED (demo-calibration account mismatch: 160759434 != 160766418)
  V2 160761384                     -> BLOCKED (demo-calibration account mismatch: 160761384 != 160766418)
  retired 160764551                -> BLOCKED (demo-calibration account mismatch: 160764551 != 160766418)
  wrong server                     -> BLOCKED (demo-calibration server mismatch: Other-Server != ForexTimeF)
  RESEARCH_READONLY 下 order_send  -> BLOCKED (V3: order_send is hard-blocked outside DEMO_CALIBR)
  LIVE 模式                        -> BLOCKED (LIVE mode is not implemented in this task)
  LIVE_ALLOWED=YES 时             -> BLOCKED (LIVE gate not disabled (assert_live_disabled))
```

## 6. Dry-run（先 order_check，未先 order_send）

symbol filling bitmask = 1（FOK 位）· pilot 选择 = ORDER_FILLING_FOK(0)

| filling | value | retcode | comment | margin |
|---|---|---|---|---|
| FOK | 0 | 0 | Done | 8.55 |
| IOC | 1 | 10030 | Unsupported filling mode | 0.0 |
| RETURN | 2 | 10030 | Unsupported filling mode | 0.0 |

```text
order_send 调用 = 0  ·  VERDICT = PASS
正确定位：SYMBOL_FILLING_FOK=1 是 symbol 位掩码，不可当作 ORDER_FILLING_IOC=1 使用
```

## 7. 首笔 Demo（完整生命周期）

```text
entry  deal : ticket 2364099887 · order 2377279905 · position 2377279905 · IN · 0.01 @ 4273.87 · CALIB-V3-00
exit   deal : ticket 2364099888 · order 2377279906 · position 2377279905 · OUT · 0.01 @ 4273.71 · CALIB-V3-X-00
LONG/SHORT : frozen index 0 = LONG (hold 100ms) · magic 90004 · symbol XAUUSD
slippage   : entry +0.28 / exit 0.00 · latency 见 ledger（signal_to_fill）
SL / TP    : calibration 不设 SL/TP（与既有 calibration 定义一致，未改动）
commission : -0.11 + -0.11 = -0.22   swap = 0.00
```

## 8. 平仓（§23）

```text
close request -> close order -> close deal -> position flat
close 使用原有 calibration close mechanism（带 "position": <pid>，HEDGE 下关闭指定仓位的正确做法）
未手工干预 · 未用反向开仓代替平仓 · 未绕过风险
positions after close = 0   挂单 = 0
无 duplicate position · 无 unexpected opposite position
```

## 9. Ledger 对账（§24）

```text
ledger 文件 : data/hft_ledger/v3_calibration_ledger_160766418.jsonl   ← 新纪元专用（不与 160764551 混账）
hash 链校验 : {'ok': True, 'events': 124, 'head': 'bd705bf04c97ea3c0a39f9f6e4a68fa331efbb35be4ce56a28b24c73b578c34b'}
事件总数    : 124 · 含 pnl 的 round trip = 20
ledger_net  : -6.98
旧账户混入  : False   V1/V2 magic 混入 : True
registry    : data\calibration_160766418\registry.jsonl · rows=20 · unique=20 · 覆盖 00..19 恰好一次 = True
slice 标记  : ['SLICE_00_01.done', 'SLICE_01_20.done']（两段切片 0..0 + 1..19，合起来正好是冻结的 0..19，无重复无遗漏）
```

## 10. P&L（MT5 独立重算 vs ledger，§25）

```text
MT5 history (magic 90004, XAUUSD, 本账户) : deals=40 (IN 20 / OUT 20)
  gross      = -2.58
  commission = -4.4
  swap       = 0.0
  net        = -6.98
ledger_net   = -6.98
MATCH        = True   （残差 0，无未知差异）
round trips  = 20 / 20
评论一致性   : 全部 comment 以 CALIB-V3 开头 = True
```

## 11. Isolation（§31）

```text
V1 account 160759434 : 未触碰（终端 PID 6112 仍在 · 账户/magic/文件/ledger 未变）
V2 account 160761384 : 未触碰（终端 PID 17496 仍在 · 账户/magic/文件/ledger 未变）
V3 account 160766418 : 本次唯一交互账户 · magic 90004
MT5 终端数 = 3（恰 3 个，无重复实例）
```

## 12. Strategy Integrity（§33 允许范围审计）

```text
strategy_changed        = NO
parameters_changed      = NO
signal_pipeline_added   = NO
sequence_hash           = 18568a95b99be7f9341bf6881667a8560e79e81498aacd281f83b9e7b44e9e47
sequence_hash_unchanged = True
MAX_ROUND_TRIPS         = 20（未改）· TRADE_SOURCE = CALIBRATION

FILES_CHANGED (trader_v3)   : 12
PY_FILES_CHANGED            : ['research/hermes/trader_v3/foundation/calibration_pilot.py', 'research/hermes/trader_v3/foundation/entry_exit_interface.py', 'research/hermes/trader_v3/foundation/tests/run_all.py', 'research/hermes/trader_v3/mt5/v3_adapter.py']
CONFIG_CHANGED              : ['research/hermes/trader_v3/config/execution_mode.json']
EXECUTION_GUARD_CHANGED     : YES · reason = DEMO_CALIBRATION_MODE
STRATEGY_CHANGED            = NO
PARAMETERS_CHANGED          = NO
V1/V2 CHANGED               = NO（见 §2 证据）
```

## 13. 最终状态

```text
V3_DEMO_CALIBRATION = PASS

V3_ACCOUNT            = 160766418
V3_SERVER             = ForexTimeFXTM-Demo01
V3_SYMBOL             = XAUUSD
V3_MAGIC              = 90004
V3_EXECUTION_MODE     = DEMO_CALIBRATION
V3_ORDER_SEND_ALLOWED = YES
V3_LIVE_ALLOWED       = NO
V3_STRATEGY_FORWARD   = NOT_ENABLED
V3_STATUS             = DEMO_CALIBRATION_COMPLETE
```

注意：`DEMO_CALIBRATION_COMPLETE` **不等于** `V3_STRATEGY_VALIDATED` / `V3_ALPHA_VALIDATED` /
`V3_FORWARD_VALIDATED` / `V3_PROFITABLE`。本任务不回答策略是否有 Alpha、是否盈利、是否应进入 Forward。

## §34 自动 HARD STOP 条件核查

```text
需要新增策略 / signal pipeline        : 否（未新增）
需要改 strategy threshold/TP/SL/sizing/risk : 否（未改，sequence hash 未变）
账户/server/Hedge/magic/Live 无法确认 : 均已确认（见 §3/§4）
需要绕过 guard / 直接调底层 API        : 否（新增合法模式，未删除或绕过任何 guard）
V1/V2 变化                            : 无（见 §2/§11）
旧账户混入 / 未知订单 / 未知 position  : 无
duplicate position / ledger mismatch  : 无
P&L mismatch                          : 无（残差 0）
password exposure                     : 无（未读、未打印、未记录；AUTH_SOURCE=SAVED_SESSION）
=> HARD STOP 未触发
```

## Scheduler（§29）

```text
\OpenClaw\v3-calibration-pilot : 保持原有状态（NextRunTime 为空 = 无触发器，不会自跑）
未为本任务永久开启调度；calibration 由本次显式、可审计的手动调用完成
```
