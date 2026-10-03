# V3 高频 Alpha Discovery R1 — 结论报告

`ts_utc = 2026-09-25T10:22:16.660226+00:00` · 任务 `V3_HIGH_FREQUENCY_ALPHA_DISCOVERY_R1`

**最终状态：`V3_ALPHA_DISCOVERY_R1 = COMPLETE_NO_CANDIDATE`**

```text
ORDER_SEND = 0 · V3_FORWARD = OFF · V3_SHADOW = OFF · V3_LIVE = OFF
未改 V3 calibration / execution adapter / risk layer / MT5 · V1/V2 完全隔离且未触碰
```

## §十七 汇报格式（按要求逐项）

```text
V3 高频 Alpha Discovery R1

数据：
  覆盖：2025-01-01 23:00:00 → 2026-09-18 21:58:00 (UTC)
  有效M1：607992 / 总 607992
  缺失：>1h 断档 445 处（周末/假日休市）· 最大间隔 262920.0s · 无人工补齐
  数据质量：重复 0 · NaN 0 · 非正价 0 · OHLC 违规 0
  语义：price=BID(VERIFIED) · tz=EST UTC-5(VERIFIED) · DST=NOT_APPLICABLE(VERIFIED)
        XAUUSD_DEFINITION/BAR_OPEN_CLOSE/LICENSE = UNKNOWN（未偷改为 VERIFIED；open/close 用 ±1 bar 敏感性处理）

机制：
  发现：8 个机制族（A 动量 / B 反转 / C 波动状态 / D 时间结构），定义在测试前冻结 (registry 77c48ac1b08f)
  测试：8 个 · raw_n 总计 235523 · effective_n 总计 56205
  淘汰：8 个 REJECT · 0 个 CANDIDATE

成本：
  0x：HF_A1_MOMENTUM_BREAKOUT60=0.0455, HF_A2_MOMENTUM_IMPULSE5=-0.358, HF_B1_REVERSION_IMPULSE3=0.2676, HF_B2_REVERSION_BREAKDOWN60=0.4523, HF_C1_VOLCOMP_BREAKOUT=-0.0615, HF_C2_VOLEXP_FADE=-1.2459, HF_D1_NY_OPEN_MOMENTUM=-0.9764, HF_D2_ASIA_REVERSION=-1.4342
  1x：HF_A1_MOMENTUM_BREAKOUT60=-0.8685, HF_A2_MOMENTUM_IMPULSE5=-1.272, HF_B1_REVERSION_IMPULSE3=-0.6464, HF_B2_REVERSION_BREAKDOWN60=-0.4617, HF_C1_VOLCOMP_BREAKOUT=-0.9755, HF_C2_VOLEXP_FADE=-2.1599, HF_D1_NY_OPEN_MOMENTUM=-1.8904, HF_D2_ASIA_REVERSION=-2.3482
  2x：HF_A1_MOMENTUM_BREAKOUT60=-1.7825, HF_A2_MOMENTUM_IMPULSE5=-2.186, HF_B1_REVERSION_IMPULSE3=-1.5604, HF_B2_REVERSION_BREAKDOWN60=-1.3757, HF_C1_VOLCOMP_BREAKOUT=-1.8895, HF_C2_VOLEXP_FADE=-3.0739, HF_D1_NY_OPEN_MOMENTUM=-2.8044, HF_D2_ASIA_REVERSION=-3.2622
  3x：HF_A1_MOMENTUM_BREAKOUT60=-2.6965, HF_A2_MOMENTUM_IMPULSE5=-3.1, HF_B1_REVERSION_IMPULSE3=-2.4744, HF_B2_REVERSION_BREAKDOWN60=-2.2897, HF_C1_VOLCOMP_BREAKOUT=-2.8035, HF_C2_VOLEXP_FADE=-3.9879, HF_D1_NY_OPEN_MOMENTUM=-3.7184, HF_D2_ASIA_REVERSION=-4.1762

稳定性：
  WF：HF_A1_MOMENTUM_BREAKOUT60={'fold1': -0.803, 'fold2': -0.855, 'fold3': -0.969}, HF_A2_MOMENTUM_IMPULSE5={'fold1': -1.09, 'fold2': -1.874, 'fold3': -0.914}, HF_B1_REVERSION_IMPULSE3={'fold1': -0.708, 'fold2': -0.076, 'fold3': -1.134}, HF_B2_REVERSION_BREAKDOWN60={'fold1': -0.478, 'fold2': -0.246, 'fold3': -0.656}, HF_C1_VOLCOMP_BREAKOUT={'fold1': -0.936, 'fold2': -0.949, 'fold3': -1.055}, HF_C2_VOLEXP_FADE={'fold1': -2.24, 'fold2': 1.786, 'fold3': -5.949}, HF_D1_NY_OPEN_MOMENTUM={'fold1': -0.664, 'fold2': -4.045, 'fold3': -1.37}, HF_D2_ASIA_REVERSION={'fold1': -1.695, 'fold2': -3.716, 'fold3': -1.849}
  Block：HF_A1_MOMENTUM_BREAKOUT60=[-1.042, -0.707], HF_A2_MOMENTUM_IMPULSE5=[-1.735, -0.763], HF_B1_REVERSION_IMPULSE3=[-1.232, -0.081], HF_B2_REVERSION_BREAKDOWN60=[-0.696, -0.237], HF_C1_VOLCOMP_BREAKOUT=[-1.094, -0.855], HF_C2_VOLEXP_FADE=[-5.598, 0.2], HF_D1_NY_OPEN_MOMENTUM=[-4.058, 0.511], HF_D2_ASIA_REVERSION=[-3.453, -1.259]
  Permutation：HF_A1_MOMENTUM_BREAKOUT60=0.60117, HF_A2_MOMENTUM_IMPULSE5=0.26644, HF_B1_REVERSION_IMPULSE3=0.82931, HF_B2_REVERSION_BREAKDOWN60=0.98251, HF_C1_VOLCOMP_BREAKOUT=0.68943, HF_C2_VOLEXP_FADE=0.93006, HF_D1_NY_OPEN_MOMENTUM=0.94754, HF_D2_ASIA_REVERSION=0.82515
  FDR：BH q=0.05 · 进入 FDR 阶段 8 个 · 阳性 0 个

Candidate：
  数量：0
  hypothesis_id：无

最高频机会（按 net_edge×frequency 排序第一名，仅供参考，非 Candidate）：
  {'hypothesis_id': 'HF_C2_VOLEXP_FADE', 'net_edge_bp': -2.1599, 'opportunities_per_day': 0.408, 'score': -0.8812, 'status': 'REJECT'}
  机会/小时与净edge见 opportunity_discovery_report.json 的 ranking 段

反证：
  主要失效条件：①【成本】——最好的毛边仅 +0.45bp，不到 0.914bp 往返成本的一半；
                ②【无统计显著性】——全部 permutation p ≥ 0.27，BH-FDR 阳性 0；
                ③【0x 即负】5/8 个机制在零成本下就已为负（无毛边）
```

