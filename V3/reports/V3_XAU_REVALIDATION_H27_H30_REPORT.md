# V3 XAUUSD 现货重验证报告：H27 首测 + H30 特殊重验证

`ts_utc = 2026-09-25T07:48:55.658557+00:00`

**最终状态：`V3_XAU_REVALIDATION_H27_H30_NO_CANDIDATE`**

```text
V3_ROUND3_COMPLETE_NO_CANDIDATE（保持）· V3_XAU_SPOT_CONDITIONAL（保持）
V3_FORWARD_READY = FALSE · V3_STRATEGY_FORWARD = NOT_ENABLED · V3_LIVE_ALLOWED = NO
ORDER_SEND = 0 · FORWARD = 0 · LIVE = 0
```

---

## 一、数据版本校验（§6，计算前）

```json
{
 "raw_sha256_match": true,
 "normalized_sha256_match": true,
 "rows_match": true,
 "start_match": true,
 "end_match": true,
 "availability_rule_match": true
}
```

**全部匹配 → 允许计算**（若任一不匹配本应 STOP_AND_REPORT）。

## 二、样本计数（§14：不要用数据行数冒充证据）

```text
raw_rows      : xau=5186  ust10y=3936  dxy=504  vix=503
aligned_rows  : 497   对齐窗口 ['2024-09-24', '2026-09-24']
eligible_rows : 496
signal_rows   : 13
effective_n   : 13
```

> **覆盖限制（必须说明）**：XAU 冻结序列有 20 年，但 H30 的触发变量 DXY/VIX 本次只能取得 **2 年**（Yahoo 长区间两次取数失败，回退到已存的 Round-3 文件；已如实记录于 panel_meta.source_meta）。因此对齐窗口只有 **497** 行。**数据增加 ≠ 证据增加**（§14）：20 年 XAU 数据并没有带来 20 年的 H30 样本。

## 三、XAU 数据定义限制（§7）

```text
XAU_DEFINITION = CONDITIONAL · PIT_STATUS = PIT_CONDITIONAL · bar_close_definition = UNKNOWN
```

> 本次结果属于基于当前已冻结 XAUUSD 研究工作序列的历史重验证，不等同于已经获得完全确认的官方交易所/经纪商 XAUUSD PIT 数据。

**未把 `PIT_CONDITIONAL` 写成 `PIT_PASS`。**

## 四、数据处理规则（§8）

```text
未删除异常 OHLC · 未删除跳点 · 未删除长断档 · 未修正 open/close · 未插值 · 未填补
保留：128 open 越界 / 9 close 越界 / 3 个 >8% 跳点 / 2 个长断档
无观测因异常而无法计算（信号计算只依赖 close 序列与对齐日期）；若发生将按原规则排除并记录
```

---

## 五、H27 首测

### 5.1 冻结定义（不得改动）

```json
{
 "needs": "XAUUSD spot DAILY",
 "hold_days": 1
}
```

### 5.2 阻塞性发现

```text
the frozen H27 definition specifies only {'needs': 'XAUUSD spot DAILY', 'hold_days': 1} and an invalidation ('divergence widens') — it contains NO operational trigger: no divergence measure, no lookback, no threshold, no direction rule. Any implementation would require INVENTING the signal rule, which the task forbids (thresholds/signal definition must stay unchanged; §12 forbids re-choosing samples or rules).
```

### 5.3 判定

```text
final_status = INSUFFICIENT_SAMPLE
reason       = effective_n = 0: no signal can be generated without fabricating a trigger. A test requires a NEW hypothesis id with a pre-registered operational definition (project rule: changing/adding any parameter requires a new hypothesis_id).
```

数据已就绪（这是**描述性**证据，**不是**一次测试，也不产生任何信号）：

```json
{
 "gc_f_rows": 505,
 "xau_rows": 5186,
 "overlap_days": 505,
 "overlap_span": [
  "2024-09-24",
  "2026-09-25"
 ],
 "basis_stats": {
  "mean": 18.736,
  "stdev": 26.553,
  "min": -115.29,
  "max": 123.8
 },
 "note": "DESCRIPTIVE ONLY — this is not a test and produces no signal"
}
```

