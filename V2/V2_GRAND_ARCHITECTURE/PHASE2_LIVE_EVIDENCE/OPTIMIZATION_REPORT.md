# OPTIMIZATION_REPORT — V2 Phase 2 运行优化

> 目标：保持 V2 Production 与 Shadow 研究**逻辑完全不变**，只把 15-min shadow runner
> 改成「闭市便宜、开市自动恢复全流水线、且不再产生周期空转 churn」。终态 `OPTIMIZED_CONTINUOUS`。
> 本次改动 **全部** 位于 `PHASE2_LIVE_EVIDENCE/`；未创建/修改任何 scheduler；runner 不做 `git commit`。

---

## 1. 改动清单（what / why）

| 文件 | 改动 | 原因 |
|---|---|---|
| `runner/paths.py` | 新增 `is_market_open()`；新增 `write_text_if_changed()` / `write_json_if_changed()`；输出根 `P2` 支持 `V2_PHASE2_ROOT` 环绕（仅用于隔离自测，正常运行时未设置 → 行为不变） | C1 分支信号；C3 写-仅在内容变化时；隔离自测 |
| `runner/heartbeat.py` | **新增**。轻量 heartbeat 记录（C1）+ `MARKET_REOPEN_RECOVERY` 记录（C2）；`scheduler_status()` 只读查询计划任务；append-only `shadow/heartbeat.jsonl`；`shadow/market_state.json` 仅在状态切换时变化 | C1/C2 核心 |
| `runner/build.py` | `--live` 按 `market_open` 分支：闭市 → `run_closed()`（heartbeat-only）；开市 → `run_open()`（全流水线 + 首次闭合→开市记 `MARKET_REOPEN_RECOVERY`）；`--market-open` 自测开关；报告改用 write-if-changed；FINAL 状态改 `OPTIMIZED_CONTINUOUS` | C1/C2/C3/C5 |
| `runner/shadow_stack.py` | `run_live(force_open=False)`；闭市**不再写 stream**（不再 append `MARKET_CLOSED` 行），只写一行 log | C1：闭市不得新增 decision/outcome/sample |
| `runner/analytics.py` | 全部报告改 `write_text_if_changed` / `write_json_if_changed`（`DATA_MANIFEST.json` 忽略易变 `generated_utc`） | C3：不再每 15min 重写未变报告 |
| `runner/gpu_batch.py` | `gpu_stats.json` / `GPU_USAGE_REPORT.md` 改 write-if-changed | C3 |
| `runner/stability_check.py` | `shadow/state.json` 改 write-if-changed；`SHADOW_MODULES` 纳入 `heartbeat.py` | C3 / 自检完整性 |

**未改动**：`backfill.py`、`make_manifest.py`、任何 strategy/参数/RiskGuard/成本/研究结论、V2 Production、V1/V3、调度任务与 launcher（`\OpenClaw\hermes-v2-shadow-evidence` + `hermes-v2-shadow-evidence-hidden.vbs` 原样）。
`backfill.py` 逻辑未动 —— 闭市路径根本不调用它，所以无需改它。

### C1–C5 映射

- **C1 MARKET_CLOSED → heartbeat only**：`build.py --live` 读到 `v2_run_health.json: market_open == false`（或 `cycle_result` 含 `CLOSED`）即走 `run_closed()`，只 append 一条 heartbeat，随后退出。heartbeat 含：heartbeat、scheduler liveness、V2 production status、shadow scheduler status、last successful cycle、next scheduled cycle、data-source health、replay health、current strategy count；状态为 `MARKET_CLOSED_ALREADY_RECORDED`（首次为 `MARKET_CLOSED_RECORDED`）。**跳过** GPU batch / heavy analytics / duplicate backfill / scorecard 重算；**不新增**任何 decision/outcome/sample。
- **C2 MARKET_OPEN → full pipeline, auto-resume**：`run_open()` 依序 `live → outcome backfill → strategy evaluation → analytics → lifecycle → degradation → competition → replay`，无需人工重启。首次 closed→open 切换写 `MARKET_REOPEN_RECOVERY`，确认 data-time continuity / closed 窗内无错误 / PIT normal / replay PASS / `order_send=0`。
- **C3 write-if-changed**：`write_*_if_changed()` 仅在内容变化时落盘；heartbeat 为小体量 append-only 记录。
- **C4 git checkpoint policy**：runner 全程**不** `git commit`（保持原状）；checkpoint 只在 stage 事件由 parent 执行。
- **C5 preserve semantics**：研究逻辑 / PIT / 17 strategies / scorecard 定义 / Phase 2 结论均不变。

---

## 2. 周期成本 before / after

| 路径 | 之前 | 现在 |
|---|---|---|
| MARKET_CLOSED | 全流水线：`run_live` → `backfill` → `gpu_batch` → `analytics` → `stability` → 重写 ~7 个 timestamped 报告；实测单周期 ~80.6s（`v2_run_health.json: cycle_seconds`），接近分钟的 git churn | heartbeat-only：实测 **1.41s**，0 GPU、0 analytics、0 backfill、0 报告重写 |
| MARKET_OPEN | 全流水线 | 全流水线（不变），自动恢复，首次切换额外记 `MARKET_REOPEN_RECOVERY` |

---

## 3. 验收证据（acceptance evidence）

### 证据 1 — 闭市真实周期只走 heartbeat，且 stream 不增长（stream 维持 5820）

真实环境连续跑 2 次 `runner/build.py --live`：

