# V1 Truth System 最终状态（V1_TRUTH_SYSTEM_FINAL）

- 版本：`v1-truth-1` · 生成：2026-10-02 · 边界：只增不覆盖、`order_send=0`、不改策略/阈值/历史账本、V1/V2/V3 隔离。
- 运行时库：`v1_upgrade/truth/{truth_lib.py, v1_forensic.py}`；证据：`v1_upgrade/truth/evidence/`。

## 1. 验收

```text
TRUTH_CHAIN          = PASS   # 十段链全部可从证据还原（新事件用 cycle_id/decision_id；旧事件标注 time_adjacency）
ID_CORRELATION       = PASS   # event/cycle/decision/order/trade/incident/dedup 七类 ID 确定性、可互查
IMMUTABLE_EVIDENCE   = PASS   # 账本+snapshots+incidents 只增；逐行 sha256+prev；文件级 SHA256 登记
DECISION_SNAPSHOT    = PASS   # 27+ 字段；执行前写；写失败 ⇒ WAIT_TRUTH（不进新仓）
INCIDENT_SYSTEM      = PASS   # 13 类自动检测；真实+合成夹具均入库；状态可演进（最新态生效）
DAILY_TRUTH          = PASS   # FACTS_ONLY 报告（今日 net=-25.41, cycles=19）
CONSISTENCY_CHECK    = PASS   # 每周期 10 项检查（包裹 try/except，不影响交易决策）
FORENSIC_CLI         = PASS   # --trade/--incident/--cycle/--date/--incidents/--index 全部实测
REPLAY_LINK          = PASS   # Case derived 与账本/券商逐笔对照（consistent=True）
HISTORICAL_INTEGRITY = PASS   # 未改写历史；缺失一律 UNKNOWN，绝不补造
REGRESSION           = PASS   # 16/16 TRUTH_SYSTEM_REGRESSION_PASS（+ 既有 14/14、12/12 无回归）
order_send           = 0
```

**演示**：① trade `V1T-2378322488` 全链（decision→risk→order→fill→close→PnL→ledger→replay，逐笔对平）；
② 三类异常均自动生成 Incident 并可 CLI 还原：风控阻断（真实 RISK_BLOCK×3）、broker/ledger 不一致（合成夹具，已标注）、restart/schedule gap（真实 30min 缺口）。

## 2. 十个问题（结论）

1. **是否“发生任何事情都能查”？** —— 对**启用后**的新事件：是（ID 全链+快照+incident+CLI）。对**历史**：部分（事件在，但缺 cycle_id/decision_id 与快照，链路由时间相邻补齐并标注）。
2. **哪些事实 100% 可从原始证据还原？** —— 账本事件（链/序号/内容）、成交价/平仓价/PnL 分量/佣金/swap（券商 deal）、风控输入与拒绝理由（DECISION 字段）、执行指纹（滑点/延迟/retcode）、完整性（哈希）。
3. **仍存 UNKNOWN？** —— ①历史事件无 cycle/decision/dedup 标记（time_adjacency 标注）；②启用前无 decision snapshot（当时系统看到的完整上下文不可复原）；③broker_facts 为最新态缓存（非追加）；④早期 broker response 细节（如 order_check 完整 probe 语义）仅以账本记录为准；⑤合成夹具不构成真实事件。
4. **任意一笔能否一键 Case？** —— 能（`--trade`；十段链+raw+derived，实测）。
5. **任意一次异常能否一键 Incident？** —— 能（`--incident`；含真实与合成）。
6. **Ledger/MT5/Replay 是否互证？** —— 是：链 True、逐笔一致、replay 确定；差异只剩“成本口径”已注明。
7. **Truth System 是否影响交易安全？** —— 不改变 signal、不绕过 RiskGuard、不导致重复下单；唯一耦合是**记录失败→不进新仓**（fail-closed，符合任务 §16）。
8. **可迁移护城河？** —— V1_TRUTH_SCHEMA / EVENT_REGISTRY / EVIDENCE_REGISTRY / INCIDENT_KNOWLEDGE_BASE / TRADE_CASES / EXECUTION_FINGERPRINT / REPLAY_PROTOCOL / FORENSIC_CLI / TRUTH_REGRESSION（全部与策略解耦）。
9. **V2/V3 如何复用？** —— 同协议：只要它们的周期写出 `cycle_id/decision_id` 并在决策前落 snapshot，即可直接复用本 registry 与 CLI（V2 已有 ledger/事件体系，需加同款 ID 与 snapshot）。
10. **Git commit + SHA256** —— 见 `SHA256SUMS.txt` 与提交信息（本次追加）。

## 3. 边界与限制（诚实声明）

- 本次**未**发送任何订单；未改历史账本；未删除任何既有审计/知识资产。
- 未覆盖：**外部 watchdog**（进程死时无自报，属运维项）；旧交易的完整“当时上下文”。
- 任何“日志更多 ≠ 完成”——可查性以本文件 §1 的 12 项闸门为准。
