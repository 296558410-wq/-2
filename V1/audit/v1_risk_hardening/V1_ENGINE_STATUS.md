# V1 引擎状态（V1_ENGINE_STATUS）

- 基线审计：`e157789e741e9974f4cb44988a97998ee9a1b456`（ENGINE=FAIL）。
- 本次 hardening 后（2026-10-02）：见下。
- ALPHA STATUS **不受**本任务影响，保持 **UNKNOWN**（无 alpha 研究，且不得与 ENGINE 混同）。

## 评级

| 维度 | 之前 | 现在 | 依据 |
|---|---|---|---|
| ARCHITECTURE | PASS | PASS | 未动架构 |
| DATA | PASS | PASS | 未改数据 |
| PIT | PASS | PASS | 未改 |
| SIGNAL | PASS | PASS | 未改信号 |
| **RISK** | **FAIL** | **PASS** | 7 规则 × A–E 全 PASS（含 DUP/KILL/FAIL-CLOSED），故障注入实测阻断 |
| EXECUTION | PASS | PASS | 单发单点；demo-only；`order_send=0` |
| ACCOUNTING | PASS | PASS | 链 True；独立重算一致 |
| RECOVERY | PASS | PASS | 幂等重建 |
| REPLAY | PASS | PASS | 确定 |
| STATISTICS | UNKNOWN | UNKNOWN | n 不足 |
| ALPHA | UNKNOWN | UNKNOWN | 无 edge / 证据不足 |
| MOAT | PASS | PASS | 回归套件+缺陷库等 |

## 验收闸门

```text
RISK_RUNTIME_MATRIX = PASS
FAIL_CLOSED_TEST    = PASS
DUPLICATE_ORDER_TEST= PASS
KILL_SWITCH_TEST    = PASS
REGRESSION          = PASS   (14/14 CI_PASS)
order_send          = 0
```

## 结论

```text
ENGINE STATUS = PASS      # 所有“继续运行前”的安全阻断项均已通过（修复+故障注入）
ALPHA STATUS  = UNKNOWN   # 独立结论，未变
```

允许从 FAIL → PASS 的依据：基线审计列出的阻断项
- D002 DUPLICATE_ORDER → **FIXED（可达且真实阻断）**
- D003 KILL_SWITCH → **FIXED（文件触发路径 + fail-closed）**
- D009 缺数据非 fail-closed → **FIXED**（5 类输入统一 WAIT_RISK/BLOCK）
- D005 / D010 / D008(外部 watchdog) → **延期且给出 WHY SAFE TO DEFER**（非安全阻断项）

**限制条件（诚实声明）**：
1. 本 PASS 只覆盖**已声明的安全闸门**；不表示策略有效（ALPHA=UNKNOWN）。
2. 延期项若在未来演化为安全阻断（例如去掉券商 SL/TP 托管），必须重新评级。
3. 建议每次改动后运行 `v1up_regression_suite.py` 与 `v1up_hardening_tests.py`；任一非 PASS 即回退评级。
4. 沙箱集成验证覆盖 kill switch 与 baseline；DUP 的端到端由单元级故障注入覆盖（真实 broker 侧重复需实盘场景，未强造）。
