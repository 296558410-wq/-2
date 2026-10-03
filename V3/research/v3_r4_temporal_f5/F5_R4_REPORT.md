# V3 R4 · F5 独立重验报告（repaired event loader, same-source sample）

- 协议：`F5_R4_FROZEN_PROTOCOL.json`（`registry_hash = adc5a94d7c12d384199931dfb2346484eb053fe7355c0c48e73e6d0777d8b9c6`，计算前冻结）
- 成本锚：0.914 bp（`CALIBRATION_20RT_20260921`，**未修改**）
- 边界：ORDER_SEND=0 / LIVE=NO / 未触碰 V1/V2 / 未改 R1-R3 原始结果 / 未调阈值·方向·持有期·样本过滤 / 未删除不利期 / 无未来数据
- 数据：`SNAPSHOT_FXTM_R4`（同源 FXTM tick，8,911,447 行，59.11 天，44 活跃日；manifest `3417edf9…`，已复验）

## 1. 结论（先说）

```
总判定        = TEMPORAL_EVIDENCE_INSUFFICIENT   （G1 未过 → 硬阻断，门槛不下调）
候选级        = 无 VALIDATED_EDGE；FDR 24 项 0 存活
数据状态      = TEMPORAL_DATA_BLOCKED（同源跨度 59.11d < 90d）
可复现性      = 同一冻结脚本重跑 → 三个结果文件逐字节相同（byte-identical）
```

## 2. Event loader 修正前后（本轮的“修正后重验”核心）

| | R1（缺陷版） | R3→R4（修正版） |
|---|---|---|
| 去重方式 | `set((ts, 文件名))` | 主键 `(pub_time_utc, title, source_file)` **按行** |
| 283 行的结果 | **被折叠成 75 个时间戳** | 283 行全部保留；并发不同事件 208 行**保留** |
| 真重复 | 误判 | **0**（283 行逐字节不同） |
| 进入研究的样本 | 时间戳级 75（F5 实际用 n≈38–50） | **按行 249 / 独立时间戳 67** |
| 与 tick 窗口 | 见 R1 | 249 行内、34 行在窗口外（**保留损失记录**） |

守恒链：`283 raw → 283 PIT → 283 unique → 249 in window → 249 final`（未放宽窗口、未造合成事件、未删除事件）。
R4 计数(249/67) 高于 R3(223/57) 的原因：R4 的 tick 窗口更宽（至 10-02 03:39Z vs R3 至 10-01 12:54Z），多收 26 行。
`EVENT_REGISTRY.json` sha256 = `46b77b6a…`（249 行逐条）。

## 3. F5 样本与主结果（gross / net@1x·2x / IS·OOS net@1x / eff_n / perm_p / bootstrap 95%CI）

| 假设 | h | n | eff_n | gross | net1x | net2x | IS | OOS | perm_p | boot95% |
|---|---|---|---|---|---|---|---|---|---|---|
| E1_EVENT_X_MICRO | 5m | 45 | 44 | +1.621 | +0.707 | −0.207 | +0.440 | +1.299 | 0.084 | [−0.207, +3.399] |
| E2_EVENT_X_VOL | 5m | 57 | 55 | +1.619 | +0.705 | −0.209 | +0.871 | +0.458 | 0.184 | [−0.449, +4.162] |
| E3_EVENT_X_SPREAD | 15m | 6 | 6 | −11.376 | −12.290 | −13.204 | −17.867 | −6.713 | 0.030 | n=6 不足 |
| E4_POST_EVENT_CONT | 15m | 57 | 51 | +2.229 | **+1.315** | **+0.401** | +0.535 | +2.468 | 0.076 | [−0.166, +4.561] |
| E5_POST_EVENT_FADE | 15m | 57 | 51 | −2.229 | −3.143 | −4.057 | −2.363 | −4.296 | 0.076 | [−4.561, +0.166] |

（全表含 1m/5m/15m × 5 假设 + 镜像控制 = 24 项，见 `results_v3_r4.json::W4`。镜像仅作控制，**不构成独立证据**。）

