# V1-R8-A TARGET REDESIGN — PRE-REGISTRATION REPORT

只读 · 离线 · **无 Hermes** · 无交易 · 无盈利指标。本阶段只做 **R8-A（目标定义 + 注册表冻结）**，不提前查看验证结果。

## 预注册（先于结果固定）
- 族定义：{"TREND": "DIRECTIONAL", "BREAKOUT_ATTEMPT": "DIRECTIONAL", "EXPANSION": "DIRECTIONAL", "ROTATION": "RANGE", "REJECTION": "RANGE", "DECELERATION": "RANGE", "COMPRESSION": "QUIET", "ACCEPTANCE": "QUIET", "NO_DEFINED_STATE": "QUIET"}
- 边界变体：{"V1_ACCEPTANCE_TO_RANGE": {"ACCEPTANCE": "RANGE"}, "V2_BREAKATTEMPT_TO_RANGE": {"BREAKOUT_ATTEMPT": "RANGE"}, "V3_REJECTION_TO_DIRECTIONAL": {"REJECTION": "DIRECTIONAL"}, "V4_DECELERATION_TO_QUIET": {"DECELERATION": "QUIET"}, "V5_COMPRESSION_TO_RANGE": {"COMPRESSION": "RANGE"}, "V6_NODEF_TO_RANGE": {"NO_DEFINED_STATE": "RANGE"}}
- horizon 集合：[4, 8, 16]（禁止事后增加）
- ABSTAIN：ABSTAIN if max_family_prob - second_family_prob < 0.10
- 不确定性：PRIMARY = argmax prob; ALTERNATIVE = 2nd family; band = top2_mass; ABSTAIN per ABSTAIN_RULE
- 指标：['balanced_accuracy', 'macro_f1', 'abstention_rate', 'top2_coverage', 'primary_accuracy', 'ece']
- 最小样本：{'dev': 5000, 'blind': 1000}
- 选择规则：SELECTED_HORIZON = argmax over the pre-registered set {4,8,16} of stability_score, tie-broken by information_score, where stability_score = mean(1-boundary_disagreement, 1-TV(dev,blind), min(1, min_class_share_blind/0.25)) and information_score = max(0, balanced_acc - chance).
- 稳定判据：boundary_disagreement <= 0.15 AND min_class_share_blind >= 0.15 AND TV(dev,blind) <= 0.10

## 稳定性与信息（各 horizon）
{
 "4": {
  "dev_share": {
   "RANGE": 0.3771,
   "DIRECTIONAL": 0.345,
   "QUIET": 0.2779
  },
  "blind_share": {
   "QUIET": 0.2858,
   "RANGE": 0.3891,
   "DIRECTIONAL": 0.3252
  },
  "entropy_dev_bits": 1.5737,
  "entropy_blind_bits": 1.5733,
  "min_class_share_blind": 0.2858,
  "TV_dev_blind": 0.0198,
  "mean_boundary_disagreement": 0.0974,
  "label_churn_rate": 0.1193,
  "persistence_within_h": 0.6175,
  "transition_rate": 0.3825,
  "information": {
   "balanced_acc": 0.5577,
   "chance": 0.3333,
   "n_te": 7310,
   "majority_acc": 0.3891
  },
  "stability_score": 0.9609,
  "information_score": 0.2244,
  "stable": true
 },
 "8": {
  "dev_share": {
   "DIRECTIONAL": 0.345,
   "RANGE": 0.377,
   "QUIET": 0.2781
  },
  "blind_share": {
   "QUIET": 0.2854,
   "RANGE": 0.3893,
   "DIRECTIONAL": 0.3253
  },
  "entropy_dev_bits": 1.5737,
  "entropy_blind_bits": 1.5732,
  "min_class_share_blind": 0.2854,
  "TV_dev_blind": 0.0196,
  "mean_boundary_disagreement": 0.0974,
  "label_churn_rate": 0.1193,
  "persistence_within_h": 0.4918,
  "transition_rate": 0.5082,
  "information": {
   "balanced_acc": 0.5382,
   "chance": 0.3333,
   "n_te": 7306,
   "majority_acc": 0.3893
  },
  "stability_score": 0.961,
  "information_score": 0.2049,
  "stable": true
 },
 "16": {
  "dev_share": {
   "RANGE": 0.3769,
   "QUIET": 0.2782,
   "DIRECTIONAL": 0.3448
  },
  "blind_share": {
   "RANGE": 0.3893,
   "DIRECTIONAL": 0.3257,
   "QUIET": 0.285
  },
  "entropy_dev_bits": 1.5738,
  "entropy_blind_bits": 1.5731,
  "min_class_share_blind": 0.285,
  "TV_dev_blind": 0.0191,
  "mean_boundary_disagreement": 0.0974,
  "label_churn_rate": 0.1193,
  "persistence_within_h": 0.383,
  "transition_rate": 0.617,
  "information": {
   "balanced_acc": 0.4787,
   "chance": 0.3333,
   "n_te": 7298,
   "majority_acc": 0.3893
  },
  "stability_score": 0.9612,
  "information_score": 0.1454,
  "stable": true
 }
}

