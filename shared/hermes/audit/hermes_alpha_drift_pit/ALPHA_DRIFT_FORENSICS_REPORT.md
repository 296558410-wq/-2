# V1/V2 Hermes Alpha Drift & PIT Forensics — 报告
## ALPHA_DRIFT_FORENSICS_REPORT

- **任务**：调查“为什么旧 V1、新 V1、V2 都曾出现‘上线初期盈利、随后衰减/亏损’”，并判定是否来自真实 Alpha / 市场状态 / 数据·PIT / Hermes 输入或行为 / 执行环境 / 研究设计偏差。
- **硬边界遵守**：只读；`order_send=0`；未改 V1/V2/V3 策略/参数/Prompt/RiskGuard/账本/成交/冻结协议；V1/V2/V3 隔离；不用未来数据解释过去决策；**允许结论为“不存在稳定 Alpha”**。
- **终态**：**`ALPHA_EVIDENCE_INSUFFICIENT`**（当前证据不足以支持继续进行 Alpha 优化；不提出新策略）。
- **证据等级**：`FACT` = 原始记录直读；`DERIVED` = 派生计算；`INTERPRETATION` = 明示推断；`UNKNOWN` = 证据不足。

---

## 0. 目录与方法

- **产物**（本目录）：`ALPHA_DRIFT_FORENSICS_REPORT.md` · `V1_HERMES_TRADE_DATABASE.jsonl`(142) · `V2_HERMES_TRADE_DATABASE.jsonl`(1666) · `CROSS_SYSTEM_COMPARISON.csv` · `PIT_AUDIT.json` · `RESTART_DIFF.md` · `REPLAY_RESULTS.jsonl` · `ROOT_CAUSE_MATRIX.md` · `DATA_GAPS_AND_UNKNOWN.md` · `SHA256SUMS.txt` · 脚本 `build_v1_db.py` / `build_v2_db.py` / `analyze.py`。
- **数据源（只读）**：券商 MT5 demo deals（按 magic 90002/90011 分系统）；`trader_v1/run_state/*`（旧 V1）；`trader_v1/v1_upgrade/{ledger,truth/evidence}`（新 V1）；`trader_v2/state/*` + `trader_v2/research/*`（V2）；既有审计 `v1_audit/` 与 `v1_loss_forensics/`（作为可追溯证据引用，关键数字已用券商事实复核）。
- **仪器修正（先查仪器）**：
  1. 证据库 `version` 是**全局抓取序号**（非逐条修订）；真正的修订 = 带 `previous_content_sha256` 的行（73,315 个 id）。
  2. 新 V1 ledger `replay_match` **恒为 null**（从未落值）⇒ 不得当作重放证据引用。
  3. 旧 V1 09-17 快照日报只到 12:51Z（`v1_audit` 记 09-17=−52.09）；券商全量同一日 = **−76.01** ⇒ 以券商事实为准。

---

## 1. 三个系统分别“实际是什么”（控制策略 vs Hermes Alpha 严格分离）

| 系统 | 实际决策层 | 是否 Hermes Alpha | 交易 |
|---|---|---|---|
| **旧 V1**（magic 90002） | Hermes **LLM 计划引擎**（决策含 `model`/`confidence`/`answers_14`/`mtf_agreement`） | **候选**（但早期输入不可复原，无法认证） | DEMO，109 笔已平 |
| **新 V1**（magic 90011） | **`BASELINE_CONTROL` 控制臂**（`signal_type=BASELINE_CONTROL`、`not_hermes_alpha=true`，机械映射） | **不是**（控制策略） | DEMO，32 笔已平 |
| **V2**（PAPER） | **`reference_rules` 占位参照器**（`signal_from_agents=false`；docstring 注明生产应为 LLM 编排） | **不是** | PAPER，**0 笔真实成交** |

> **关键事实**：三个系统里，**只有旧 V1 曾运行真正的 Hermes LLM 决策层**；新 V1 是控制臂、V2 是占位参照器。因此“三个 Hermes 都先盈后亏”的表述**在系统身份上就不成立**——其中两个并非 Hermes Alpha 在交易。

---

## 2. 四核心对照

### 对照 1：前期盈利 vs 后期亏损
窗口在取数**之前**由首/末成交时间确定，不事后挑选。

