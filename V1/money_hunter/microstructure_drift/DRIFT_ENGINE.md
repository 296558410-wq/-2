# DRIFT ENGINE — 微结构漂移观察环（v0，2026-09-07）
> 定位：MICROSTRUCTURE DRIFT → ECONOMIC RELEVANCE → CANDIDATE TRIGGER 自动观察环。
> 本环**不**直接产出交易候选，不启动实验，不购买数据。它把"等待前瞻数据"升级为"主动寻找市场状态变化"。
> 与宪章关系：不改 Constitution（按任务书 §9）；观察环进入现有每日/每周自主循环（§8 落地）。

## 1. 输入（只使用已存在数据）
| 源 | 路径 | 内容 | 角色 |
|---|---|---|---|
| FXTM 历史报价（同源同 feed） | `data/staging_fxtm/ticks_*.parquet`（2026-08-04..09-04, 24 日） | bid/ask 报价流 | 基准 seed 主层 |
| FXTM 前瞻报价（live） | `data/live_fxtm/ticks_*.parquet`（cron 15min 采集） | bid/ask 报价流 | 观察层（forward-only） |
| DUKA assembled（跨年参考） | `data/staging_duka/assembled/*.parquet` | bi5 报价（不同采样） | 参考层，不混入主基准阈值 |
| 实时会话快照 | `research/microstructure_memory/daily/*.json` | 采集器快照 | dashboard/交叉核对 |

纪律：所有漂移统计用同一函数（`metrics.py`）从 parquet 重算，不信任不同口径的中间文件；
口径跨层不一致时宁可不比（`baseline_seed.py` 与 `drift_engine.py` 共用同一 `metrics.py`）。

## 2. 计算层
- `metrics.py`：单日微结构指标。字段集：
  - **spread**：`median_spr_bps / p90_spr_bps / p99_spr_bps / spread_usd_median / spread_usd_p90`
  - **activity**：`n_ticks / n_minutes / arrival_per_min`（tick 到达率）
  - **quote burst**：`burst_min_p99_count`（分钟计数 p99 阈值）+ `burst_minutes`（超阈值分钟数）
  - **vol 状态**：`rv1m_bps`（分钟对数中价收益 std, bps）
  - **price jumps**：`n_jump_min`（分钟级 |Δlog mid|≥10bps 次数）、`max_min_move_bps`
  - **session 状态**：`by_session{Asia,London,Overlap,NY,Quiet}`（n / median_spr_bps / p99_spr_bps，UTC 切分）
- `baseline_seed.py`：一次性/手动重跑。把 staging_fxtm（24 日）压成 `baseline_seed/fxtm_daily.json`，
  DUKA 压成 `duka_daily.json`（参考），再写 `BASELINE.yaml` 三窗口基准。
- `drift_engine.py`：每轮运行。重算滚动基准 → 比较当前 vs 基准 → 判定 → 写日志/状态/候选文件。

## 3. 基准（BASELINE）
滚动三窗口（全部已观测日，排除"当前观察窗"避免循环比较）：
- **short_7d**：最近 7 个有数据日
- **medium_21d**：最近 21 日
- **long_all**：全部
每字段每窗口存 n / mean / std / median / p90 / p99。
主层 = fxtm（与 live 同 feed 同定义）；DUKA 单独标注为参考层，**不**进主阈值（采样不同，混合会制造伪漂移）。

## 4. 判定（observation only）
- 当前状态 = 最近 ≤3 个 live 日均值（`cur_dates`）。
- 比较对象 = 排除当前窗后的 short/medium/long 基准（避免"当前 vs 自己"）。
- 漂移定义（与既有 drift_detect 阈值一致）：`|z| >= 3 且 |rel| >= 15%`。
- WARMUP：live 日 < 3（`WARMUP_NO_LIVE_DAYS` / `WARMUP_LOW_N`）→ 正常，不打扰。
- 跨 session 稳定性：5 个 session 的 median spread 相对中期基准同向比例（agree_pos / stable）。
- 输出：`BASELINE.yaml`（每轮重写）、`DRIFT_LOG.yaml`（append，cap 500）、`drift_state.json`。

## 5. 经济相关性门（ECONOMIC RELEVANCE GATE）
任何统计漂移必须映射到五个通道之一才可能被研究：
`PROBABILITY / PAYOFF / COST / EXECUTION / OPPORTUNITY_FREQUENCY`
通道映射见 `ECONOMIC_RELEVANCE_RULES.md`（字段→通道表与 engine 内 `ECON_CHANNELS` 同步）。
**规则：统计漂移本身只是 INFORMATION。只有 information → P/Payoff/Cost 变化 → 净 EV 成立的链条才进入 MONEY 层。**
第一阶段：发现漂移 → 记录（DRIFT_LOG）→ 周评审按经济门裁决 → 满足升级判据才进 CANDIDATE_TRIGGER.yaml（观察级），
不自动预注册、不自动实验。

## 6. 候选升级判据（对应任务书 §六）
某微结构变化需同时满足：
1. 历史中重复出现（≥2 个独立观察窗/时段命中）
2. 不是单一 regime（跨波动/跨 spread 状态）
3. 不是单一 session（跨 session 同向，sess_stability）
4. 不是单一时期（时间上分离出现）
5. 对未来变量有稳定影响（前瞻关联，如 activity→future vol 可测）
6. 有潜在经济意义（过 §5 经济门，至少一个通道 + 幅度足以改变净 EV 结构）
→ 才标 `UNPROVEN MECHANISM`，进入正式预注册研究队列（由周评审执行，人工/周会裁决；engine 只打标）。

## 7. 明确不做什么（红线）
- 不把统计漂移自动变成交易策略（本环无任何策略逻辑）。
- 不购买数据；signed flow 缺口不伪装（不用 volume 当 signed flow）。
- 不改 Constitution；不写 registry 冻结物；不碰交易 API。
- MT5 终端未开 / live 无新 tick → 正常空跑，不报错不打扰（沿用宪章）。

## 8. 与现有循环的接线
- `money-hunter-daily-cycle`（cron，每日）：新增一步——跑 `drift_engine.py`，仅 material 才上报。
- `money-hunter-weekly-review`（cron，每周）：step-0 确定性漂移探测改为跑 `drift_engine.py`
  （替代/叠加既有 drift_detect.py；drift_detect 保留作 dashboard 兼容）。
- 升级动作（CANDIDATE_TRIGGER 落库 → 预注册队列）只发生在周评审且过经济门时。

## 9. 执行反馈（长期解锁模块，任务书 §七）
定义（见 DATA_GAPS.md）：若未来获得免费 MT5 Demo 并设 `DEMO_MT5_*` env →
`research/self_collect/demo_exec_instrument.py` 自动接入，产出
`request_time / quote_time / fill_time / requested_price / filled_price / spread / slippage / reject / latency`。
**红线：绝不触真实账户交易 API，不自动下单，不花钱。**
v0 状态：代码就绪（demo_exec_instrument.py），等待免费 demo 注册（待用户一次性动作）。