## 一、数据集

```json
{
 "coverage": {
  "earliest_utc": "2025-01-01 23:00:00",
  "latest_utc": "2026-09-18 21:58:00",
  "total_bars": 607992,
  "valid_bars": 607992,
  "months": {
   "2025-01": 30196,
   "2025-02": 27440,
   "2025-03": 29271,
   "2025-04": 28947,
   "2025-05": 29846,
   "2025-06": 29188,
   "2025-07": 31498,
   "2025-08": 28970,
   "2025-09": 30208,
   "2025-10": 31378,
   "2025-11": 27657,
   "2025-12": 29401,
   "2026-01": 28827,
   "2026-02": 27429,
   "2026-03": 30595,
   "2026-04": 28976,
   "2026-05": 28822,
   "2026-06": 30144,
   "2026-07": 31414,
   "2026-08": 29437,
   "2026-09": 19164
  },
  "session_coverage_utc": {
   "asia_00_06": 159330,
   "london_07_12": 159462,
   "ny_13_20": 210661,
   "late_21_23": 51959
  },
  "weekday_coverage": {
   "0": 121475,
   "1": 122744,
   "2": 122542,
   "3": 121043,
   "4": 114481,
   "6": 5707
  }
 },
 "gaps": {
  "max_gap_s": 262920.0,
  "gaps_gt_5min": 451,
  "gaps_gt_1h": 445,
  "gaps_gt_24h": 91
 },
 "quality": {
  "duplicate_ts": 0,
  "nan_prices": 0,
  "nonpositive": 0,
  "high_lt_low": 0,
  "high_lt_oc": 0,
  "low_gt_oc": 0,
  "median_step_s": 60.0,
  "zero_volume_rows": 607992
 },
 "file_hash_sha256": "dd633889fa63586baae9a726079c1643",
 "replay_check": {
  "parquet_sha256": "dd633889fa63586baae9a726079c1643f9671c20895306f49f284d57783601dd",
  "second_read_matches": true,
  "declared_in_dataset_report": "dd633889fa63586baae9a726079c1643f9671c20895306f49f284d57783601dd",
  "matches_declared": true
 }
}
```