| 系统 | 窗口 | 前期（盈利） | 后期（衰减） | 合计 | 胜率 |
|---|---|---|---|---|---|
| **旧 V1** | 09-07→09-28 | 09-08..09-14 **+126.49 价差 / +116.57 净额**（47 笔） | 09-15..09-28 **−146.92 / −159.49**（62 笔） | −20.43 / −42.92 | 0.450 |
| **新 V1** | 09-28→10-02 | 09-28..09-29 **+21.89 / +20.49**（7 笔） | 09-30..10-02 **−33.33 / −38.35**（25 笔） | −11.44 / −17.86 | 0.375 |
| **V2** | 09-11→10-02 | n/a | n/a | **0（无成交）** | n/a |

- **旧 V1**：日级路径清楚 —— 09-08 +58.1、09-09 −50.3、09-10 +45.8、09-11 +39.8、09-14 +33.7，累计 **+127.2**；随后 09-15 起转负（09-17 −76.0、09-25 −43.1）。**“先盈后亏”= `CONFIRMED`（日级，两口径均成立）。**（`DERIVED`，源=券商 deal）
- **新 V1**：前 7 笔 +21.89 → 后 25 笔 −33.33。**`PRESENT`（幅度小、仅约 2 天）。**（`DERIVED`）
- **V2**：**`NOT_EVALUABLE`** —— `paper_executions` 仅 6 条 smoke/合成记录，`paper_account.realized_pnl=0.0`。**V2 从未产生可评估的成交序列。**（`FACT`）
- **输入→输出→市场→结果 是否变化**：
  - 旧 V1：**市场未变**（spread p50 0.319→0.349bp、波动/活跃同量级）、**入场方向未恶化**（近期 +1s 胜率 .714 > 整体 .617）⇒ **结果变了，但输入与市场没变** ⇒ 指向小样本/个体大逆行与退出管理，而非信号衰减。（`DERIVED`，源自 v1_audit 复核）
  - 新 V1：输入（控制臂）恒定；结果变化中 **6 笔可归因于风控接线缺陷**（见对照 3/`RISK_SYSTEM_EFFECT`），其余 14 笔为市场实现。
  - V2：无输出可评。

> **不写因果**：“先盈后亏”是**描述性 P&L 形状**，不是已证因果。

### 对照 2：重启前 vs 重启后
详见 `RESTART_DIFF.md`。要点：
- 新 V1：重启 `2026-10-01T13:52:15Z`（漏 1 拍 14:03Z，14:18Z 恢复）；决策层全窗恒定；truth 快照全在重启后 ⇒ 逐字段对照 `DATA_GAP`；**`NO_EVIDENCE_OF_RESTART_CAUSALITY`**（重启前后正确语义状态相同、无持仓、无状态可失）。
- 旧 V1：重启（09-09 / 09-14）前后**输入不可复原** ⇒ `UNKNOWN`。
- V2：重启改变的是**行情源可达性**（MT5↔执行武装耦合 → fallback），非决策行为；0 成交 ⇒ 无 P&L 因果。

### 对照 3：V1 vs V2（找共同**设计模式**，不比较表面策略名）
- **共同模式 A —— “非 Alpha 的决策层顶着 Hermes 之名”**：新 V1 控制臂、V2 参照器占位器；V2 另有**结构性机会单一化**（`opp_geo_shock` **148/148 周期 = 100%**，7 成周期仅 1 个候选，90.1% 决策因“需确认”而 WAIT）⇒ **150 决策→148 WAIT、0 成交**。这不是策略在挑选，而是恒定新闻型机会反复撞上“需确认”门。（`FACT`，源自 V2 机会退化诊断）
- **共同模式 B —— 无 PIT 完整输入留痕**：V1 早期输入轮转、V2 `point_in_time_valid=unknown` 100%。
- **共同模式 C —— 小样本 + 事后窗口**：两系统都只有数日/数十笔。
⇒ 共同的不是“Alpha 衰减”，而是**研究/设计偏差**。

### 对照 4：PIT / Lookahead（逐字段）
详见 `PIT_AUDIT.json`。

