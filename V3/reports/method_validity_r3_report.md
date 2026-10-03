# Method Validity Report — MV-R3（Positive Control 修复）

`ts_utc = 2026-09-25T11:57:09.387615+00:00`

**METHOD_VALIDITY = VALID**

## 四象限（§33）

|  | 应识别 | 应拒绝 |
| --- | ---: | ---: |
| Positive Control | **PASS** | PASS |
| Negative Control | PASS (未误识别) | **PASS** |

```text
TRUE STRUCTURE      → DETECT          ✓（植入 16 事件 → MECHANISM_SUPPORTED）
RANDOM STRUCTURE    → NOT SUPPORTED   ✓（三个零模型 supported_rate 全为 0.00）
```

## 比较表（§57 口径）

| 数据 | Supported | Uncertain | Rejected | Supported Rate |
|---|---:|---:|---:|---:|
| REAL（R2 基线，未变） | 0 | 1 | 3 | 0.0 |
| NC-A | 0 | — | — | 0.0 |
| NC-B | 0 | — | — | 0.0 |
| NC-C | 0 | — | — | 0.0 |
| **POSITIVE CONTROL** | **1** | 0 | 0 | **1.0** |

## R2 → R3 到底改了什么（只改正控，未改验证器）

```text
R2 正控失败的两个机制原因（R2 报告已诊断）：
  ① 事件间隔恰好 = 6h 分离窗 → 判据是「> 6h」不成立 → 16~30 个植入事件全部并成 1 个事件
  ② 合并后该事件内 30 行签名完全相同 → 触发退化判据 → FATAL_ARTIFACT → REJECTED
  ③ 更深一层：R2 判定要求 TIME_STABILITY == HIGH，而这需要「事件时间比随机更成簇」；
     等间隔或均匀铺开的排布都无法满足（这正是 R1 缺陷修复后留下的正确门槛）

R3 的正控设计（预注册、一次执行、不调参）：
  · 簇发式复现结构：4 个 episode × 4 个事件；簇内间隔 7/8/9/11h（全部 > 6h），簇间 240/264/300h 静默
  · 每事件在冻结范围内变化 persistence/duration/intensity → 签名不完全相同，避开退化判据
  · crossmarket = NONE（不依赖 ^TNX 代理）· market_state = VOL_NORMAL（映射到 M01）
  · 16 事件 ≥ MIN_INDEPENDENT_EVENTS(8)，间隔离散但全部大于分离窗（非固定周期）
  · definition_hash = ca4d92baa9b022a5d2e2 · dataset_hash = 72d8593a2f8c2f291eef
```

## 正控审计（§26/§27/§28/§29）

```json
{
 "synthetic_events_defined": 16,
 "independent_events_detected": 16,
 "within_tolerance": true,
 "FATAL_ARTIFACT": false,
 "duplicate_events": 0,
 "cross_grid_events": 0,
 "mechanism_id": "M01",
 "expected_mechanism": "M01",
 "time_stability": "HIGH",
 "counter_evidence_level": "WEAK",
 "gaps_all_above_window": true
}
```

```text
EXPECTED_MECHANISM_DETECTED = TRUE ✓（M01，与预注册一致）
FATAL_ARTIFACT = FALSE ✓ · 独立事件 16/16 在容差内 ✓ · 无重复 ✓ · 无跨网格重复计数 ✓
TIME_STABILITY = HIGH（置换 p = 0.002 ≤ 0.05，比随机零假设更成簇）✓
```

## 冻结与隔离证据

```text
R2 registry_hash = 9913dd6d9860f5e0fb3b（与 R2 运行一致，未改动）
真实输入四份哈希运行前后一致 · 合成数据从未进入真实账本（synthetic_in_real_ledgers = false）
合成数据对真实计数的影响：0（real_opportunities=1999 · real_mechanisms=4 · real_events=127 · real_candidates=0）
本任务未修改：R2 验证器 / NC / Null Model / 分离窗 / Artifact 规则 / 反证规则 / Candidate 门 / 真实数据
```
