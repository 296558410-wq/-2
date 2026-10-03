# V3 R4 · 时间扩展与完整性报告

- 协议：`F5_R4_FROZEN_PROTOCOL.json`，`registry_hash = adc5a94d7c12d384199931dfb2346484eb053fe7355c0c48e73e6d0777d8b9c6`
- 产物：`results_v3_r4.json`｜`DATA_REGISTRY.json`｜`EVENT_REGISTRY.json`｜`SHA256_MANIFEST.json`
- 边界：`ORDER_SEND=0`｜`LIVE=NO`｜未触碰/未读取 V1/V2｜**未修改 R1/R2/R3 任何原始结果**｜**未修改成本锚**｜未调参｜无未来数据｜**未删除不利时间段**｜**未新增 Alpha Sweep 假设**｜X3 与 OFI 本轮不研究

---

## 1. 结论（先说）

```
W1 VERDICT = TEMPORAL_DATA_BLOCKED
```

**同源 FXTM tick 的最大跨度只有 59.11 天，达不到 90 天门槛。门槛未降。**

---

## 2. 数据源普查（为什么拼不出 90 天）

| 来源 | 文件 | 行数 | 跨度 | 字段 | 判定 |
|---|---|---|---|---|---|
| `data/staging_fxtm` | 24 | 4,995,855 | 2026-08-04 → 09-04 | `bid,ask,last,volume,flags,volume_real,ts_utc` | ✅ **同源** |
| `data/live_fxtm` | 20 | 3,915,592 | 2026-09-07 → **10-02** | 同上 + `time,time_msc,utc_ms` | ✅ **同源** |
| `data/staging_duka` | **140** | — | **2023-09 → 2026-08** | **`ms,ask,bid,ask_vol,bid_vol,hour`** | ❌ **异源异定义** |

**DUKA 为什么不能用（任务书明令禁止拼接）**：
- bid/ask 是**整数缩放**值，不是价格
- 带 **`ask_vol` / `bid_vol` 真实成交量**（FXTM 是 0）
- 时间字段是 **`ms`（小时内毫秒）+ `hour`**，不是 UTC 时间戳
⇒ **字段、单位、定义、来源全不同**。拿它凑 90 天就是"拼接异源数据冒充扩展样本"，**不做**。

## 3. 重建的同源快照

```
SNAPSHOT_ID      : V3-SNAP-FXTM-R4
目录              : research/v3_r4_temporal_f5/SNAPSHOT_FXTM_R4/
组成              : staging_fxtm(24) + live_fxtm(20)
TOTAL_ROWS       : 8,911,447
跨度              : 2026-08-04 01:05:00.093Z → 2026-10-02 03:39:06.819Z
calendar_days    : 59.11
active_days      : 44
segments         : 1,774
manifest sha256  : 3417edf9814f9b0f5e38259940449d7eec205fbd2e4ca5ca3630dba9d58f8a14
字段/单位/时区    : ts_utc / ms / UTC（与既有快照一致）
volume           : 两个来源 100% 行为 0（报价代理）
```

## 4. Temporal Gate

| 门 | 判据 | 实测 | 结果 |
|---|---|---|---|
| **G1** | calendar span ≥ **90 天** | **59.11 天** | ❌ **FAIL** |
| **G2** | active trading days ≥ 40 | **44 天** | ✅ PASS |
| G3 | 时间块稳定性 | 见 `F5_R4_REPORT.md` | 见该报告 |

```
TEMPORAL_DATA_BLOCKED  —— G1 未通过，且门槛不下调
```

**⇒ 本轮所有候选（含 F5_R4 全部假设）一律 `TEMPORAL_EVIDENCE_INSUFFICIENT`，不得进入 `VALIDATED_EDGE`。**

## 5. 要拿到 90 天的唯一路径（不做，仅记录）

1. **继续向前收**：同源采集从 2026-08-04 才开始，按当前节奏需再等约 **31 天**（到 2026-11 上旬）才能自然达到 90 天。
2. **回补历史**：需要向 FXTM 索取/导出更早的同源 tick（若其保留历史）——**不能**用别家数据顶替。
3. 二者都不做的话，`TEMPORAL_DATA_BLOCKED` 就是本轮的终态。

## 6. 边界核对

| 项 | 状态 |
|---|---|
| ORDER_SEND / LIVE / 执行 | 0 / NO / 未进 |
| V1/V2 触碰或读取 | 无 |
| R1/R2/R3 原始结果 | **未修改** |
| 成本锚 0.914 bp | **未修改** |
| 参数调整 | 无 |
| 未来数据 | 无 |
| 删除不利时间段 | **无** |
| 新增 Alpha Sweep 假设 | **无** |
| Git 写入范围 | 仅 `research/hermes/trader_v3/` |
