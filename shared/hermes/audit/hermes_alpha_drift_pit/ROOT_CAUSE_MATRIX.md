# 根因矩阵（ROOT_CAUSE_MATRIX）— V1/V2 Hermes Alpha Drift & PIT Forensics

> 词表取自任务书；每个发现**只归入有证据支持的类别**。
> 证据等级：`FACT`（原始记录直读）/ `DERIVED`（派生计算）/ `INTERPRETATION`（明示推断）/ `UNKNOWN`。
> 一句话总纲：**三系统未共享同一“Alpha 漂移”根因；观察到的“先盈后亏”是系统各自的短期 P&L 路径 + 共同的研究/设计偏差，而非可验证的 Hermes Alpha 衰减。** 终态 **`ALPHA_EVIDENCE_INSUFFICIENT`**。

| 类别 | 判定 | 证据等级 | 依据 | 作用系统 |
|---|---|---|---|---|
| `TRUE_ALPHA_DRIFT` | **NOT_SUPPORTED** | DERIVED | 三系统里**从未存在具备 PIT 完整输入证据的 Hermes Alpha 被实际执行**：V1_NEW=控制臂、V2=参照器占位器、V1_OLD 早期输入已轮转不可复原 → 没有可“漂移”的已验证 Alpha | 全部 |
| `MARKET_REGIME_CHANGE` | **NOT_SUPPORTED** | DERIVED | V1 全生命周期审计（v1_audit）：spread p50 0.319→0.349bp、tick 率/波动/波幅同量级 → 环境无实质变化 | V1_OLD |
| `DATA_PIPELINE_CHANGE` | **PARTIAL（非因果）** | FACT | V2：MT5 读取与执行武装耦合 → PAPER 下静默回退 `local_fxtm/sina`（结构性，见 V2_LONG_RUN_AUDIT）；V1 归档 tick 标签为服务器帧(UTC+3)。**均未被证明影响了亏损方向** | V2 / V1 |
| `PIT_LOOKAHEAD` | **NOT_PROVEN（不可认证）** | DERIVED | 可用时点泄漏：16922 条 V2 证据引用中 **0** 条 `retrieved_at > decision_time`、**0** 条 `published_at > decision_time`（FACT）。但：75,394 条证据 `point_in_time_valid=unknown`；73,315 个 evidence_id 携带 `previous_content_sha256`（旧内容被覆盖、未保留）；宏观 878/878 `release_timestamp_unknown` → **内容版本不可复原** ⇒ 不能认证无回填 | V2 |
| `HERMES_INPUT_CHANGE` | **UNKNOWN** | UNKNOWN | V1_OLD 早期决策输入已轮转（仅 state_summary 残留）；V1_NEW 输入为冻结控制臂、未变；V2 输入侧结构性退化（见下） | V1_OLD |
| `HERMES_BEHAVIOR_CHANGE` | **NOT_SUPPORTED** | FACT | V1_NEW `signal_type=BASELINE_CONTROL` 全窗恒定；V2 `decision_source=reference_rules` 全窗恒定（占位器）；无行为变更证据 | V1_NEW / V2 |
| `EXECUTION_CHANGE` | **PARTIAL（非因果）** | FACT | V2 行情源 MT5→fallback（结构性，0 成交）；V1_NEW 执行链无异常（retcode 全 10009、滑点 ≤3.4bps） | V2 |
| `RISK_SYSTEM_EFFECT` | **CONFIRMED（仅 V1_NEW）** | DERIVED | V1_NEW：声明守卫未接线期，**6 笔亏损本应被拦**（连亏/日亏限额），修复后现网出现 `WAIT_RISK`。属**风控缺陷**，非 Alpha 衰减；不改变其余 14 笔亏损的市场实现属性 | V1_NEW |
| `RESEARCH_SELECTION_BIAS` | **CONTRIBUTING** | INTERPRETATION | “前期/后期”窗口由观测者选定；样本极小（V1_OLD 109 笔/15 日、V1_NEW 32 笔/5 日、V2 0 笔）；三段式切分易把随机波动读成“漂移” | 全部 |
| `COMMON_DESIGN_BIAS` | **CONTRIBUTING** | FACT+INTERPRETATION | 三系统被冠以“Hermes”，但实际运行：V1_NEW=控制臂、V2=参照器占位器 + 单一化机会供给（`opp_geo_shock` 148/148 周期）、V1_OLD=LLM 计划引擎但无 PIT 输入快照 ⇒ “Hermes 判断力”**从未被真正测试** | 全部 |
| `NO_IDENTIFIABLE_CAUSE` | **判定（针对 P&L 路径本身）** | DERIVED | V1_OLD 自身审计：入场方向近期未恶化(+1s 胜率 .714>整体 .617)、市场环境未变、连亏在随机范围(93.4%)、根因 `UNRESOLVED`；V1_NEW 同型（14/20 亏损为市场实现） | V1_OLD / V1_NEW |
| `UNKNOWN` | 见 `DATA_GAPS_AND_UNKNOWN.md` | UNKNOWN | 早期输入快照、当时 `data_age`、内容版本、V2 真实成交后果 | 全部 |

## 结构性 vs 因果性（必须同时报两个数）
- **V1_NEW**：守卫接线缺陷结构性覆盖 **32/32 笔**（决策时 `risk_reasons` 全空）；**因果责任 8/32**（本应拦：6 亏 + 2 盈）→ 可预防亏损 **6 笔**。
- **V2**：`opp_geo_shock` 结构性出现在 **148/148 周期**（100%）；但因果上只影响“决策质量”，**成交数为 0** ⇒ 对 P&L 无因果。
- **V1_OLD**：无系统性缺陷被证据支持（根因 `UNRESOLVED`）。

## 明确“不许写”的结论
- 不得写 `V1_HAS_ALPHA` / `NO_ALPHA` / `IS_BROKEN`；不得把“先盈后亏”直接写成因果；
- 不因结果调整分类标准、窗口、成本锚或统计方法；不提出任何新策略/参数。