```
[build] MARKET_CLOSED heartbeat-only status=MARKET_CLOSED_RECORDED stream_rows=5820 gpu_ran=False analytics_ran=False
[build] MARKET_CLOSED heartbeat-only status=MARKET_CLOSED_ALREADY_RECORDED stream_rows=5820 gpu_ran=False analytics_ran=False
```

前后计数（`LIVE_EVIDENCE_STREAM.jsonl` / `OUTCOMES.jsonl`）：

```
before: stream_lines=5820  outcome_lines=22144
after : stream_lines=5820  outcome_lines=22144
```

→ 闭市路径**没有**新增 decision / outcome / sample；`stream` 维持 **5820**。新增物仅为 append-only 的 `shadow/heartbeat.jsonl`（2 条）与 `shadow/market_state.json`。

### 证据 2 — 闭市时 GPU 被跳过

- 两次闭市运行中 `shadow/gpu_stats.json` 的 SHA256 **完全一致**：
  `849de44d3bf0fc7a01f6191167168ce2258ed3c5f438477c9b08dcade17cdce2`（before = after）。
- 闭市路径**不 import** `gpu_batch`（分支内才 import），`run_log.jsonl` 中无 `gpu_batch` 事件；heartbeat 明确记 `gpu_ran=false`、`path=HEARTBEAT_ONLY`。
- 对比：开市分支会打印 `[gpu_batch] device=NVIDIA RTX A2000 Laptop GPU ...`（见证据 3）。

### 证据 3 — MARKET_OPEN 分支（注入 `market_open=True`，隔离自测）

因是周末，未等真实开市；用测试开关 `--market-open`（只旁路 health 标志，**不伪造数据**）驱动开市分支，并把输出重定向到隔离沙箱（`V2_PHASE2_ROOT=<temp>`）以免污染真实证据流：

```
=== sandbox closed (prime) ===
[build] MARKET_CLOSED heartbeat-only status=MARKET_CLOSED_ALREADY_RECORDED stream_rows=5820 gpu_ran=False analytics_ran=False
=== sandbox OPEN (--market-open) ===
[gpu_batch] device=NVIDIA RTX A2000 Laptop GPU per_strategy_gpu=2.046s pooled_bench gpu=0.113s cpu=7.260s speedup=64.28x peak=209MB combos=32
[analytics] stream=5820 outcomes=22144 strategies=17 replay=MATCH
[stability_check] status=PASS failed=[]
[build] status=OPTIMIZED_CONTINUOUS rows=0 outcome_rows=0 reopen=True replay=MATCH
```

`shadow/heartbeat.jsonl` 尾部（沙箱）出现**首次 closed→open 切换**记录：

```
status : MARKET_REOPEN_RECOVERY
confirm: {"data_time_continuity": {"continuous": true, ...},
          "no_error_across_closed_window": true,
          "pit_normal": true,
          "replay": "MATCH", "replay_pass": true,
          "order_send": 0}
随后:   status=MARKET_OPEN_RECORDED  path=FULL_PIPELINE  gpu_ran=true analytics_ran=true
```

- 全流水线确实执行（GPU 真跑：`speedup=64.28x`；analytics `replay=MATCH`；stability `PASS`）。
- `rows=0 / outcomes=0` 是**幂等**结果：沙箱复制的数据中 latest cycle 已被既有 SEED/REPLAY 覆盖，故无新增 —— 如实体现在诚实性上，非"没有执行"。
- 沙箱运行**未改动真实目录**：`V2_PHASE2_ROOT` 重定向后，真实 `PHASE2_LIVE_EVIDENCE/` 全文件哈希 `changed=[]`。

### 证据 4 — 无周期性报告 churn（连续两次闭市路径逐文件哈希对比）

对 `PHASE2_LIVE_EVIDENCE/` 下所有文件（除 append-only 的 `heartbeat.jsonl` / `run_log.jsonl` 与 `*.pyc`）做 SHA256 前后对比：

```
changed: []
added:   ['shadow\\market_state.json']
removed: []
```

→ **0 个未变报告被重写**；唯一"新增"是状态机文件（且其内容稳定，重复闭市不变）。这正是 C3 要消除的 churn。

### 证据 5 — 边界确认（V2 RUNNING / replay PASS / order_send=0 / 未动 scheduler）

```
stability_check status = PASS
boundary_order_api      = {"clean": true, "risk_flags": 0, "findings": []}   # 无 order_send/order_check/MetaTrader5
replay (production)     = MATCH        (v2_run_health.json)
replay (shadow)         = MATCH        (analytics / REPLAY_REPORT)
V2 run_status           = RUNNING      (unblocked=true)
shadow scheduler        = \OpenClaw\hermes-v2-shadow-evidence  只读查询 state=就绪, Next Run Time 原样
```

- Scheduler：全程只调用**只读** `schtasks /query`；未 `create`/`change`/`delete`/`/run`。任务名、Next Run Time 与 launcher（`build.py --live`）保持不变。
- `order_send = 0`：runner 静态边界扫描 0 命中（`gpu_batch.py`/`backfill.py`/`heartbeat.py` 等无 MT5 order API）。

---

## 4. 完整性

- 改动范围：**仅** `PHASE2_LIVE_EVIDENCE/`（`git show --name-only` 复核）。
- `SHA256SUMS.txt` 在所有文件冻结后由 `runner/make_manifest.py` **最后**生成并自校验。
- runner **不** `git commit`；提交由 parent 在本报告冻结后执行。
- 未动策略/参数/RiskGuard/成本/研究结论；未动 V2 Production；未动 V1/V3；未创建/修改 scheduler。
