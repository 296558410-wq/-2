# V3 Demo Execution Start Report

`task = V3 新账户 Demo 下单启动` · `ts_utc = 2026-09-24T16:55:55.677872+00:00` · `VERDICT = HARD_STOP_STRUCTURAL`
`ORDER_SEND_CALLS_TOTAL = 0` · `GATES_CHANGED = NONE`

## 1. Git

```text
commit  = 545b4a3ffdc54b1f3828030bde6ea146857ab20a
short   = 545b4a3   (迁移基线，任务书指定)
branch  = fix/v2-full-system-repair-20260917
worktree: trader_v3 dirty 文件 = 4，其中 .py = 0
        -> 无未授权策略/参数/执行逻辑修改（.py 变更 = 0）
```

## 2. 账户

```text
old account   = 160764551 (NETTING, retired, password lost)
new account   = 160766418 (HEDGE)   <- ACTIVE
server        = ForexTimeFXTM-Demo01
margin mode   = 2 (HEDGE)
balance/equity= 500.0 / 500.0   margin=0.0 free=500.0
trade_allowed = True · positions = 0
account epoch = ACTIVE 160766418 · retired 160764551
```

## 3. 配置哈希

```text
config_hash            = d4d7607e425f971a6665ece223780e00ed7909130bfc72079f6eb7ea37db5c34
strategy_hash          = 42a3f488e2be5e8eabd1fd59940c1711f1eac72cf7f64ab272a35d81ba31d482   (foundation/entry_exit_interface.py —— V3 无策略模块，取该接口)
execution_hash         = 6810b1fa3ceb41615a775436d473a8d7f81fd5d659f5552d49bfa214e826e2d3   (mt5/v3_adapter.py)
calibration_pilot_hash = 2679b6a99191aa2c94d278d8ce7eb2b3976936a4eb647a3acea6ce3f730f4afb
```

## 4. 安全闸门（未改动）

```text
V3_LIVE_ALLOWED        = NO
V3_ORDER_SEND_ALLOWED  = NO     <- 未解除（硬停）
V3_FORWARD_ALLOWED     = NO
ORDER_PERMISSION_CHANGED = NONE
```

## 5. Dry-run（§9，ORDER_SEND = 0）

symbol filling bitmask = 1（FOK=True / IOC=False）
pilot._filling_mode() 选择 = ORDER_FILLING_FOK（值 0）→ 与 broker 匹配 ✓

| filling | value | retcode | comment | margin |
|---|---|---|---|---|
| FOK | 0 | 0 | Done | 8.55 |
| IOC | 1 | 10030 | Unsupported filling mode | 0.0 |
| RETURN | 2 | 10030 | Unsupported filling mode | 0.0 |

```text
结论：pilot 会选的 FOK 被 broker 接受（retcode 0, margin 8.55）。
      IOC/RETURN 被拒（10030）—— 与 pilot 源码注释中记录的坑一致，pilot 已正确处理。
order_send 调用次数 = 0
```

## 6. 首笔成交

```text
NOT_EXECUTED —— 未产生任何成交。
原因见 §9/§11：本任务要求首笔来自"正常 V3 signal pipeline"，而 V3 不存在该 pipeline（见 §11 硬停原因 1）。
未人工制造 signal、未强制下单、未绕过任何 guard。
```

## 7. Hedge 验证

```text
代码层（by inspection）:
  close_order_sets_position_field = True
  close_side_is_opposite          = True
  post_entry_position_count_assert= True
  post_roundtrip_flat_assert      = True
  verdict                         = HEDGE_SAFE_BY_CODE
实测层：UNPROVEN_LIVE（未下单，故 position/deal/order 映射未在真实 HEDGE 成交中验证）
```

## 8. 隔离

```text
V1 account 160759434 / magic 90002   （未触碰）
V2 account 160761384 / magic 90003   （未触碰）
V3 account 160766418 / magic 90004
V3 执行代码中出现的 V1/V2 magic = NONE
路径隔离：V3 只写 C:\AIQuant\research\hermes\trader_v3 与 C:\AIQuant\mt5_instances\fxtm_demo_v3calib
```