> 若要让 H27 真正可测，必须用一个**新 hypothesis_id** 预先注册可操作定义（分歧度量、lookback、阈值、方向规则）—— 本任务禁止自行发明这些参数。

## 六、H30 特殊重验证

### 6.1 冻结定义与数据版本（不得改动）

```json
{
 "set_a": {
  "DXY": "down>=0.30%",
  "UST10Y": "down>=5bp",
  "VIX": "up>=5%"
 },
 "a_direction": "LONG",
 "set_b": {
  "DXY": "up>=0.30%",
  "UST10Y": "up>=5bp",
  "VIX": "down>=5%"
 },
 "b_direction": "SHORT",
 "hold_days": 1,
 "entry": "close(t+1)",
 "exit": "close(t+2)",
 "states": 2
}
```
```text
data_version_id = H30_XAU_REVALIDATION_e4d18a7dda5ba315
target_series   = V3_XAU_SPOT_DAILY (XAU spot)
```

### 6.2 统计输出（§16）

```text
n                 = 13
effective_n       = 13   (overlap_ratio=0.0)
mean_return       = 91.753 bp
median_return     = 77.422 bp
win_rate          = 0.8462
gross_return      = 1192.79 bp
net_return        = 91.753 bp/笔 (1x)
profit_factor     = 5.823
max_dd            = -243.66 bp
cost_0x / 1x / 2x / 3x = 92.667 / 91.753 / 90.839 / 89.925
CI95              = [-1.985, 130.605]
permutation_p     = 0.71686
walk_forward      = fold1 26.657 / fold2 84.883 / fold3 179.995
FDR_q             = 0.05 (本次进入 FDR 阶段 0 个，因 n<30)
final_status      = INSUFFICIENT_SAMPLE
```

### 6.3 Regime 与分段稳定性（§15）

```json
{
 "vol_tercile": {
  "low": {
   "n": 4,
   "mean_bp": 83.645,
   "insufficient": true
  },
  "mid": {
   "n": 4,
   "mean_bp": -3.011,
   "insufficient": true
  },
  "high": {
   "n": 5,
   "mean_bp": 174.052,
   "insufficient": true
  }
 },
 "weekday": {
  "0": {
   "n": 3,
   "mean_bp": 53.683
  },
  "2": {
   "n": 2,
   "mean_bp": 185.693
  },
  "3": {
   "n": 4,
   "mean_bp": 98.903
  },
  "4": {
   "n": 4,
   "mean_bp": 66.186
  }
 }
}
```
```json
{
 "2006-2010": {
  "n": 0,
  "insufficient": true
 },
 "2011-2015": {
  "n": 0,
  "insufficient": true
 },
 "2016-2020": {
  "n": 0,
  "insufficient": true
 },
 "2021-2026": {
  "n": 13,
  "mean_bp": 91.753,
  "insufficient": true
 }
}
```

> 分段为空**不代表那些年份没有信号**，而是因为 DXY/VIX 的可得覆盖只有 2 年（见第二节）。分段结果仅作稳定性审计，**未用于择优、未删除任何年份**。

### 6.4 必须直说的一点

```text
均值 +91.753 bp、胜率 0.8462、三折全正，看起来很好。
但：n=13 < 30 → 按 §13 直接 INSUFFICIENT_SAMPLE，无讨论空间。
且：CI95 = [-1.985, 130.605] 跨 0；permutation_p = 0.71686 远不显著。
=> 没有任何统计证据；漂亮的是样本的偶然，不是机制。规则不得因结果漂亮而放松（§12）。
```

### 6.5 历史代理结果（严格分离）

```json
{
 "source": "Round 3 (GC=F gold leg)",
 "n": 13,
 "mean_bp": 91.19,
 "verdict": "INSUFFICIENT_SAMPLE",
 "note": "must NOT be merged with the XAU result"
}
```

## 七、多重检验记录（§19）

