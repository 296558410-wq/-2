# REPORT — 微结构漂移观察环 v0 交付（2026-09-07）
> 任务：把"等待前瞻数据"升级为"主动寻找市场状态变化"。
> 环：MICROSTRUCTURE DRIFT → ECONOMIC RELEVANCE → CANDIDATE TRIGGER（观察级，不产策略）。
> 裁定额外约束全部遵守：不开启毛量异常研究、不改 Constitution、不启动新正式 alpha 实验、不购买数据。

## 1. commit
`a34ce32`（repo C:\AIQuant, 本地 git 无 remote 禁 push）
`feat(money-hunter): 微结构漂移观察环 v0 — 审计定案落地 (DRIFT->ECON->CANDIDATE 观察环)`
含 microstructure_drift/ 全部文件 + STATE.md 增补。

## 2. 建立了什么
`research/money_hunter/microstructure_drift/`（7 份要求文件 + 3 个确定性脚本 + seed 缓存）：
| 文件 | 内容 |
|---|---|
| DRIFT_ENGINE.md | 观察环设计: 输入(已存在数据) / 计算 / 滚动基准 / 判定 / 经济门 / 升级判据 / 红线 / 接线 |
| metrics.py | 单日微结构指标(确定性): spread median/p90/p99(bps+usd), tick 到达率, quote burst, rv1m, 价格跳跃, session 状态; 与 live 采集同 UTC 会话切分 |
| baseline_seed.py | 历史基准种子: staging_fxtm 24 日 + DUKA 140 日 → BASELINE（只读已有 parquet） |
| drift_engine.py | 每轮: 重算滚动基准 → 当前 vs 基准 → z/rel 漂移 → 跨 session 稳定性 → 日志/状态 |
| BASELINE.yaml | 滚动基准(short_7d/medium_21d/long_all) × 全字段 × session; 主层=fxtm, DUKA=参考层不混阈值 |
| DRIFT_LOG.yaml | 观察日志(append, cap 500; 含每轮状态/发现/session 稳定性) |
| ECONOMIC_RELEVANCE_RULES.md | 经济相关性门: 5 通道(P/Payoff/Cost/Exec/OppFreq) + 字段映射 + INFORMATION vs MONEY 判定树 + 幅度标尺(1.7bps retail / 0.1bps 可提取上界) + 负面清单(proxy/闪烁/聚合谎言) |
| CANDIDATE_TRIGGER.yaml | 候选触发登记(观察级)。**当前空** |
| DATA_GAPS.md | signed flow = TOP 缺口; 执行反馈解锁模块(字段定义); 其他缺口登记(不重复考古) |
| baseline_seed/fxtm_daily.json + duka_daily.json | 逐日指标缓存(24 + 140 日) |

接线：`money-hunter-daily-cycle` cron 增跑 drift_engine.py（每轮改写 BASELINE + append DRIFT_LOG）;
`money-hunter-weekly-review` cron step-0 = drift_engine + drift_detect(兼容 dashboard), step-2b 新增经济门裁决
（通过→CANDIDATE_TRIGGER 观察级登记; 不通过→verdict=INFORMATION_ONLY）。判定无需 LLM（确定性），裁决归周评审。

## 3. 当前发现了什么漂移
**无漂移（WARMUP）**：live 前瞻日 = 0（`data/live_fxtm/` 尚无已收市完整日），观察环按设计安静积累。
基准期画像（fxtm 24 日, 2026-08-04..09-04, 供未来对比参考）：
- spread median ≈ 0.34 bps（usd ≈ 0.15），p90 ≈ 0.41 bps，p99 ≈ 0.52 bps —— 与 ACCESS LAB retail 1.7bps 往返、S7 全距 0.11bps 的历史证据一致
- session 分层（median bps）：Overlap 0.314 < NY 0.316 < London 0.33 < Quiet 0.36 < Asia 0.40
- DUKA 参考层 140 日（2023-09..2024-03 + 2026-08 前 4 日）已入库作跨年上下文

## 4. 哪些漂移被认为没有经济意义
尚无 live 日 → 无任何漂移裁决。规则已固化（ECONOMIC_RELEVANCE_RULES.md §3/§4）：
- 毛量/activity 类 = proxy → 默认 INFORMATION（NM-1 不升级，遵裁定）
- spread ≤0.2bps 且不持续 → 经济意义存疑; 单日单 session spread p99 尖峰(1-5s 闪烁) → 不可交易忽略
- 池化高但日内 t≈0 → 按 session 分层，禁止只报聚合（RQ-H1 K2 教训固化）
- rv/jump 单独出现 → 风险层信息（S-06 先例），无方向规则不算 MONEY

## 5. 有没有产生正式候选
**没有。** CANDIDATE_TRIGGER.yaml `triggers: []`。live_days=0，任何候选/UNPROVEN MECHANISM 都无从谈起。
观察环已进入自主循环（每日/每周 cron），积累足够前瞻日后自动开始比较。

## 6. signed flow 当前状态
**DATA GAP（维持 TOP1，未购买）**：FXTM feed 实测 volume≡0（staging 全 0），DUKA bi5=报价更新非 trades →
主动成交方向从未被直接观测。考古仅用现有数据；不用 volume 伪装。免费潜在解 = MT5 Demo（待用户一次性注册，同 S-09 动作）；
$25 Databento GC MDP3 属采购门(S-07, 待批)非免费。详见 DATA_GAPS.md。

## 7. 执行反馈当前状态
**模块已定义 + 代码就绪，等待免费 MT5 Demo**（不花钱、不触真实账户、不自动下单）：
- demo_exec_instrument.py 就绪 → 一旦 DEMO_MT5_* env 出现即接入，记录 request/quote/fill time、requested/filled price、spread、slippage、reject、latency → exec/*.json 供 RQ-07 校准
- 本环不阻塞：观察环与执行反馈解耦，前者现在就跑，后者等一次免费注册

## 8. 钱猎手下一步
1. **让观察环跑**（已接线 cron，静默）；每日/每周自动积累 live 日并比对滚动基准。
2. **继续等待真实前瞻数据**：live tick 采集当前 NO_NEW_TICKS（周开盘后 MT5 history 未回新 tick——
   已登记 DATA_GAPS 观察项，下一交易时段复核；若持续属采集器故障按宪章 E 类上报）。
3. 只有满足经济门槛（幅度标尺 + 持续性 + 事前可识别）且过 §六 六条判据的状态变化才升级 UNPROVEN MECHANISM
   → 预注册队列（仍非实验）。当前一切照旧：S-08 积累 / S-09 待注册 / S-07 待批。
4. 不开启新正式 alpha 实验。无 MONEY CANDIDATE 就继续安静观察；毛量异常保持 proxy 定位不升级。

## 纪律自检
- [x] 未改 Constitution; [x] 未开新实验; [x] 未买数据; [x] 未用 volume 伪装 signed flow;
- [x] 观察环确定性(无 LLM); [x] 已进入每日/每周自主循环; [x] 空候选 = 诚实记录
