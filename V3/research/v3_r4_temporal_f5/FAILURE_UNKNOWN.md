# V3 R4 · 数据缺口与 UNKNOWN 清单（FAILURE / UNKNOWN REGISTER）

> 规则：研究失败保留为失败证据；**不通过改协议获得 PASS**；不删/不筛不利期；缺口与未知如实列示。

## A. 数据缺口（DATA GAPS）

| # | 缺口 | 事实 | 处置 |
|---|---|---|---|
| A1 | **同源跨度不足 90 天** | 最宽同源 FXTM tick = 2026-08-04→10-02 = **59.11 天**（G1 FAIL） | 门槛不下调；按当前采集节奏自然达标约需再等 **~31 天**（2026-11 上旬）。不得用异源拼接 |
| A2 | staging→live 间断 | staging_fxtm 止于 09-04；live_fxtm 起于 09-07 ⇒ **约 3 天缺口** | 保留为独立段（segments=1774 已按 gap 切分）；不补造 |
| A3 | 事件超出 tick 窗口 | vintage 覆盖至 2026-10-03；**34 个事件行**在 tick 窗之外 | 按窗口规则剔除并在守恒链记录（283→249），不移动窗口 |
| A4 | 无真实成交量 | 两来源 `volume=0` 于 **100%** 行 ⇒ 仅报价代理 | 明示：一切结论基于 quote 数据；不得声称有 trade-flow 证据 |
| A5 | DUKA 不可用 | 异源 + 异 schema（整数缩放价、真实量、小时本地 ms） | **排除**；禁止拼接（本轮未用一行） |

## B. UNKNOWN（不可计算 / 现有数据无法回答）

| # | UNKNOWN | 原因 |
|---|---|---|
| B1 | ≥90 天同源样本下的 F5 真值行为 | 数据不存在（A1）；不做推断 |
| B2 | E2-5m / E4-15m 的“时间块 net 正”是否持续 | 3 块 n≈15–20；p=0.18/0.077；bootstrap CI 均含 0；FDR 全部不过 |
| B3 | E3 的时间块稳定性 | n=9（1m）/6（5m/15m）< 拆分下限 ⇒ 不计算；并已 DATA_BLOCKED |
| B4 | 部分 session/vol/spread 拆分 | n<10 的“假设×horizon”组合按规则不报告（见 `results_v3_r4_splits.json`） |
| B5 | 执行层真值（成交价、滑点、部分成交） | 研究口径为 quote mid；未做执行建模；成本锚 0.914bp 沿用，**本轮未重导** |
| B6 | G3 的协议级精确定义 | 冻结协议只给 “time-block stability”；本轮定义：按事件时间 3 等分、比较块 mean 符号（net 版另行报告）。此为**实现选择**，已两版并列披露，不改变任何门结果 |

## C. 已保留的失败证据（FAILURE RECORDS）

| # | 失败 | 记录位置 |
|---|---|---|
| C1 | **R1 事件加载器缺陷**：`set((ts, 文件名))` 把 283 行折成 75 时间戳，F5 族被少算 | R3 `EVENT_RECONSTRUCTION_REPORT.md` §2；R1 产物原样保留 |
| C2 | R3 自我实现的第 1 版错误（用了不存在的 `event_name`/`country` 作主键，误报 208 真重复） | R3 `results_v3_r3.json::W2.implementation_errors_recorded` |
| C3 | E3_EVENT_X_SPREAD 不可评估（eff_n≤6） | `results_v3_r4.json::taxonomy=DATA_BLOCKED` |
| C4 | **全部候选无 VALIDATED_EDGE**；BH-FDR 24 项 **0 存活** | `results_v3_r4.json::FDR/FINAL` |
| C5 | **G1 未过 ⇒ 硬阻断**（TEMPORAL_EVIDENCE_INSUFFICIENT） | `results_v3_r4.json::temporal_gate_applied`；本目录报告 §5 |

## D. 声明

- 未修改任何冻结假设/信号定义/成本锚/统计协议；未下调任何门槛；未删除不利时间段；未创建合成事件；未放宽窗口。
- 全部产物与哈希见 `SHA256_MANIFEST.json`；复现命令见 R4 报告 §7。
