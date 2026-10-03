# V1 全量架构审计（V1_FULL_ARCHITECTURE_AUDIT）

- 范围：`research/hermes/trader_v1/v1_upgrade`（magic 90011，FXTM DEMO），从零重审。
- 口径：**MT5 券商事实 > Ledger > 声明**；只读；本次 `order_send=0`；不改策略/阈值/成本锚。
- 证据文件：`V1_RISK_RUNTIME_MATRIX.json` / `V1_EXECUTION_AUDIT.json` / `V1_LEDGER_REPLAY_AUDIT.json` / `V1_PIT_DATA_REGISTRY.json` / `V1_ALPHA_STATS.json` / `V1_DEFECT_REGISTER.json`。

## 1. 运行链路（实际，非文档）

```text
OpenClaw cron `v1-upgrade-demo-cycle` (3-59/15 * * * * UTC, script payload)
   → exec: .venv/python cycle.py --exec demo            [零 LLM]
        → MT5 initialize(path/login, DEMO)               gates.DemoGate.assert_demo
        → reconcile_broker_closes()  (broker deals → ledger CLOSE/PNL, idempotent)
        → snapshot() (tick)  +  atr_m15()                [市场上下文]
        → RiskGuard.evaluate()  ← rebuild_risk_state(ledger) + data_age + slippage   [风控]
        → live_state_family() ← label_adapter (冻结 9-state, M1→M15)
        → signal_baseline.signal_for_state() + order_intent()   [决策 = 控制臂]
        → ledger.append(DECISION)
        → [若 ENTER] order_check → order_send → FILL → POSITION
        → MT5 券商 SL/TP 平仓 → 下一周期 reconcile → CLOSE + PNL
   → Ledger (SHA256 链) → replay()/审计
```

## 2. 逐层职责与设计正确性

| 层 | 职责 | 判定 | 说明 |
|---|---|---|---|
| OpenClaw | 调度 + 投递（script payload） | ✅ 正确 | **不在决策链路内**（零 LLM），只做定时；设计干净 |
| Hermes | （本版**缺席**）推理内核 | ⚠️ BY_DESIGN | 本版信号 = `BASELINE_TRANSITION` 控制臂，**不是** Hermes；registry 明示 predictor UNSUPPORTED |
| Market Context | tick/ATR/live 9-state | ✅ 正确 | 输入即取即用，无跨周期缓存 |
| Decision | family→signal→order_intent | ✅ 正确 | 纯函数、无记忆；LONG/SHORT 由 MA20 趋势符号定 |
| RiskGuard | 6+1 条声明限额 | ❌ 曾失效（D001） | 已修（见 §4）；DUPLICATE_ORDER/KILL_SWITCH 仍未接线 |
| Execution | order_check→order_send | ✅ 正确 | demo-only；filling 位掩码按名映射；单发单点 |
| MT5 | 券商 | ✅ | 事实权威 |
| Ledger | SHA256 追加链 | ✅ 正确 | verify/replay 通过 |
| Replay/Audit | 独立重算 | ✅ | 与券商事实对平 |

## 3. 结构性问题（设计层）

- **`cycle.py` 是“上帝模块”**：把对账（broker→ledger）、风控、信号、执行、写账本混在一个 `main()`。职责越界，但**未造成错误**；列为 DESIGN 观察（非缺陷）。
- **孤立性验证不在运行链路里**：`DemoGate.assert_isolation` 只在 `run_gates.py`（离线自测）被调用；运行链路只调 `assert_demo`。即“命名空间隔离”是**约定**而非运行时强制（MAGIC/COMMENT 是常量）。列 OPERATIONAL 观察。
- **单点**：唯一调度器（cron，无看门狗，D008）；唯一终端路径/账户；账本单文件（有 quarantine 归档）。

## 4. 运行时矩阵结论（`V1_RISK_RUNTIME_MATRIX.json`）

| 规则 | 核心阻断(A–D) | 含数据异常(E) | 备注 |
|---|---|---|---|
| MAX_POSITION | PASS | PASS | 实时输入 |
| MAX_DAILY_LOSS | PASS | **FAIL** | 已接线；E：券商数据缺失→计数偏低（D009） |
| MAX_CONSECUTIVE_LOSS | PASS | **FAIL** | 已接线；同上 |
| STALE_DATA | PASS | PASS | 同源服务器帧；None→deny |
| SLIPPAGE_LIMIT | PASS | **FAIL** | 已接线；E：无成交史→按 0（D009） |
| DUPLICATE_ORDER | **FAIL** | FAIL | 结构性不可达（D002） |
| KILL_SWITCH | **FAIL** | FAIL | 无任何运行路径可置位（D003） |

**“设计存在 ≠ 运行时生效”**：修复前 4 条声明限额虽有代码但**零阻断能力**（D001）；修复后 5 条具备核心阻断能力。

## 5. 状态 / 隐式状态 / 污染

- **状态丢失（曾）**：风控计数器每周期归零（D001，已修）。现从账本回放重建，确定、可复算。
- **隐式状态**：`label_adapter._M` 模块缓存；`Ledger._last()` 每写读全文件；`RiskGuard.day`。均可复算，无隐患。
- **该恢复 / 不该恢复**：应恢复 = 风控计数、未平仓（取自 MT5 实时）、待对账 close（取自券商）。**绝不能恢复** = 策略记忆（本版信号无记忆，天然满足“每天面对新市场，不把历史结果变成下一日依据”）。
- **污染**：V1 代码对 V2/V3 引用 = **0**（双向核对）；账本与券商事实一致（§6）。无跨组件数据污染。

## 6. 账实一致性（`V1_LEDGER_REPLAY_AUDIT.json`）

- 账本链 `verify()`=True；seq 连续无缺口；重复事件 0。
- 独立重算（券商事实）：持仓 32 / 已平 32；价差分量 −11.44 == 账本 PNL 合计 −11.44（match）；净额另含 commission/swap。
- `replay()` 确定性（同输入同输出）。

## 7. 结论

架构**骨架正确**（职责清晰、零 LLM 调度、demo-only、账本链、无污染）；**风险层曾整体哑火**（已修）；仍有 2 条声明规则（DUP/KILL）未接线、3 条限额的数据异常路径非 fail-closed。详见 `V1_FINAL_STATUS.md` 评级。