```json
{
 "round1": 12,
 "round2": 11,
 "round3": 8,
 "this_revalidation": 2,
 "cumulative_tested": 33,
 "fdr_q": 0.05,
 "reached_fdr": 0,
 "fdr_positive": 0,
 "note": "the revalidation is a data-substitution re-test: it is counted, never deleted from history"
}
```

> 数据替换后的重验证与首次假设测试在统计解释上不同，但不能因为换数据源就把原测试从研究历史中删除。

## 八、与 Round 3 严格分离（§17）

```text
research/v3_strategy_round3/ 未改动（未覆盖、未写入）
新结果只写入 research/v3_strategy_revalidation_xau/{H27,H30}/
```

## 九、输出与哈希（§21）

```json
{
 "schema": "v3_xau_revalidation_manifest/1",
 "ts_utc": "2026-09-25T07:47:36.635138+00:00",
 "data_hash": "e4d18a7dda5ba3155af459619993aa3fb7308c4fb8d9665da0e3179c2f880e9f",
 "xau_frozen_normalized_sha256": "902313acacf0e8ec4eb2256fc1f8f3848a762e07f813f7cfa4e8c8b06451f63b",
 "hypothesis_hash_H27": "1a60a6074c88a61a58ffe1e5329588684ab68d0aa2adf6520c0f91ec4407296f",
 "hypothesis_hash_H30": "e1058cc97d0e730b03a178045400dc8f497b4f045d04b4649a9ea88d3eb50f30",
 "protocol_hash": "6c1af54c9cd6981b61a58cca6e819fc4052a9b58586b14e9f925a7f0dd0361b4",
 "result_hash_H27": "62c3f2d19d0340de96caf7bfcea28f3d9105d839c33f164a4f1cdbb4bff3b23d",
 "result_hash_H30": "6f5285899db36d433a34ffdf98754e51a0bb315dc32c2555e15972ffbfcfaa56",
 "frozen_rules_used": {
  "cost_anchor_bp": 0.914,
  "stress": [
   0,
   1,
   2,
   3
  ],
  "hold_days": 1,
  "entry": "close(t+1)",
  "exit": "close(t+2)",
  "no_param_change": true,
  "no_sample_selection": true
 },
 "historical_results_separate": {
  "H30_gc_proxy": {
   "n": 13,
   "mean_bp": 91.19
  }
 }
}
```

## 十、禁止事项与停止条件（§20）

```text
未自动执行 H24/H25/H26/H28/H29/H31 ✓ · 未进入 Round 4 ✓
未调阈值 / 未重定义状态 / 未改 lookback / 未改持有 / 未改 entry/exit ✓
未删除困难样本 / 未选择最佳年份 / 未改成本 / 未加过滤条件 ✓
FORWARD = OFF · LIVE = OFF · ORDER_SEND = 0 ✓
```

## 十一、最终状态（§22）

```text
V3_XAU_REVALIDATION_H27_H30_NO_CANDIDATE
V3_FORWARD_READY = FALSE · V3_STRATEGY_FORWARD = NOT_ENABLED · V3_LIVE_ALLOWED = NO
```

## 十二、结论（§23）

> 本次问的不是「换成 20 年数据能否找到赚钱策略」，而是：**H27 与 H30 在不改变任何假设、参数与统计规则的前提下，换成 XAUUSD 现货数据后是否仍然存在证据？**
>
> 答案：**H27 仍无法检验**（其冻结定义缺少可操作触发规则，补齐需要一个新 id 的预注册定义）；**H30 仍未达有效样本**（n=13 < 30，且触发变量只有 2 年覆盖）。
>
> **0 Candidate 是有效结果。** 未改变 V3 的 Forward/Live 状态。

## 十三、可见的下一步（需单独授权，本任务不做）

```text
1) 补齐 DXY/VIX 的长历史（目标 2006-2026）→ 才能让 H30 在 20 年窗口上真正检验；当前阻塞是【触发变量的覆盖】，不是黄金数据。
2) 若要测 H27：以新 hypothesis_id 预注册可操作定义（分歧度量 + lookback + 阈值 + 方向）。
3) H24/H25/H26/H28/H29/H31 的重算仍未授权。
```