**成本阶梯**：1× 后仅 E1/E2/E4 的最好 horizon 为正（+0.71/+0.71/+1.31）；2× 后仅 E4-15m 为正（+0.40）；3× 全部为负。

## 4. 统计验证

- **block bootstrap**（2000 次, 50 块）：所有 CI 均含 0（E4-15m 上界 +4.56 / 下界 −0.17）⇒ 无显著证据。
- **permutation**（符号翻转 2000, 双侧）：最好的 p=0.0295（E3-15m，但 eff_n=6）；其余 p≥0.076。
- **BH-FDR**（24 项, α=0.05）：**0 项存活**（E3 的 p 也未过其 cutoff 0.0021）。
- **effective_n**：最大 55（E2-5m）；E3 ≤6 ⇒ DATA_BLOCKED。

## 5. Temporal Gate

| 门 | 判据 | 实测 | 结果 |
|---|---|---|---|
| G1 | ≥90 日历天 | **59.11** | ❌ FAIL |
| G2 | ≥40 活跃日 | **44** | ✅ PASS |
| G3 | 时间块稳定性（net@1x，三段按时间切分） | 见下表 | ⚠️ 弱/不稳 |

**G3 明细**（本次补全；完整拆分见 `results_v3_r4_splits.json`，与冻结结果**核心数字逐项相同**）：

| 假设(h) | 三块 net@1x | net 同号？ |
|---|---|---|
| E2_EVENT_X_VOL (5m) | [+0.48, +0.55, +1.08] | ✅ STABLE（但 p=0.18、CI 含 0） |
| E4_POST_EVENT_CONT (15m) | [+0.02, +0.45, +3.47] | ✅ STABLE（B1≈0；p=0.077；CI 含 0） |
| E1_EVENT_X_MICRO (5m) | [+0.12, −0.61, +2.61] | ❌ |
| E5_POST_EVENT_FADE (15m) | [−1.85, −2.28, −5.30] | 同号但为负（fade 侧无经济意义） |
| E1 mirror / E2 mirror | 混号 | ❌ |
| E3（n=9/6） | 样本不足，未做拆分 | — |

session / vol / spread 拆分：18 个“假设×horizon”已产出（`results_v3_r4_splits.json`；n<10 的组合按规则不报）。
**G1 失败 ⇒ 全部候选（含 5 个假设与镜像）本轮一律 `TEMPORAL_EVIDENCE_INSUFFICIENT`；G3 即使个别稳定也不改变该硬阻断。**

## 6. 判定词与最终

- 候选级 taxonomy：E1/E2/E4 = `EDGE_UNCERTAIN`；E2镜像/E5 = `COST_INSUFFICIENT`；E3 及其镜像 = `DATA_BLOCKED`。
- 叠加 temporal gate 后：全部 `__gate = TEMPORAL_EVIDENCE_INSUFFICIENT`。
- `FINAL = NO_VALIDATED_EDGE`；`FINAL_REASON = TEMPORAL_DATA_BLOCKED (59.11d < 90d) + 无候选通过 FDR/CI`。

## 7. 复现与完整性

- 同一冻结脚本重跑：`results_v3_r4.json` / `DATA_REGISTRY.json` / `EVENT_REGISTRY.json` **逐字节相同**（sha256 一致）。
- splits 补跑：核心数字逐项相同（脚本内置断言 `IDENTICAL`），仅新增 `splits` 段。
- 快照复验：`MANIFEST.json` sha256 与冻结协议声明 `3417edf9…` **MATCH**；抽检 6/44 个 parquet 哈希 6/6 一致；44 文件/8,911,447 行。

## 8. 缺口与 UNKNOWN

见 `FAILURE_UNKNOWN.md`（34 个窗口外事件、staging→live 的 09-04→09-07 间断、volume=0 报价代理、E3 样本不足、G3 部分不可算、DUKA 异源排除、90 天行为未知）。