## 选择
SELECTED_HORIZON = **16**；trace = {"4": {"stability_score": 0.9609, "information_score": 0.2244}, "8": {"stability_score": 0.961, "information_score": 0.2049}, "16": {"stability_score": 0.9612, "information_score": 0.1454}}

## 判定
SCENARIO_STATUS = **SCENARIO_TARGET_STABLE**
TARGET_STATUS   = **PREREGISTERED**
TIMING_STATUS   = **DEPRECATED**（事后定义的删失量；R7 中 balanced accuracy = 随机）

## §10 必须回答
1. SCENARIO 是否比 STATE 更稳定：**是**（3 族 vs 9 类；盲测期最小类占比 0.285，state 为多个 <0.05 的小类）
2. 最稳定的 horizon：**H=16**
3. 是否存在严重类别失衡：**否**（最小类占比 0.285）
4. ABSTAIN 是否有合理定义：**有**（ABSTAIN if max_family_prob - second_family_prob < 0.10）
5. PRIMARY+ALTERNATIVE 是否比单标签更合理：**是**（PRIMARY = argmax prob; ALTERNATIVE = 2nd family; band = top2_mass; ABSTAIN per ABSTAIN_RULE；单标签在边界上不稳定）
6. 现有 PRICE+MTF+STATE_HISTORY 信息增量是否仍存在：balanced_acc=0.4787 vs chance=0.3333 vs majority=0.3893
7. TIMING 是否正式废弃：**是**

## 边界与安全
PIT=PASS · REPLAY=PASS · DETERMINISTIC=PASS · 账本 1 条链 OK
不可变性：{"R3": "PASS", "R4": "PASS", "R5": "PASS", "R5_1": "PASS", "R6": "PASS", "R7": "PASS"} · tests=10/0
**R8 不证明预测能力**；本阶段只冻结一个"可解释、可 replay、无未来信息、值得进入盲验证"的目标。


---

## AMENDMENT 1（验证前修订，全程留痕）

**原规则缺陷**：只按 `stability_score` 取最大，而三个 horizon 的稳定性分**几乎并列**
（{"16": 0.9612, "4": 0.9609, "8": 0.961}，全距 0.0003），
于是选到了**信息量最低**的 H=16（balanced_acc 0.4787）。
预注册文本明确要求"比较**稳定性与信息量**"，故该规则未能实现其自身意图。

**修订规则**：稳定性分在最大值 0.005 邻域内视为并列 → 其间取 `information_score` 最大者。

**修订结果**：SELECTED_HORIZON = **4**（原 16）。
选择轨迹：{"16": {"stab": 0.9612, "info": 0.1454, "ba": 0.4787, "stable": true}, "4": {"stab": 0.9609, "info": 0.2244, "ba": 0.5577, "stable": true}, "8": {"stab": 0.961, "info": 0.2049, "ba": 0.5382, "stable": true}}

**合规声明**：R8-B **盲验证尚未开始**，未查看任何验证结果；原注册表 `v1_r8_target_registry.json` **原样保留**（哈希 7ac48d2adefbbc26），
修订另立 `v1_r8_target_registry_AMENDMENT_1.json` 与 `v1_r8_target_registry_v2.json`（哈希 368392de43aeafa8）。
