# 重启前后差异（RESTART_DIFF）

> 目标：**重启是否改变了 Hermes 决策行为**。只列可用证据；不可复原者标 `UNKNOWN`，不用时间先后推因果。
> 数据：`RESTART_FACTS.json`（本目录）+ 既有审计（`v1_loss_forensics/`、`v1_audit/`、`trader_v2/research/`）。

## 1. 新 V1（v1_upgrade, magic 90011）
- **重启时点**：host `LastBootUpTime` = **2026-10-01T13:52:15Z**（21:52:15 GMT+8）；python 21:54 起。
- **调度**：OpenClaw cron `v1-upgrade-demo-cycle`（`3-59/15 * * * *` UTC）存活；**漏 1 拍（14:03Z）**，14:18Z 恢复（缺口 30.0min）；无专用看门狗。
- **重启余留状态**：空仓/无挂单；无跨重启 CLOSE。
- **决策行为对照**：
  - truth 快照 34 条**全部在重启之后**（truth 系统 2026-10-02 才上线）⇒ `before` 组为空，**无法**用快照对比重启前后 —— `DATA_GAP`（不是“无差异”）。
  - ledger（09-28→10-02）跨重启连续：`signal_source=BASELINE_TRANSITION`、`signal_type=BASELINE_CONTROL` 全窗恒定，`not_hermes_alpha=true`；重启前后**决策层未变**（`FACT`）。
  - 已知事实：接线缺陷（守卫未接）在重启**之前**即存在，修复在其**之后**（commit `63d5a22`/`eceeec2`，2026-10-02 ~03:51Z）⇒ 重启与修复是两个独立事件。
- **同输入重放**：`hermes_input_hash` + `sha256` 每条快照已存；输入正文未存 ⇒ 本轮**未做输出重放**（`REPLAY_INPUT_HASH_ONLY`）。既有审计（2026-09-14 循环）记录 `replay MATCH`（机械控制臂映射）。
- **判定**：**`NO_EVIDENCE_OF_RESTART_CAUSALITY`**（沿用并复核 `v1_loss_forensics/`）：重启前后正确语义状态相同（daily +38.99 / consecutive 0）、无持仓、无状态可失；漏 1 拍属未知反事实，**不构成**因果证据。

## 2. 旧 V1（trader_v1, magic 90002）
- **重启记录**：2026-09-09 ~06:07–06:12Z（系统自动更新重启，正常）；2026-09-14（另有）。无逐次程序级快照留存。
- **决策输入**：**早期决策完整输入已轮转**（`run_state` 现仅覆盖 09-23→09-28；09-07→09-17 的 794 份决策中仅 `state_summary` 级别留存）⇒ 重启前后**输入是否改变 = `UNKNOWN`**（v1_audit class-E）。
- **同输入重放**：**`NOT_POSSIBLE`**（无输入快照）。
- **判定**：**`UNKNOWN`** —— 证据不足以判“重启改变了 Hermes 行为”。不得用“重启后开始亏”这一时间先后写成因果。

## 3. V2（trader_v2, PAPER）
- **运行形态**：按 run 分窗（如 `V2-SHADOW-20260917-105319-b5e4` 48h；`...-021627-f80e`）；Windows 任务 `hermes-v2-cycle`（15m）。V1/V2/V3 进程独立（MT5 PID 分开）。
- **重启/环境变更证据**：
  - MT5 读取与执行武装**耦合**（`execution/fxtm_demo_adapter._gate()` 同时把守行情与执行）⇒ PAPER（broker=false）下 MT5 只读行情也被拒，router 静默回退 `local_fxtm/sina`（23:22Z、23:30Z 实测）。**行情源在“重启/配置变更”下间接改变**（`DATA_PIPELINE_CHANGE`，`FACT`）。
  - run `f80e` 的 G3 验收 = **FAIL**（`provenance_missing`、replay/provenance/instrument 关键不一致）。
- **决策行为对照**：`decision_source=reference_rules` 全窗恒定（占位参照器，非 LLM）；机会供给结构性坍缩（`opp_geo_shock` 148/148 周期）。
- **同输入重放**：`f80e` 2 周期 `replay_mismatch=[]` 但 `provenance_missing` ⇒ **`PARTIAL`**。
- **判定**：重启改变的是**行情源可达性（pipeline）**，**不是** Hermes 决策行为；且 0 成交 ⇒ 无 P&L 因果。

## 4. 三系统汇总
| 系统 | 重启证据 | 输入是否变 | 行为是否变 | 同输入重放 | 判定 |
|---|---|---|---|---|---|
| V1_NEW | 10-01T13:52Z（+漏1拍） | 否（控制臂恒定） | 否 | INPUT_HASH_ONLY | `NO_EVIDENCE_OF_RESTART_CAUSALITY` |
| V1_OLD | 09-09 / 09-14 | `UNKNOWN`（输入轮转） | `UNKNOWN` | NOT_POSSIBLE | `UNKNOWN` |
| V2 | per-run / 配置变更 | 源可达性变（pipeline） | 否（参照器恒定） | PARTIAL | 非因果（0 成交） |

**结论（Q5）**：**没有证据**表明任一系统的重启改变了 Hermes 的**决策行为**；能观察到的重启效应属于**数据管道可达性（V2）**，不是 Alpha/行为变化。