## 9. Calibration

```text
status = NOT_STARTED（未启动）
判据：启动 calibration 需要 V3_ORDER_SEND_ALLOWED=YES；而该开关的解除会使 v3_adapter.assert_readonly()
      按设计 raise（见硬停原因 2），即"启用下单 = 必须修改代码级安全守卫"，任务书明令禁止。
```

## 10. Forward

```text
status = NOT_STARTED
V3_EXECUTION_MODE = RESEARCH_READONLY（未变更）
```

## 11. 硬停原因（决定性）

### 原因 1 — V3 不存在 signal pipeline（§12 不可满足）

```text
在 trader_v3 全树中搜索 generate_signal / decide / entry_signal / strategy / on_bar / run_cycle：
  命中数 = 0
foundation/entry_exit_interface.py 自述为 stage-1 skeleton，且 ORDER_SEND = FALSE（声明为 hard invariant）
V3 唯一的真实下单路径 = foundation/calibration_pilot.py（冻结的预注册方向/持有序列，非 signal）
=> 任务书 §12 要求"首笔来自正常 V3 signal pipeline"，在 V3 中不存在该 pipeline；
   而 §3 禁止人工制造 signal / 强制下单 / 绕过 signal guard。
   要满足该条只能新增策略逻辑（=修改/新增策略），§3 明令禁止。
```

### 原因 2 — V3 在代码层硬拦截下单（解除闸门 = 修改安全守卫）

```text
mt5/v3_adapter.py:
  order_send 硬拦截 = True
  order_check 亦被拦截 = True
  assert_readonly() 要求三闸门全 = NO = True
=> 把 V3_ORDER_SEND_ALLOWED 置为 YES 后，V3 官方适配器 v3_adapter.connect() 会按设计 raise OrderSendBlocked。
   因此"解除闸门"必然要求修改代码级安全守卫 —— 任务书 §3/§26 禁止（不得绕过 execution safety / 不得修改 execution semantics）。
```

### 其他如实记录

```text
- 任务书内部不一致：§27 目标要求 V3_STATUS=RUNNING_DEMO（需 signal pipeline），但 §27 同时要求 V3_FORWARD_ALLOWED=NO；
  且 §11（恢复 calibration）与 §3（不得为 calibration 强行制造交易）存在张力。
- .env.mt5_v3_calib 的新账户密码尚未由用户填入（终端靠已保存会话工作）；
  若走需要显式 login 的路径，会缺凭据 —— 这是需要用户动作的前置项，非本任务可自行解决（也不允许在聊天中收集密码）。
```

## 12. 异常汇总

```text
reject / duplicate / retry / unknown execution = 0  （本次未发任何订单）
order_send 调用 = 0 · 闸门变更 = 0 · V1/V2/V3 文件未改（除本报告与状态文件）
dry-run 探针自身的 filling 取值错误（10030）已定位并修正 —— 非 V3 代码缺陷
```

## 最终结论

```text
V3_DEMO_EXECUTION = HARD_STOP（结构性问题，非执行层故障）
V3_STATUS         = RESEARCH_READONLY（未变）
V3_LIVE           = DISABLED
V3_ORDER_SEND_ALLOWED = NO（未解除，保持现场）
```

### 若要继续，需要你（用户）决定其一

```text
(a) 明确授权"修改 v3_adapter / entry_exit_interface 的代码级安全守卫"以允许 Demo 下单；并说明
    这是否视为"修改 execution semantics"（任务书禁止项）的例外；
(b) 或者先补齐 V3 的 signal pipeline（= 新增策略逻辑，属更大范围的新任务，需独立任务书）；
(c) 或仅授权"用 calibration pilot 验证执行链"（不声称是策略首笔），并同步解除闸门（仍需 (a) 的代码授权）。
三者都需要你先解决"代码级硬拦截"这一条，否则任何下单路径都不可用。
```
