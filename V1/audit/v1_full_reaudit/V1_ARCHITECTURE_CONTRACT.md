# V1 架构契约（V1_ARCHITECTURE_CONTRACT）

> 任何新增/修改代码不得突破本契约。违反即视为 DESIGN_DEFECT。版本 v1（2026-10-02）。

## 1. 组件职责（单一归属）

| 组件 | 允许做 | 禁止做 |
|---|---|---|
| **OpenClaw cron** | 定时触发 `cycle.py`（script payload，零 LLM）；投递报告 | 参与决策；读写风险/交易状态；承载策略记忆 |
| **Hermes**（本版缺席） | 提供推理信号（未来接入时） | 直接下单；绕过 RiskGuard；读写 MT5 |
| **Market Context**（`label_adapter`/`snapshot`/`atr`） | 把当时的实时数据转成信号上下文 | 持久化跨周期状态；引用未来数据 |
| **Decision**（`signal_baseline`） | 由 context 生成 signal → order_intent（纯函数） | 读取历史盈亏/胜负/旧仓位作为输入 |
| **RiskGuard**（`gates.RiskGuard`） | 唯一的一票否决闸门 | 自动平仓；修改意图；放宽限额 |
| **Execution**（`cycle.py` 执行段） | order_check → order_send（demo-only） | 在 RiskGuard 之前发单；跳过 demo 断言 |
| **MT5** | 券商事实权威；SL/TP 由券商托管 | —— |
| **Ledger**（`gates.Ledger`） | SHA256 追加链；唯一记录源 | 被随意改写；非经 append 的写入 |
| **Replay/Audit** | 从券商事实独立重算 | 用 V1 自算数字证明 V1 自算数字 |

## 2. 状态所有权（State ownership）

| 状态 | 所有者 | 恢复规则 |
|---|---|---|
| 未平仓/持仓 | MT5（实时读取） | 重启后**从 MT5 重读**，不从内存恢复 |
| 已实现盈亏 / CLOSE/PNL | Ledger（经 broker 对账写入） | 重启后**从账本回放** |
| 风控计数（daily/consecutive） | Ledger（派生） | 重启后**由 `rebuild_risk_state` 重建**（禁止留内存或独立 counter 文件） |
| 策略/信号上下文 | 无（设计为无状态） | **绝不恢复**：历史交易结果不得进入下一周期决策 |
| 调度 | OpenClaw cron | 由 cron 自身负责；无自愈要求（见 D008） |

## 3. 数据所有权（Data ownership）

- 实时行情（tick/M1）：MT5。任何“数据年龄”必须**同源**（服务器帧 − 服务器帧），禁止跨帧相减（D007）。
- 冻结资产（labeler 源码、mapping、state 序列）：只读，凭 SHA256 冻结；改动即新版本。
- 成本/口径：账本 PNL 若只含价差，**必须标注**；风险口径统一用净额（D004）。

## 4. 恢复规则（Recovery rules）

1. 重启后可恢复：风控计数、待对账 close、未平仓视图。
2. 重启后**不可**恢复：任何形式的策略记忆/历史结果反馈。
3. 恢复必须**幂等**：同账本 → 同状态（`rebuild_idempotent` 测试）。
4. 恢复失败必须 **fail-closed**（不可读账本/链断 → HALT），不得静默降级为“无保护”。

## 5. 隔离规则（Isolation rules）

- V1 与 V2/V3 **代码零引用**（双向已核对 = 0）。
- 命名空间：`MAGIC=90011`（不占用 90001/90002/90003）、`COMMENT=V1UP_DEMO`、**独立账本**。
- 账户沿用旧 demo 账户属**已授权偏差**；但命名空间隔离须保持。
- 任何跨 V1/V2/V3 的状态/数据共享需单独授权。

## 6. 安全不变量（必须始终成立）

1. `order_send` 仅存在于唯一的、被 demo 断言 + RiskGuard 通过 + `order_send_enabled` + 账户空仓 的路径上。
2. RiskGuard 只能**收紧**（deny-only），任何改动不得放宽限额或使其更易放行。
3. 缺数据 ⇒ 要么明确标注为“无保护”，要么 fail-closed；**不得**默认 PASS。
4. 账本链任何写入后 `verify()` 必须为 True；replay 必须确定。

## 7. 回归闸门

`v1up_regression_suite.py` 必须 100% PASS，否则 **CI/AUDIT FAIL**。覆盖：daily/consecutive/position/stale/slippage/duplicate/kill-switch/restart-recovery/ledger-chain/replay-determinism/seq。