## 二、逐机制结果（全指标）

| hypothesis_id | family | raw_n | eff_n | hold | 0x | 1x | 2x | 3x | WF folds | CI95 | perm p | 状态 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| HF_A1_MOMENTUM_BREAKOUT60 | A_momentum | 22597 | 11827 | 5 | 0.0455 | -0.8685 | -1.7825 | -2.6965 | [-0.803, -0.855, -0.969] | [-1.042, -0.707] | 0.60117 | **REJECT** |
| HF_A2_MOMENTUM_IMPULSE5 | A_momentum | 12180 | 6365 | 3 | -0.358 | -1.272 | -2.186 | -3.1 | [-1.09, -1.874, -0.914] | [-1.735, -0.763] | 0.26644 | **REJECT** |
| HF_B1_REVERSION_IMPULSE3 | B_reversal | 11413 | 5412 | 5 | 0.2676 | -0.6464 | -1.5604 | -2.4744 | [-0.708, -0.076, -1.134] | [-1.232, -0.081] | 0.82931 | **REJECT** |
| HF_B2_REVERSION_BREAKDOWN60 | B_reversal | 17946 | 9936 | 5 | 0.4523 | -0.4617 | -1.3757 | -2.2897 | [-0.478, -0.246, -0.656] | [-0.696, -0.237] | 0.98251 | **REJECT** |
| HF_C1_VOLCOMP_BREAKOUT | C_vol_state | 154486 | 19441 | 10 | -0.0615 | -0.9755 | -1.8895 | -2.8035 | [-0.936, -0.949, -1.055] | [-1.094, -0.855] | 0.68943 | **REJECT** |
| HF_C2_VOLEXP_FADE | C_vol_state | 659 | 255 | 5 | -1.2459 | -2.1599 | -3.0739 | -3.9879 | [-2.24, 1.786, -5.949] | [-5.598, 0.2] | 0.93006 | **REJECT** |
| HF_D1_NY_OPEN_MOMENTUM | D_time_structure | 5291 | 917 | 15 | -0.9764 | -1.8904 | -2.8044 | -3.7184 | [-0.664, -4.045, -1.37] | [-4.058, 0.511] | 0.94754 | **REJECT** |
| HF_D2_ASIA_REVERSION | D_time_structure | 10951 | 2052 | 15 | -1.4342 | -2.3482 | -3.2622 | -4.1762 | [-1.695, -3.716, -1.849] | [-3.453, -1.259] | 0.82515 | **REJECT** |

## 三、机会频率与净edge（V3 目标是高频）

