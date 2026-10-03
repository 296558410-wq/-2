# V1 最终状态（V1_FINAL_STATUS）

- 生成：2026-10-02 · 范围：`research/hermes/trader_v1/v1_upgrade`（magic 90011，FXTM DEMO）
- 口径：MT5 券商事实 > Ledger > 声明；只读；本次 `order_send=0`。
- 证据：本目录 12 个文件 + `V1_ALPHA_STATS.json` + `V1_REGRESSION_SUITE_RESULT.json` + 生成脚本。

## 1. 评级（每项：PASS / FAIL / UNKNOWN / DATA_BLOCKED）

| 维度 | 评级 | 依据 |
|---|---|---|
| ARCHITECTURE | **PASS** | 层职责清晰、零 LLM 调度、demo-only、无跨系统污染；`cycle.py` 上帝模块、孤立性断言不在运行链路 = 观察项 |
| DATA | **PASS** | 实时输入即取即用；roll/exposure 无缓存污染 |
| PIT | **PASS** | 决策输入按构造 PIT；labeler/mapping 冻结可哈希；对账延时属独立项 |
| SIGNAL | **PASS** | 控制臂实现正确、纯函数、无记忆；但**非 Hermes、无 alpha 语义** |
| RISK | **FAIL** | 4 条声明限额已修复且核心阻断 PASS；但 `DUPLICATE_ORDER`、`KILL_SWITCH` **零阻断能力**（D002/D003），且 3 条限额数据异常路径非 fail-closed（D009） |
| EXECUTION | **PASS** | 宣称==券商逐笔；单发单点；demo 断言；filling 按名映射；拒单均在授权前/休市 |
| ACCOUNTING | **PASS** | 链 True、seq 连续、独立重算价差分量一致；净额口径已文档化（D004 缓解） |
| RECOVERY | **PASS** | 修复后风控计数可从账本幂等重建；无 `RESTART_STATE_BUG` |
| REPLAY | **PASS** | 同输入同输出；replay 确定；独立重算与账本一致 |
| STATISTICS | **UNKNOWN** | 检验流程正确，但 n=32 无功效（`TEMPORAL_EVIDENCE_INSUFFICIENT`） |
| ALPHA | **UNKNOWN** | 控制臂、无 edge、成本后为负；证据不足 |
| MOAT | **PASS** | 7 项护城河资产已建立且可自动复跑 |

## 2. 两个独立结论（严禁混同）

```text
ENGINE STATUS = FAIL        # 工程质量尚未达到“可长期运行 + 持续研究”标准
ALPHA STATUS  = UNKNOWN     # 无足够证据证明可交易 alpha（且方向为负）
```

**ENGINE STATUS 为 FAIL 的阻塞项（可执行清单）**：
1. V1-D002 `DUPLICATE_ORDER` 结构性失效（无阻断能力）。
2. V1-D003 `KILL_SWITCH` 无运行路径可置位（无阻断能力）。
3. V1-D009 3 条限额数据异常路径非 fail-closed（缺数据→计数偏低/滑点按 0）。
4. V1-D005 券商平仓→账本对账延时（最高 ~31h）。
5. V1-D008 无看门狗、重启漏拍无补偿。
6. V1-D004/D010 账本成本口径与 replay 瑕疵。
> 注：核心安全闸门（POSITION/DAILY/CONSECUTIVE/STALE/SLIPPAGE）**已修复并验证**，故引擎**可运行**，但未达“工程标准”。

## 3. 十一个问答

1. **设计正确的地方**：OpenClaw 只做调度不决策（零 LLM）；信号纯函数无记忆（“每天面对新市场”原则成立）；demo-only + 命名空间隔离；账本 SHA256 追加链 + 独立 replay；broker 管 SL/TP、引擎只观察。
2. **设计缺陷**：`cycle.py` 上帝模块（对账/风控/信号/执行同处）；风控状态所有权未定义（直接导致 D001）；孤立性断言不在运行链路；无看门狗/补偿（D008）。
3. **实现 BUG**：D001（4 条限额零阻断，已修）；D002（DUP 不可达）；D003（KILL 不可达）；D007（跨帧 stale 负值，已修）；D010（replay 非票据键）。
4. **被污染的历史结果**：整个窗口 32 笔均在**风控哑火**下执行（D011）；其中 **8 笔**“应拒而放行”为明确 CONTAMINATED；全部 32 笔的**风控有效性**维度不可信（账实/价格维度仍 VALID）。口径：账实 VALID；风控策略 CONTAMINATED。
5. **RiskGuard 当前是否真正可靠**：**部分**。核心 5 条已可真实阻断并通过回归；**不完整**——DUP/KILL 零阻断，且缺数据时非 fail-closed。故 RISK=FAIL。
6. **MT5 → Ledger → Replay 是否完全一致**：**一致**。链 True、seq 无缺口、独立重算出价差分量 −11.44 == 账本合计；差异仅在成本项口径（已注明）。
7. **Restart 后是否安全**：**是（修复后）**。无 `RESTART_STATE_BUG`；风控计数幂等重建；无持仓残留；唯一缺陷是漏 1 拍无补偿（D008）。
8. **V1 alpha 现有证据**：**无**。n=32、t≈−0.3、p=0.78、CI 含 0、成本后为负；且是控制臂。判定 `TEMPORAL_EVIDENCE_INSUFFICIENT` / `NO_VALIDATED_EDGE`。
9. **已建立的可复用护城河**：数据/PIT registry、失败知识库、缺陷库（13 条）、replay 工具、执行指纹、14 项回归套件、架构契约（见 `V1_MOAT_REGISTER.md`）。
10. **仍有 FAIL / UNKNOWN**：RISK=FAIL；STATISTICS/ALPHA=UNKNOWN；D002/D003/D005/D008/D009/D010 OPEN。
11. **下一步最重要的一件事**：**给风控补 fail-closed 语义并接线 DUP/KILL**（把“缺数据/重复/急停”从“无保护”变成“拒单”），使 RISK 从 FAIL 转 PASS。这是继续运行前的最高优先级；alpha 研究在 n 远不足前不应推进。

## 4. 边界声明

未改策略/信号/阈值/成本锚（除已授权并单独验证的 D001 风控接线）；本次 `order_send=0`；未触碰 V2/V3；未恢复真实下单。
