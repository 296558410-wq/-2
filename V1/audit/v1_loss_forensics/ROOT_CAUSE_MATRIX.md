# V1 根因矩阵（ROOT_CAUSE_MATRIX）

> 类别定义（本分析统一口径，先定义后应用）：
> - **RISK_ERROR**：声明风控门（按正确语义重建）本应拒单而实际放行（此前审计确认的接线缺陷时期）。
> - **TIMING_ERROR**：方向未被证明错，但 MFE ≥ 0.5R 后全部回吐至 SL（进场/离场时机问题）。
> - **DIRECTION_ERROR**：入场方向与当时 60m 趋势（MA20）相反，且路径几乎未朝持仓方向展开（MFE < 0.5R）。
> - **REGIME_ERROR**：60m 趋势强度弱（|close−MA20| < 0.3×ATR）且路径未展开——趋势信号在不成立的市况里被使用。
> - **NO_IDENTIFIABLE_ERROR**：无上述任何可识别错误特征（=普通市场损失）。
> - **EXECUTION_ERROR / DATA_ERROR / SIGNAL_REASONING_ERROR / EXIT_ERROR**：本样本未触发（证据见下）。

| PRIMARY_ROOT_CAUSE | 亏损数 | trade_ids | 可修复性 | 证据 |
|---|---|---|---|---|
| RISK_ERROR | 6 | V1T-2378071359; V1T-2378074134; V1T-2378095101; V1T-2378098886; V1T-2378348994; V1T-2378382127 | CONFIRMED_FIXABLE | guard_cf.block=True（价差/净额两口径一致）；此前审计 RISK_VIOLATION 与修复 commit 63d5a22/eceeec2（dm dry-run 已显示 WAIT_RISK） |
| TIMING_ERROR | 7 | V1T-2377720619; V1T-2377901575; V1T-2378032044; V1T-2378224663; V1T-2378253584; V1T-2378264395; V1T-2378333628 | POTENTIALLY_FIXABLE | mfe_r ≥ 0.5 且最终 R≈−1（SL 平仓） |
| DIRECTION_ERROR | 3 | V1T-2377943078; V1T-2378067697; V1T-2378322488 | POTENTIALLY_FIXABLE | dir_vs_ma20(60m) 与持仓方向相反 且 mfe_r < 0.5 |
| REGIME_ERROR | 1 | V1T-2378343004 | POTENTIALLY_FIXABLE | 60m trend_strength_atr < 0.3 |
| NO_IDENTIFIABLE_ERROR | 3 | V1T-2378052329; V1T-2378409328; V1T-2378413449 | NOT_FIXABLE_FROM_CURRENT_DATA | 无任何错误特征 |
| UNKNOWN | 0 | — | UNKNOWN | tick 归档窗口缺失（记录于 DATA_GAPS） |

## 其他类别（本样本计数=0，定义保留）
| 类别 | 计数 | 依据 |
|---|---|---|
| EXECUTION_ERROR | 0 | 全部 32 笔：retcode=10009、|slippage| ≤ 3.4bps（限 15）、SL/TP 随单、fill=请求价±3.4bps 内 |
| EXIT_ERROR | 0 | 全部亏损均为券商 SL 按声明规则（1R）触发；realized_R ∈ [−1.047, −1.0]；无提前/延后离场均未见 |
| SIGNAL_REASONING_ERROR | 0 | 本 build 无推理层：信号＝冻结控制臂表（BASELINE_TRANSITION，not_hermes_alpha=true），机械映射无可证伪的“推理错误”；方向问题已归 DIRECTION_ERROR |
| DATA_ERROR（对交易因果） | 0 | 交易期决策用实时终端数据；归档帧问题只影响本研究分析（已修正），不影响当时决策输入 |

## 反事实风险门集合（含盈利样本）
- 声明门（正确语义）本应拦下的执行 = **8** 笔：亏损 6 笔（合计价差 -52.15） + **盈利 2 笔（合计价差 +32.03）**。
- 含义：该缺陷既压进亏损也放过了盈利；**亏损侧 {len(blk_loss)} 笔即 CONFIRMED_FIXABLE 的实质证据**（修复已部署并验证）。
- 注意：这是“应拦未拦”的因果证据，不是收益工程建议；不推导任何参数调整。