| 字段组 | 规则 | 状态 |
|---|---|---|
| V2 新闻证据 `published_at`/`retrieved_at` | availability ≤ decision_time | **PASS 无泄漏**（16,922 引用：0 条 retrieved>decision、0 条 published>decision）|
| V2 K 线 | 无未收盘/未来 bar | **PASS**（`PIT_VALIDATION_REPORT.md`：5m/15m/60m/4h/1d 未收盘 bar=0，单调）|
| V2 宏观 `release_timestamp`/vintage | 发布时点+版本 | **FAIL_UNKNOWN**（878/878 `release_timestamp_unknown`，置信=low，38 行改动）|
| V2 证据库 PIT 标志 | `point_in_time_valid` | **UNKNOWN**（75,394/75,394 = unknown）|
| V2 证据**内容版本** | 决策时刻内容可复原 | **PARTIAL/不可认证**（73,315 id 带 `previous_content_sha256`，旧内容被覆盖；仅 31 保留 >1 版本）|
| 新 V1 决策快照 | 每决策 `PIT_status` | **PASS**（34/34 `PIT_OK`）|
| 旧 V1 决策 | availability ≤ decision_time | **UNKNOWN**（早期输入轮转）|

**“最终修订值回填历史”检查**：**未观察到可证的 availability-time 泄漏**；但对 **73,315** 条被覆盖的证据，**决策时刻的内容版本不可复原**，宏观修订亦不可证 ⇒ **不能认证“无回填”**（`NOT_PROVEN`，非“已证无泄漏”）。

---

## 3. 逐笔/逐决策覆盖

- **V1**：`V1_HERMES_TRADE_DATABASE.jsonl` = 142 行（旧 109 已平 + 1 未平 + 新 32 已平），**覆盖券商全部 magic 90002/90011 roundtrip**（券商侧 109/110、32/32）。
- **V2**：`V2_HERMES_TRADE_DATABASE.jsonl` = 1,666 行（全部决策；`WAIT 1439 / TRADE 166 / REJECT 61`），另 2,806 条机会记录；**成交 0**。
- **控制策略与 Hermes Alpha 分离 = 100%**：新 V1=控制臂、V2=参照器，均非 Hermes Alpha；旧 V1 为唯一 Hermes LLM 候选但输入不可 PIT 认证。

---

## 4. 根因判定（详见 `ROOT_CAUSE_MATRIX.md`）

- `TRUE_ALPHA_DRIFT`：**NOT_SUPPORTED** · `MARKET_REGIME_CHANGE`：**NOT_SUPPORTED** · `HERMES_BEHAVIOR_CHANGE`：**NOT_SUPPORTED**
- `RISK_SYSTEM_EFFECT`：**CONFIRMED（仅新 V1，6 笔可预防）** · `DATA_PIPELINE_CHANGE` / `EXECUTION_CHANGE`：**PARTIAL（非因果）**
- `PIT_LOOKAHEAD`：**NOT_PROVEN（不可认证）** · `HERMES_INPUT_CHANGE`：**UNKNOWN**
- `RESEARCH_SELECTION_BIAS` + `COMMON_DESIGN_BIAS`：**CONTRIBUTING**
- `NO_IDENTIFIABLE_CAUSE`：**判定（P&L 路径本身）** · 余下 **`UNKNOWN`**

---

## 5. 最终必须回答

**Q1｜三系统是否真存在共同的“前期盈利→后期衰减”？**
→ **否（非共同/非普遍）**。旧 V1 `CONFIRMED`（日级、两口径）；新 V1 `PRESENT`（小、约 2 天）；**V2 `NOT_EVALUABLE`（0 成交）**。2/3 出现，1/3 无数据 ⇒ 不构成“三系统共同现象”。（`FACT`+`DERIVED`）

**Q2｜若存在，是否存在共同根因？**
→ **无共享的 Alpha 漂移根因**。可共享的是**研究/设计偏差**：`RESEARCH_SELECTION_BIAS`（事后选窗+小样本）+ `COMMON_DESIGN_BIAS`（非 Alpha 决策层冠以 Hermes 之名、无 PIT 输入留痕）。系统特定因素：新 V1 风控接线缺陷、V2 机会供给结构性坍缩。⇒ 判定 `MULTI_FACTOR`，非单一共同根因。

**Q3｜早期盈利是否具有 PIT 完整、可验证、可复现的预测证据？**
→ **否**。旧 V1 早期输入轮转（`UNKNOWN`）、V2 `point_in_time_valid` 100% unknown、新 V1 是控制臂（非预测）。**无任何系统提供 PIT 完整、可验证、可复现的“早期盈利=预测能力”证据。**（`FACT`）

