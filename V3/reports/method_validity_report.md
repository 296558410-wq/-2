# Method Validity Report — MV-R2

`ts_utc = 2026-09-25T11:48:34.750200+00:00`

**METHOD_VALIDITY = INVALID**   (reasons: POSITIVE_CONTROL_FAIL)

## §56 核心比较表（必须展示完整分布）

| 数据 | Supported | Uncertain | Rejected | Supported Rate |
|---|---:|---:|---:|---:|
| REAL | 0 | 1 | 3 | 0.0 |
| NC-A (random time labels) | 0 | — | — | 0.0 |
| NC-B (event time permutation) | 0 | — | — | 0.0 |
| NC-C (mechanism label permutation) | 0 | — | — | 0.0 |
| Positive Control | 0 | 0 | 1 | 0.0 |

```text
REAL_SUPPORTED_RATE = 0.0
NULL_SUPPORTED_RATE = 0.0
EXCESS_SUPPORTED    = 0.0
```

## 四象限（§28）

| | 应识别 | 应拒绝 |
|---|---:|---:|
| Positive Control | **FAIL** | PASS |
| Negative Control | FAIL | **PASS** |

```text
Negative Control → NOT DETECT ✓（随机结构不再被奖励 —— R1 的缺陷已修复）
Positive Control → DETECT ✗（植入结构未被识别 —— 验证器过严）
=> §69 情况 C：METHOD_INVALID，禁止进入 Candidate
```

## 失败诊断（分析，不是调参）

```text
植入结构被拒绝的机制链条（我自己的实现）：
① 正控事件间隔 = 6h，而 1h 网格的事件分离窗恰好 = 6h → 「> 6h」不成立 → 30 个植入事件全部并入【1 个事件】
② 该唯一事件含 30 条签名完全相同的行 → 触发 DATA_ARTIFACT 退化判据 → FATAL_ARTIFACT = TRUE
③ 规则 B1 → MECHANISM_REJECTED
含义：正控【未通过】既可能说明验证器过严，也可能说明该正控定义与分离窗/退化判据在设计上冲突。
按 §70，本轮【不得】重设正控或调规则使其通过；正确的做法是把更合适的正控预注册留到 R3。
```
