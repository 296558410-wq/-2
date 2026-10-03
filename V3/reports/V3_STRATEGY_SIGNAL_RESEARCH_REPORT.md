# V3 策略 / Signal 研究与 Forward 前验收报告

`ts_utc = 2026-09-24T17:15:22.849338+00:00` · **`final_status = V3_STRATEGY_RESEARCH_COMPLETE`** · `V3_FORWARD_READY = False`

## 0. 方法纪律（先冻结，后看数据）

```text
假设 -> 定义 -> 冻结 -> 数据 -> 验证 -> 反证     （§5 要求的方向）
hypothesis registry 在【任何评估之前】写入并哈希：registry_hash = 1650e065911e72c93f85cf26d51cdb179f252b089eb4a2c86ad8be2c7682c52d
所有阈值均由机制推理先验给定；本报告不含任何参数搜索、不含"跑很多组合挑最好"。
```

## 1. 基线

```text
Git            : 本任务提交（见 §10）；execution 层 v3_adapter.py 未改动
Execution      : V3_EXECUTION_MODE=DEMO_CALIBRATION · ORDER_SEND=YES · LIVE=NO · FORWARD=NOT_ENABLED
Calibration    : 20/20 · HEDGE lifecycle PASS · MT5↔ledger 对账 PASS · ledger 链 PASS（均未被本任务触碰）
Account        : 160766418 · magic 90004 · XAUUSD · ForexTimeFXTM-Demo01
```

## 2. 数据（PIT / hash / coverage）

```text
源数量        : 14（全部 data/live_fxtm/*.parquet，FXTM 本所）
覆盖          : 2026-09-07 01:05:00.047000+00:00  ->  2026-09-24 17:09:06.840000+00:00
总行数        : 2821581
PIT 说明      : 每个文件登记 hash/mtime/coverage；bars 一律【从 tick 重建】，不复用预计算特征
排除（并在报告中声明）:
  data/staging_duka           不同交易所（DUKA），不可当作 FXTM 执行环境数据
  micro_m1_features / labels  预计算特征/标签，无法审计其构造 → 为避免隐性泄漏一律不用
样本文件 hash（前 2 条示例）:
[
 {
  "kind": "MARKET_DATA",
  "source": "FXTM XAUUSD L1 (live_fxtm)",
  "file": "data/live_fxtm/ticks_20260907.parquet",
  "rows": 166470,
  "coverage": {
   "from": "2026-09-07 01:05:00.047000+00:00",
   "to": "2026-09-08 01:16:44.368000+00:00"
  },
  "timezone": "UTC",
  "retrieval_time": "collected continuously (recorded mtime)",
  "mtime_utc": "2026-09-08T01:16:41.119303+00:00",
  "quality": "venue-consistent",
  "hash_sha256_of_first_64MB": "c1ec30d59bbd78e8bcaa1513857fefcc8917cffcbdd94a502803d63dfdf2c886",
  "PIT": "point-in-time (append-only daily parquet; ts_utc from venue)"
 },
 {
  "kind": "MARKET_DATA",
  "source": "FXTM XAUUSD L1 (live_fxtm)",
  "file": "data/live_fxtm/ticks_20260908.parquet",
  "rows": 203959,
  "coverage": {
   "from": "2026-09-08 01:15:44.158000+00:00",
   "to": "2026-09-09 01:09:07.344000+00:00"
  },
  "timezone": "UTC",
  "retrieval_time": "collected c
```

## 3. Hypothesis Registry（全部 12 条，冻结）

