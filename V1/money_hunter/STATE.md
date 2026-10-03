# MONEY HUNTER STATE — 运行状态与前沿（2026-09-06 安装; 2026-09-07 增补）
## 当前前沿(单句)
已测空间(2011-2026 全尺度, 20+ 机制族) = NO MONEY; 剩余路径: 前瞻 live 数据积累(S-08) / demo 执行实测(S-09: 2026-09-07 FXTM demo 已注册并实测 20/20 fills(FOK); 2026-09-13 周评审经济门裁决=NO_CHANGE, 维持 EXECUTION_GATE) / GC 数据门(S-07, 待批准); 新增: 微结构漂移观察环(2026-09-07, 只观察不研究, 见 research/money_hunter/microstructure_drift/); **新增: 交易系统 V1 架构总设计(2026-09-07, 见 architecture/v1_trading_system/; FXTM=EXECUTION DATA GAP 已核验; P0 入口)**。
## 活跃管道
- cron mt5-live-tick-collect: 每 15 分钟静默采集(live_fxtm + microstructure daily 快照); 2026-09-07 修复假运行后已产出并验证(首真实交易日 76k+ ticks, commit e4e074c)
- 本宪章新增: 每日 cycle + 每周 review(cron, 静默; 仅 material 才报)
- 【2026-09-07 新增】每日 cycle 跑 drift_engine.py（微结构漂移观察环）; 每周 review 跑 drift_engine + drift_detect + 经济门裁决(ECONOMIC_RELEVANCE_RULES.md) → CANDIDATE_TRIGGER.yaml 观察级登记
- 【2026-09-07 DoD】完成定义入宪章: 先真跑后宣布/产出断言/24h checkpoint/证据确认根因
## 24h CHECKPOINT（DoD §3 落实; 采集修复后首个交易日 = 2026-09-07）
- T0 (09-07 18:xx GMT+8): 首真实交易日已端到端确认: ticks_20260907.parquet 存在且 76k+ 行, 时间戳 UTC 无未来戳, 增量 run 正常追加, json 快照与文件行数一致 ✓
- T+24h (09-08): 需确认第 2 个交易日的日增正常(新 parquet 出现且行数量级一致)后才信任整个 14 天基线周期; 若异常按 E 类上报
## 周评审（2026-09-13, 首次; 静默）
- drift_engine status=OK live_days=5(min 3) findings=0, sess_stability 5/5 stable=true → NO_DRIFT; legacy drift_detect WARMUP 5/14; 经济门 §2b findings=0 → 无需逐条裁决
- live 采集 5 完整交易日(09-07..09-11); 周末 NO_NEW_TICKS 正常; 无新提交/新候选(CANDIDATE_TRIGGER triggers=[])
- ONE BEST NEXT RESEARCH ACTION = S-09 经济门裁决 → verdict=NO_CHANGE(实测成本 spread≈0.3bps + 滑点 0.7~0.96bps ≥ 已知净提取上界 ≈0.1bps/笔 → 不产生新净 EV; 维持 S-04 KILLED / S-09 EXECUTION_GATE)
- 无 material → 静默 (NO_REPLY)

## 周评审（2026-09-20, 第 2 次; 静默）
- drift_engine status=OK live_days=10(min 3, seed 24d, duka 140d) findings=0, sess_stability 5/5 stable=true → NO_DRIFT; legacy drift_detect WARMUP 10/14 fields_checked=0; 经济门 §2b findings=0 → 无需逐条裁决
- live 采集 10 完整交易日(09-07..09-18), 最新 ticks_20260918.parquet 5.08MB/198,493 ticks; 周末休市 NO_NEW_TICKS 正常; 无新提交/新候选(CANDIDATE_TRIGGER triggers=[])
- ONE BEST NEXT RESEARCH ACTION = S-08 前瞻累积(冻结探测器 3-6 月后复跑) + 维持漂移观察环; 无 findings → 无新预注册检验(新检验必须先预注册 + rlap_audit)
- 无 material → 静默 (NO_REPLY)
- 产物: dashboard/heartbeat_weekly.json(更新) + cycle_history.jsonl(追加), commit 同步
## 周评审(2026-09-27, 第3次; 静默)
- drift_engine status=OK live_days=15(min 3, seed 24d, duka 140d) findings=0, sess_stability 5/5 stable=true → NO_DRIFT; legacy drift_detect 本周首次达标 status=OK days=15/14(min) fields_checked=10 findings=0; 经济门 §2b findings=0 → 无需逐条裁决
- live 采集 15 个完整交易日(09-07..09-25); 无新提交/新候选; CANDIDATE_TRIGGER triggers=[])
- ONE BEST NEXT RESEARCH ACTION = S-08 前瞻累积(冻结探测器 3-6 月后复跑) + 维持漂移观察环; 无 findings → 无新预注册检验(新检验必须先预注册 + rlap_audit)
- 无 material → 静默 (NO_REPLY)
- 产物: dashboard/heartbeat_weekly.json(更新) + cycle_history.jsonl(追加), commit 同步
## 待用户(免费/批准类, 非例行研究问题)
1. [已完成 2026-09-07 21:0x] FXTM MT5 demo 注册(.env.mt5_demo) + demo_exec_instrument.py 实测: 20/20 fills(FOK; IOC 10030 不支持→改 FOK), XAUUSD spread≈0.13-0.14USD(~0.3bps), 滑点±0.7bps, latency 0.33-0.98s(证据: microstructure_memory/exec/exec_20260907_130424/130520/130655.json, commit 1d21f8e)
2. [批准] Databento GC MDP3 $25 pilot → S-07 信息门终审(ACCESS LAB 方案已备)
## 纪律快照
- forward-only live 数据不回填假设; 新候选必经: 记忆检查→novelty→机制→预注册→IS→OOS→placebo/shuffle→FDR→成本→跨 regime→forward
- 判词: MONEY CANDIDATE 之前不称策略; NO MONEY 就说 NO MONEY
- 【2026-09-07】观察环纪律: 统计漂移≠赚钱候选; 只记录不研究, 升级须过经济门+六条判据(人工/周评审)
- 【2026-09-07】DoD: 任何"OK/运行中"声明前先验证真实产出(见 CONSTITUTION 完成定义小节)
## 下一动作队列(按优先级函数)
1. (自动) 保持采集与健康检查(每日 cycle, 含 drift_engine 观察环)
2. (数据到位后) 3-6 月; 截至 2026-09-27 已 15 个完整交易日: 冻结探测器在 forward 数据复跑
3. [已完成 2026-09-13 周评审] S-09 经济门裁决 = NO_CHANGE(实测成本≥净提取上界, 维持 EXECUTION_GATE; 不改判词)
4. (若批准) GC pilot 预注册+执行
5. [已完成 2026-09-20 周评审] 第 2 次周评审: drift findings=0 → NO_DRIFT, 无新候选/新提交, 静默 NO_REPLY