```json
[
 {
  "hypothesis_id": "HF_C2_VOLEXP_FADE",
  "net_edge_bp": -2.1599,
  "opportunities_per_day": 0.408,
  "score": -0.8812,
  "status": "REJECT"
 },
 {
  "hypothesis_id": "HF_D1_NY_OPEN_MOMENTUM",
  "net_edge_bp": -1.8904,
  "opportunities_per_day": 1.467,
  "score": -2.7732,
  "status": "REJECT"
 },
 {
  "hypothesis_id": "HF_B1_REVERSION_IMPULSE3",
  "net_edge_bp": -0.6464,
  "opportunities_per_day": 8.66,
  "score": -5.5978,
  "status": "REJECT"
 },
 {
  "hypothesis_id": "HF_B2_REVERSION_BREAKDOWN60",
  "net_edge_bp": -0.4617,
  "opportunities_per_day": 15.899,
  "score": -7.3406,
  "status": "REJECT"
 },
 {
  "hypothesis_id": "HF_D2_ASIA_REVERSION",
  "net_edge_bp": -2.3482,
  "opportunities_per_day": 3.283,
  "score": -7.7091,
  "status": "REJECT"
 },
 {
  "hypothesis_id": "HF_A2_MOMENTUM_IMPULSE5",
  "net_edge_bp": -1.272,
  "opportunities_per_day": 10.185,
  "score": -12.9553,
  "status": "REJECT"
 },
 {
  "hypothesis_id": "HF_A1_MOMENTUM_BREAKOUT60",
  "net_edge_bp": -0.8685,
  "opportunities_per_day": 18.925,
  "score": -16.4364,
  "status": "REJECT"
 },
 {
  "hypothesis_id": "HF_C1_VOLCOMP_BREAKOUT",
  "net_edge_bp": -0.9755,
  "opportunities_per_day": 31.108,
  "score": -30.3459,
  "status": "REJECT"
 }
]
```

## 四、反证优先（§十三）

```text
什么时候失效？—— 在【成本 ≥ 1x】时全部失效；5/8 在 0x 就已为负。
为什么失效？  —— 毛边量级(0.05~0.45bp) 比往返摩擦(0.914bp) 小一个量级：这些 1 分钟结构确实存在，但不足以覆盖摩擦。
在哪个 regime 失效？—— 分季度结果见 opportunity_discovery_report.json 的 quarter_splits（各季均无稳定正边）。
成本提高多少以后失效？—— 2x/3x 全部更负；即便 0x 也仅 3/8 微正。
换时间段是否失效？—— 三折 WF 与季度切分均无一致性正边。
事件之外是否仍存在？—— 本窗口与 Jin10 事件层【无重叠】(数据止 2026-09-18，事件层 09-21..26) → 事件族未检验(NOT_TESTABLE)。
是否只是单一行情造成？—— 否；样本跨 20.7 个月、608k 根，且各机制 effective_n 5k~19k。
```

## 五、语义与泄漏处理（§五/§十一）

```text
BAR_OPEN_CLOSE=UNKNOWN → 对每个机制做了 ±1 bar 位移敏感性（semantics_sensitivity）
  —— 结论：位移不改变任何机制的 REJECT 判定（无一个由正翻负或由负翻正而改变等级）
未来泄漏：所有特征仅由 ≤t 的 bar 计算；入场在 t+1 收盘、出场在 t+1+hold 收盘 → 无未来信息
重叠样本：报告 raw_n 与 effective_n（贪心非重叠），不把重叠信号当独立样本
未拼接任何其它数据源（GC/其它 XAUUSD/不同报价体系）→ 单一 venue、单一报价类型
```

## 六、安全与可复现（§十六）

```json
{
 "replay_check": {
  "parquet_sha256": "dd633889fa63586baae9a726079c1643f9671c20895306f49f284d57783601dd",
  "second_read_matches": true,
  "declared_in_dataset_report": "dd633889fa63586baae9a726079c1643f9671c20895306f49f284d57783601dd",
  "matches_declared": true
 }
}
```

```text
compile check ✓ · secret scan ✓ · path boundary scan ✓ · 数据哈希校验 ✓ · 确定性重放 ✓
未提交任何 key/token/password/.env/凭据/个人信息
V1/V2 未触碰（见 _git_audit.json 的 frozen_checks）
```

## 七、最终状态（§十五/§十七）

```text
V3_ALPHA_DISCOVERY_R1 = COMPLETE_NO_CANDIDATE
V3_PROJECT_STATUS = CLOSED_NO_VALIDATED_EDGE（保持）· V3_LIVE_ALLOWED = NO
V3_FORWARD = OFF · V3_SHADOW = OFF · ORDER_SEND = 0
```

**本阶段的产出不是「没有发现」，而是：把这 8 个机制族在真实成本、时间切分、多重检验与语义不确定性下逐一证伪，并给出可复现的数据集与特征池，供 R2 在【不重复这些方向】的前提下继续发现。**