**Q4｜后期亏损是否伴随输入、数据、市场状态或 Hermes 行为变化？**
→ **否（无一致证据）**。市场状态未变（旧 V1 审计）、决策层恒定（新 V1 控制臂、V2 参照器）、输入不可复原（旧 V1）。唯一被证实的“变化”是新 V1 的**风控接线修复**（属风控，且发生在亏损之后，不解释亏损方向）与 V2 的**行情源可达性**（无成交）。（`DERIVED`）

**Q5｜重启是否真正改变了 Hermes 决策行为？**
→ **无证据改变**。新 V1 `NO_EVIDENCE_OF_RESTART_CAUSALITY`；旧 V1 `UNKNOWN`；V2 变的是管道可达性、非决策行为。（`DERIVED`）

**Q6｜哪些结果属于真正 Hermes Alpha，哪些属于控制策略/执行/风险/其他？**
→ **真正 Hermes Alpha（具备可验证证据）= 0**。新 V1 全部 = **控制策略**；V2 全部 = **参照器占位器（0 成交）**；旧 V1 = 唯一 Hermes LLM 候选，但其结果**无法与 Alpha 分离地认证**（输入不可 PIT 复核、成本口径 `DATA_GAP`）。控制/执行/风险归属：新 V1 有 **6 笔风控缺陷可预防亏损**，其余为市场实现。

**Q7｜当前证据是否足以支持继续进行 Alpha 优化？**
→ **不足**。终态 **`ALPHA_EVIDENCE_INSUFFICIENT`**。**不提出新策略、不调参、不改 Prompt、不启动新交易、不进入下一轮 Alpha Research。**

---

## 6. 验收自检

| 验收项 | 结果 | 依据 |
|---|---|---|
| 可获得 Hermes 交易/决策完整覆盖 | **PASS** | V1 覆盖券商全部 90002/90011 roundtrip；V2 覆盖全部 1666 决策 |
| 控制策略与 Hermes Alpha 100% 分离 | **PASS** | §1/§3（新 V1 控制臂、V2 参照器、旧 V1 候选不可认证） |
| PIT/lookahead 审计完成 | **PASS（含不可认证项）** | `PIT_AUDIT.json`（泄漏 0；内容版本/宏观 `UNKNOWN`） |
| 重启前后差异完成 | **PASS** | `RESTART_DIFF.md`（含 `DATA_GAP`/`UNKNOWN`） |
| 同输入 replay（可做范围内） | **PASS（如实分级）** | `REPLAY_RESULTS.jsonl`：V1_NEW=INPUT_HASH_ONLY、V2=PARTIAL、V1_OLD=NOT_POSSIBLE |
| 结论可追溯至原始证据 | **PASS** | 每条注明源与等级 |
| UNKNOWN 保留 | **PASS** | `DATA_GAPS_AND_UNKNOWN.md` |
| Git commit + SHA256 | **PASS** | `SHA256SUMS.txt` + §7 |
| 工作区干净 / `order_send=0` / V1/V2/V3 隔离 | **PASS** | 本目录脚本 order 调用=0；仅读 V1/V2 路径 |

---

## 7. 证据与指纹
- 券商全量 deals：magic 90001(82, test) · **90002(219, 旧 V1)** · **90011(64, 新 V1)** · 0(2)。
- 旧 V1 日级：见 §2；`v1_audit/V1_PNL_SERIES.json`（09-17 快照，已被本报告用券商全量修正）。
- V2：`trader_v2/state/{opportunity_ledger,hermes_memory,paper_executions,paper_account,evidence_registry,macro_releases}.jsonl`；`trader_v2/research/{OPPORTUNITY_DEGENERATION_DIAG_20260915.md,PIT_VALIDATION_REPORT.md,V2_G3_VERDICT.json,V2_LONG_RUN_AUDIT_20260918.md}`。
- SHA256：`SHA256SUMS.txt`（本目录）。Git commit：见 `SHA256SUMS.txt` 头部记录（两笔式）。

**完成后停止。** 不修改策略、不调参、不优化 Prompt、不启动新交易、不自动进入下一轮 Alpha Research。
