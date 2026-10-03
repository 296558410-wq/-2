# FORENSICS — 当前 vs 历史 分离与取证结论
只读取。**禁止把历史状态当当前状态。**

## 1. 当前 vs 历史 对照
| 维度 | 当前（实运行） | 历史（曾声明/曾运行） | 判定 |
|---|---|---|---|
| 代码 | 工作区实文件（含 75 项未提交改动 + 1 未跟踪文件） | 已提交历史（87 提交，止于 09-19 语境） | **当前代码 ≠ 已提交代码** |
| 执行模式 | 活跃 run `V2-PAPER-*`，`backend=paper_local` | config 声明 `BROKER_DEMO`/`broker_demo_enabled=true` | **声明 ≠ 实际** |
| 账户 | paper 账户 200→150（夹具） | config `initial_balance=10000` | **不一致** |
| 风控门 | `blocked=null`、无成交可检验 | 测试/fail-injection 判 PASS | 结构 PASS，**运行未验证** |
| 决策层 | `reference_rules` 占位器；`signal_from_agents=false` | docstring 称生产应为 LLM 编排 | **占位器在跑** |
| 成交 | **0**（券商 0 / 正式 paper 0） | ledger 含 1 次 `demo_calibration` FILL；paper 6 smoke | 历史=校准/夹具，**非真实** |
| 计数 | run 窗：wait 1059/trade 125/reject 25 | 全历史 memory：1443/167/61 | **口径不同** |

## 2. 取证要点（可追溯）
1. **券商无 V2 magic**：magic 集合 = {0, 90001, 90002, 90011}；无 V2 ⇒ V2 无券商成交（`EVIDENCE_MANIFEST.json` 无关，事实来自 MT5 `history_deals_get`）。
2. **V2 ledger 仅 12 条**（全 2026-09-11T13:09:29Z，`demo_calibration`）⇒ 非生产运行账本。
3. **决策 1671 条 0 结果标注**，`outcome=null` 全覆盖 ⇒ 无闭环反馈。
4. **opportunity 供给单一**：geo_shock 1442/2815（且有 806/1671 被选）⇒ 与 `research/OPPORTUNITY_DEGENERATION_DIAG_20260915.md` 结论一致（结构性）。
5. **PIT**：K 线 PASS；宏观/证据 **UNKNOWN/FAIL**（见 DATA_PIT_STATUS）。
6. **未跟踪文件** `execution/execution_guard.py` 存在于工作区但不在 git ⇒ 运行可能引用未版本化代码（**需在下一阶段显式声明/提交**）。

## 3. 判定（事实/推断/未知）
| 结论 | 等级 |
|---|---|
| V2 当前 RUNNING（run `…8b9e`），周期正常出数、agent OK、replay MATCH | **FACT** |
| V2 **从未产生真实成交**（券商=0；正式 paper=0；仅校准/夹具记录） | **FACT** |
| 决策层为 `reference_rules` 占位器，Agent 输出未进入下单路径 | **FACT**（`signal_from_agents=false`） |
| 执行模式声明（BROKER_DEMO）与实际（PAPER）不一致 | **FACT**（config vs run/paper_account） |
| 宏观/新闻证据 PIT 不可认证 | **FACT**（release_timestamp 全缺；point_in_time_valid 全 unknown） |
| 运行代码含未提交改动 + 未跟踪文件 | **FACT**（git status） |
| “为何 167 TRADE 决策 0 执行”的**逐条链路定性** | **INFERENCE**（占位器 + requires_confirmation + 供给单一；无逐条证据时不下更细结论） |
| 任何未来 P&L 预期 | **UNKNOWN**（无成交） |

## 4. 边界声明
- 本审计**未**修改 V2 任何代码/配置/参数/账本/状态；**未**停 scheduler；**未**发单（`order_send=0`）；V1 完全隔离（仅读）。
- 生成物仅写入 `research/hermes/trader_v2/audit/V2_FULL_STATE_SNAPSHOT/`（新目录）。
- 所有数值均可回溯至 `EVIDENCE_MANIFEST.json` 所列源文件（含 sha256）。
