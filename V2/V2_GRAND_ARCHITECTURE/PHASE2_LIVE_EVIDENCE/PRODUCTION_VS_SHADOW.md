# PRODUCTION_VS_SHADOW

> 每周期对照：Production Reference VS Strategy A…N VS Strategy Brain。
> 回答：谁发现机会/谁没发现/谁与 Reference 一致/谁互相冲突/谁产生更多假机会/谁在特定 regime 更好。
> **不能只看收益。**

## 决策对照计数 (production_status, shadow_final) → cycles

| production | shadow_brain | cycles |
|---|---|---|
| NONE | WAIT | 624 |
| NONE | ENTER_SHORT | 562 |
| NONE | ENTER_LONG | 438 |
| NONE | WAIT_DATA_GAP | 59 |
| WAIT | WAIT | 36 |
| WAIT | ENTER_LONG | 24 |
| WAIT | ENTER_SHORT | 19 |
| TRADE | WAIT | 3 |
| TRADE | ENTER_LONG | 1 |
| TRADE | ENTER_SHORT | 1 |

## 解读（诚实口径）

- Production 在种子窗口以 `WAIT` 为主（真实周期里 91 WAIT / 6 TRADE）。
- Shadow Brain 需要 ≥2 个一致策略才 `ENTER_*`，多数周期为 `WAIT`/`CONFLICT`。
- 谁产生更多假机会：见 `FALSE_ALPHA_REPORT`（以 60m 结果判定）。
- 谁在特定 regime 更好：见 `REGIME_STRATEGY_MATRIX.json`。