| ID | 假设 | 期望 horizon | 独立性 |
|---|---|---|---|
| H01_1M_SIGMA_FADE | 1-minute 2.5-sigma mid move partially reverts over the next 5 minutes | 5m | INDEPENDENT |
| H02_5M_RANGE_BREAKOUT | 1m close beyond the prior 20-bar range continues for 10 bars | 10m | INDEPENDENT |
| H03_LONDON_OPEN_MOMENTUM | the first bar after 07:00 UTC continues in its own direction for 6 bars | 6m | INDEPENDENT |
| H04_LOWVOL_SIGMA_FADE | the sigma-fade works better when realized vol is in its lower tercile | 5m | DERIVED (regime-conditioning |
| H05_SPREAD_SPIKE_FADE | when the 1m mean spread z-score exceeds 2 the contemporaneous mid move fades | 5m | INDEPENDENT |
| H06_EMA_TREND_PULLBACK | in an EMA20>EMA50 uptrend a pullback to EMA20 then resumption continues 8 bars | 8m | INDEPENDENT |
| H07_ROUND_LEVEL_REJECTION | a failed test of a round 10.00 level fades away from the level for 6 bars | 6m | INDEPENDENT |
| H08_SQUEEZE_BREAKOUT | after a bandwidth squeeze a breakout follows for 8 bars | 8m | INDEPENDENT |
| H09_ROLLOVER_REVERSAL | the prior 30-minute move fades around the 21:00-22:00 UTC rollover | 6m | INDEPENDENT |
| H10_DXY_CONFIRMED_REVERSAL | an FXTM move aligned with an opposite DXY move reverses | 6m | INDEPENDENT (cross-asset) |
| H11_TICKRATE_SPIKE_FADE | a tick-rate spike with a directional move fades 5 bars later | 5m | INDEPENDENT |
| H12_DAILY_GAP_FADE | an overnight gap from the prior session close partially fades at the open | 10m | INDEPENDENT |

> 独立性声明（§9）：全部为 **INDEPENDENT**；H04 标注 **DERIVED**（对 H01 机制做 regime 条件化，属独立检验）。
> **不存在 REUSED**：未复制 V1/V2 的 entry/exit/threshold/prompt/decision schema（已核对：策略层代码不含 V1/V2 逻辑引用）。

## 4. Signal（定义与契约）

```text
contract : strategy/contracts.py —— 覆盖 §13 全字段（run_id/signal_id/timestamp/symbol/signal_type/
           direction/confidence/regime/feature_snapshot_hash/context_hash/entry_reference/
           expected_horizon/invalid_condition/reason/strategy_version/signal_version/data_cutoff/execution_delay）
validate(): 强制 data_cutoff <= timestamp（lookahead → 直接抛错）；NO_TRADE 必须带合法原因
NO_TRADE : 一等结果（NO_EDGE/LOW_CONFIDENCE/BAD_LIQUIDITY/CONFLICTING_CONTEXT/HIGH_COST/DATA_INVALID/REGIME_UNCERTAIN/RISK_BLOCKED）
时序     : signal@close[t]  ->  execution@open[t+1]（§7；绝不同 bar 成交）
回放     : 11 个假设两次生成逐字节一致 = True
```

## 5. 实验（样本 / 成本压力 / 回撤 / OOS）

bars = **17937** 根 1m（2026-09-07 01:05:00+00:00 → 2026-09-24 17:09:00+00:00）；成本锚 = **0.914 bp 往返**

| ID | signals | eff n | gross bp/笔 | 0x | 1x | 2x | 3x | maxDD bp | PF | OOS 前半/后半 | 判定 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H01_1M_SIGMA_FADE | 391 | 324 | 0.499 | 0.499 | -0.415 | -1.329 | -2.243 | -289.47 | 0.909 | -0.986/0.153 | REJECT |
| H02_5M_RANGE_BREAKOUT | 2213 | 880 | -0.258 | -0.258 | -1.172 | -2.086 | -3.0 | -2684.67 | 0.774 | -0.979/-1.365 | REJECT |
| H03_LONDON_OPEN_MOMENTUM | 9 | 9 | -2.714 | -2.714 | -3.628 | -4.542 | -5.456 | -42.17 | 0.294 | -4.099/-3.25 | INSUFFICIENT_SAMPLE |
| H04_LOWVOL_SIGMA_FADE | 374 | 276 | 0.216 | 0.216 | -0.698 | -1.612 | -2.526 | -302.72 | 0.781 | -0.989/-0.407 | REJECT |
| H05_SPREAD_SPIKE_FADE | 818 | 295 | -0.126 | -0.126 | -1.04 | -1.954 | -2.868 | -920.7 | 0.738 | -1.054/-1.027 | REJECT |
| H06_EMA_TREND_PULLBACK | 2784 | 1091 | -0.07 | -0.07 | -0.984 | -1.898 | -2.812 | -2950.77 | 0.774 | -0.722/-1.246 | REJECT |
| H07_ROUND_LEVEL_REJECTION | 1255 | 702 | -0.05 | -0.05 | -0.964 | -1.878 | -2.792 | -1222.07 | 0.745 | -0.997/-0.93 | REJECT |
| H08_SQUEEZE_BREAKOUT | 427 | 260 | -0.004 | -0.004 | -0.918 | -1.832 | -2.746 | -565.46 | 0.776 | -0.506/-1.329 | REJECT |
| H09_ROLLOVER_REVERSAL | 1461 | 244 | -1.386 | -1.386 | -2.3 | -3.214 | -4.128 | -3627.94 | 0.539 | -2.807/-1.794 | REJECT |
| H10_DXY_CONFIRMED_REVERSAL | 0 | - | - | - | - | - | - | - | - | -/- | INSUFFICIENT_SAMPLE |
| H11_TICKRATE_SPIKE_FADE | 800 | 365 | -0.017 | -0.017 | -0.931 | -1.845 | -2.759 | -922.56 | 0.818 | -0.914/-0.948 | REJECT |
| H12_DAILY_GAP_FADE | 0 | - | - | - | - | - | - | - | - | -/- | INSUFFICIENT_SAMPLE |

（`eff n` = 重叠调整后的有效样本；`OOS 前半/后半` = 1x 成本下时间序两半的均值 bp）

## 6. 淘汰（明确分类）

```text
REJECT                 = 9   （1x 成本后均值<=0，或 2x 即转负 => 成本脆弱）
EDGE_UNCERTAIN         = 0
INSUFFICIENT_SAMPLE    = 3   （有效样本不足 / 数据缺口）
CANDIDATE              = 0
多元检验               : 测试 12 个假设 · 走到 FDR 阶段 0 个 ·
                         BH(q=0.05) 阳性 0 个
```

三个 INSUFFICIENT_SAMPLE 的具体原因：
```text
H03_LONDON_OPEN_MOMENTUM : 有效样本不足（07:00 整点 bar 在 tick 断档日缺失；eff n < 30）
H10_DXY_CONFIRMED_REVERSAL: DATA_REQUIRED —— 无带发布时间戳的 DXY PIT 序列登记（§17：不得用 period/label 冒充）
H12_DAILY_GAP_FADE       : 有效样本不足（隔夜跳空样本太少；eff n < 30）
```

## 7. Candidate

```text
CANDIDATE = []
=> 无候选进入 Shadow。这是结论，不是失败：在真实成本 + 分块 OOS + BH-FDR 三关下没有假设存活。
```

## 8. Shadow

```text
状态      : N/A（无 Candidate）
ORDER_SEND: 0   ·  与 Calibration 分账 : True
说明      : shadow ledger 刻意未创建（空账本会污染统计）；run_id 预留 = V3_STRATEGY_SHADOW_20260925
```

## 9. Forward Preflight

```text
strategy_hash  = 066cbb0985de55c23556dce38aad3ece…
config_hash    = 90b0dbd85cf72efc5b6c0027152feffd…
signal_hash    = d601a1aa9a51aad60e229b39cff9b553…
data_hash      = 00eff2d793ccd0c0d6fa19c1089dbf3b…
execution_hash = b207ce1903d1ca6b900000602d0ebc40…
account = 160766418 · magic = 90004 · symbol = XAUUSD
V3_LIVE_ALLOWED = NO
V3_FORWARD_READY = False   (§34：仅 Candidate 达标才为 TRUE)
V3_STRATEGY_FORWARD = NOT_ENABLED   (§35/§46：绝不自动开启)
```

## 10. 最终状态

```text
V3_STRATEGY_RESEARCH_COMPLETE
V3_FORWARD_READY     = False
V3_STRATEGY_FORWARD  = NOT_ENABLED
```

## §45 最终安全闸门

| gate | 结果 | 说明 |
|---|---|---|
| V3_CODE_INTEGRITY | PASS | trader_v3 code diff 限本任务授权范围（strategy/* + config + state） |
| V3_EXECUTION_INTEGRITY | PASS | v3_adapter.py 本任务未改动（execution 层冻结，§38） |
| V3_ACCOUNT_ISOLATION | PASS | 160766418 / magic 90004 / 无 V1(160759434) 或 V2(160761384) 引用 |
| V3_DATA_LINEAGE | PASS | 14 个 live_fxtm 文件登记 + sha256 + PIT |
| V3_NO_LOOKAHEAD | PASS | Signal.data_cutoff <= timestamp 强制校验；特征全部 trailing window |
| V3_NO_SAME_BAR_CHEAT | PASS | 执行价 = t+1 bar open；绝不用信号 bar 自身 close 成交 |
| V3_CALIBRATION_ISOLATION | PASS | calibration ledger/state 未被本任务改动；calibration P&L -6.98 未进入策略 P&L |
| V3_STRATEGY_CONTRACT | PASS | strategy/contracts.py 覆盖 §13 全字段 + validate() |
| V3_SIGNAL_REPLAY | PASS | 11 个假设两次生成逐字节一致 |
| V3_HYPOTHESIS_REGISTRY | PASS | 12 条冻结，registry_hash=1650e065911e72c9（评估前冻结） |
| V3_COST_MODEL | PASS | 锚 0.914bp 往返，压力 0/1/2/3x 全跑 |
| V3_OOS_VALIDATION | PASS | 时间序前后半区（blocked，无 shuffle） |
| V3_REGIME_TEST | PASS | 波动三分位 + 四个 session 分层的净收益 |
| V3_MULTIPLE_TESTING_CONTROL | PASS | 记录 12 个测试，BH q=0.05 |
| V3_SHADOW_LEDGER | N/A | 无 Candidate → §32 shadow 不适用；shadow ledger 刻意未创建（避免空账本） |
| V3_FORWARD_PREFLIGHT | PASS | 五哈希 + account/magic/symbol + LIVE=NO 全部记录 |
| V3_LIVE_DISABLED | PASS | V3_LIVE_ALLOWED=NO |

## §49 验收标准

| 标准 | 结果 |
|---|---|
| V3_EXECUTION_PRESERVED | YES |
| V3_CALIBRATION_PRESERVED | YES |
| V3_STRATEGY_LAYER_CREATED | YES |
| V3_SIGNAL_CONTRACT_CREATED | YES |
| V3_DATA_LINEAGE_VERIFIED | YES |
| V3_NO_LOOKAHEAD | YES |
| V3_NO_SAME_BAR_CHEAT | YES |
| V3_HYPOTHESES_FROZEN | YES |
| V3_COST_STRESS_COMPLETED | YES |
| V3_OOS_COMPLETED | YES |
| V3_REGIME_TEST_COMPLETED | YES |
| V3_MULTIPLE_TESTING_RECORDED | YES |
| V3_SHADOW_COMPLETED | N/A (no candidate) |
| V3_CALIBRATION_SEPARATED | YES |
| V3_FORWARD_PREFLIGHT_COMPLETED | YES |
| V3_LIVE_DISABLED | YES |
| V3_FORWARD_NOT_AUTO_STARTED | YES |
| V3_REPORT_CREATED | YES |
| V3_GIT_COMMITTED | YES |

## 结论（诚实口径）

```text
本任务建立并跑通了 V3 的【策略/Signal 研究层】：契约、数据登记、冻结假设、确定性信号、
成本压力、分块 OOS、状态分层、多重检验控制、Forward 预检。
结论是【没有候选存活】—— V3 尚未展示出可重复、可验证、成本后仍存在的交易机会。
这不是"策略失效"，也不是"alpha 已证"：它只是第一次诚实的第一轮筛选结果。

Execution = 已验证 · Calibration = 已完成 · Strategy/Signal = 已建立并完成第一轮筛选
Shadow = 无对象 · Forward = 未开启 · Live = 永远不是本任务目标
```
