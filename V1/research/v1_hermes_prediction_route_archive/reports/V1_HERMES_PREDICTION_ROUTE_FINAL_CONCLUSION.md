# V1 Hermes 预测路线阶段性结论归档

**生成时间** 2026-09-28T12:03:12.120226+00:00 ｜ **只读归档**：不重跑、不重训、不改任何历史产物 ｜ GIT_HEAD `9e8c4f94089c5700ade3b08ec528e14d83821b2e`

## 证据链

```
R3    9类 STATE@H=8                    → UNSUPPORTED
R4    独立 Hermes-B 审计引擎            → INSTALLED
R5    预测纪律 prompt（结构/机制/弃权）  → FROZEN
R5.1  父进程权威落盘修复                → COMPLETION_GATE PASS (20/20)
R6    9类 STATE@H=8（独立盲测 N=30）  → UNSUPPORTED
R7    目标/特征信息诊断                 → STATE/TRANSITION/DIRECTION 信息弱或缺失；SCENARIO 存在信息
R8-A  SCENARIO@H=4                     → 目标稳定 + 注册表冻结（TIMING 废弃）
R8-B  SCENARIO@H=4（独立盲测 N=32）  → UNSUPPORTED
```

## 核心结论

> **Hermes 当前预测架构在现有信息集下，未证明具有独立、稳定、超过简单基线的市场状态预测能力。**

**不是**：目标粒度问题 · Prompt 调参问题 · R5.1 持久化问题 · Replay/Lookahead 问题 · 交易执行问题。

## 最重要的数据

| 阶段 | 目标 | 结果 |
|---|---|---|
| R3 | STATE@H=8 | UNSUPPORTED |
| R6 | STATE@H=8 | UNSUPPORTED |
| R8-B | SCENARIO@H=4 | UNSUPPORTED |

R8-B：
```
Hermes-A balanced accuracy = 0.4056
Frozen baseline            = 0.5444
Persistence                = 0.75
Simple transition          = 0.75
Raw accuracy               = 0.25      chance = 0.3333
ECE                        = 0.1616
Abstention                 = 0.0
Class recall               = {"DIRECTIONAL": 0.3333, "QUIET": 0.05, "RANGE": 0.8333}
```
Hermes-B：`Adversarial = 16 · AGREE 0 · PARTIAL 7 · DISAGREE 9`

## R7 → R8-A → R8-B 的逻辑

```
R7    发现 SCENARIO 是当前信息集中唯一相对明确的信息对象
  ↓
R8-A  验证 SCENARIO 标签稳定（边界扰动 9.7% / 跨期 TV 0.019 / 最小类占比 0.285）
      选择 H=4（三者稳定并列，信息量最大）→ 冻结 registry（e51a5fdea95535e5）
  ↓
R8-B  在冻结目标上独立重新验证 Hermes
  ↓
      仍然 UNSUPPORTED
```

> **“目标本身稳定且存在信息” ≠ “当前 Hermes 能提取这些信息”。**

## 最终 Gate

```
CAPABILITY_GATE = CLOSED
PREDICTION      = UNSUPPORTED
STRATEGY_MAPPING= CLOSED
TRADING         = CLOSED
```

**不得**解读为：策略失败 / 交易失败 / 市场没有预测性。只能说明：**当前 Hermes 架构 + 当前信息集，没有证明出独立预测能力。**

## 下一阶段边界

**禁止**：继续调 Prompt · 继续换 target · 继续细调分类规则 · 为提高 accuracy 反复挑样本。
**若重开该路线，只允许优先研究**：跨市场更长历史 · 宏观更长 PIT 历史 · 更丰富的独立信息源 · 数据覆盖扩展 —— 然后**重新做独立验证**。

**不得修改 R3–R8-B 历史结论。**

## 安全边界

`ORDER_SEND=0 · ORDER_CHECK=0 · BROKER_WRITE=0 · FORWARD=OFF · SHADOW=OFF · LIVE=OFF · MT5_CALLS=0` ；V1/V2/V3 其他系统未修改。

## 不可变性

{"R3": "PASS", "R4": "PASS", "R5": "PASS", "R5_1": "PASS", "R6": "PASS", "R7": "PASS", "R8A": "PASS", "R8B": "PASS"} ｜ BOUNDARY_VIOLATION = 0
本次归档 CHANGED_FILES = 1（仅新增 `v1_hermes_prediction_route_archive/`）
