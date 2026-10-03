# EVENT_TIMELINE — V2 关键历史事件
来源：`git log`（V2 树 87 提交）+ `state/*` 时间戳 + `research/V2_*.md` + 既有 MEMORY。
格式：`时间 → commit/config → 变化内容 → 是否影响决策/交易`

| 时间(UTC) | commit/config | 变化内容 | 影响决策/交易? |
|---|---|---|---|
| 2026-09-11 | `f3bf407` | V2 Phase-1 baseline：隔离骨架 + 架构 + config + 国内数据源调研 | 建立（无成交） |
| 2026-09-11T13:09Z | `ledger/hermes_v2_ledger.jsonl` | `demo_calibration` 自测序列（12 事件，含 1 FILL/1 REJECT） | 无（校准） |
| 2026-09-11T13:33Z | `state/hermes_memory` 起 | 开始逐周期决策记录 | 是（决策记录起） |
| 2026-09-13~14 | run `…7a88` | 记录中的“数据瞎期” | 是（候选质量） |
| 2026-09-15 | （MEMORY） | V2 全系统抢修：崩溃/开关/metrics/ledger 截断修复 | 是（稳定性） |
| 2026-09-16 | （MEMORY） | broker 自动平仓对账 BLOCK + DXY 递归 + GC/spot 标尺审计修复 | 是（对账/数据） |
| 2026-09-17 | `6f67f1f` | P0-01：统一 instrument=XAUUSD（config/agent1/agent2/context/hermes/router/price_space） | 是（标的无歧义） |
| 2026-09-17 | `359e495` | P0-02：router = 唯一取数入口；移除 hidden env override；V1 数据隔离断言 | 是（取数唯一化） |
| 2026-09-17 | `8b6f064` | P0-04：freshness 改按 `data_ts`；health 入 Hermes 门（FAIL→REJECT, DEGRADED→WAIT） | 是（决策门） |
| 2026-09-17 | `a6229b1` | P0-05：不可变 PIT as-of 缓存（`get_asof`）+ router 接线 | 是（PIT） |
| 2026-09-17 | `18a440c` | P0-03/P1-01：宏观核心 fail-closed（DEGRADED 不降级为 NEUTRAL） | 是（宏观门） |
| 2026-09-17 | `7284f10`/`b002054` | forward gate 全入口加固；未认证 forward run 锁死 | 是（准入） |
| 2026-09-17 | `d364f5d` | 券商止损预校验 fail-closed + live symbol spec probe | 是（执行安全） |
| 2026-09-17 | `e0f2a6a` | P1-b：决策输入快照 + 离线回放（`decide_pure`）+ fail-closed | 是（可回放） |
| 2026-09-17 | `0e33811` | P1-e/f：LLM 独立性 7/7 + 失败注入 13/13 fail-closed | 否（验证） |
| 2026-09-17 | `1d7fa24` | 数据层改为 **国内 + MT5-only**（历史走 V2 MT5；报价/宏观走 sina/tencent；移除 yahoo/eastmoney/CFTC/BLS） | 是（数据源） |
| 2026-09-17 | `6d1e9fd` | shadow guardian 接入调度周期（每周期校验 + 4h/24h/48h 门） | 是（监控） |
| 2026-09-17 | `503b104` | 面板重建为中文驾驶舱（旧面板全部保留）；tests 81/81 | 否（展示） |
| 2026-09-17 | `363c620`/`1af2e03`/`8d997fb`/`0fc0f30` | G3 冻结 + run lineage + 初始 final report（INSUFFICIENT_EVIDENCE）；面板 supervised autostart | 部分（冻结/守护） |
| 2026-09-18 | `research/V2_BROKER_DEMO_ENABLE_20260918.md` | BROKER_DEMO 启用相关记录 | 是（执行模式） |
| 2026-09-18 | `research/V2_LONG_RUN_AUDIT_20260918.md` | 48h 长跑审计：**LONG_RUN_READY_WITH_OBSERVATION**；发现并修 MT5 读取/执行耦合→回退 | 是（数据/执行） |
| 2026-09-18T13:27Z | `state/V2_G3_EXECUTION_INCIDENT.json` | G3 执行事件记录 | 是（事件） |
| 2026-09-19 | `research/V2_G3_FINAL_SHADOW_REPORT_20260919.md`、`V2_RUNTIME_PROCESS_NETWORK_AUDIT_20260919.md` | G3 最终 shadow 报告 + 运行态/网络审计 | 部分 |
| 2026-09-29T04:23Z | `state/v2_run_health.json.pre-monfix.bak` | 监控修复前的备份（“monfix”） | 否（监控） |
| 2026-10-01T14:37Z | `v2_run_health.last_failure` | **`PAPER_REPLAY_MISMATCH`**（run `…484f`，net_pnl/trade_count/commission 均 false） | 是（阻断该 run） |
| 2026-10-01T20:52Z | `state/runs/ACTIVE.json` | 当前 run **`V2-PAPER-20261001-205202-8b9e`** 启动 | 是（当前 run） |
| 2026-10-02T14:07Z | `v2_scheduler_state` | 当前周期 WAIT；cycles 累计 1306 | 是（当前） |

## 说明
- **配置变化**：`config/v2_config.json` 目前 **dirty（未提交）**；声明 `execution_mode=BROKER_DEMO`/`broker_demo_enabled=true`，而实际跑 PAPER（见 FORENSICS）。
- **重启/故障/修复**：V2 由 Windows 任务驱动（无 OpenClaw 依赖）；运行态显示 `missed_cycles=17`、`recovery_count=5`（调度补跑），`last_failure` 1 次 replay mismatch。
- **连续亏损 / 交易异常**：**无**——V2 无成交，故无连续亏损或成交异常（`exec_rejected_total=3` 为历史累计拒单）。
- **审计异常**：G3 `f80e` 曾判 **FAIL**（provenance_missing）；长跑审计为 READY_WITH_OBSERVATION。
