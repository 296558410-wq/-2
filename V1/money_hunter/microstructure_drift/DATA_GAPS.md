# DATA GAPS — 数据缺口登记（v0，2026-09-07）
> 规则：缺口如实标记。**不购买数据；不用 volume 伪装 signed flow；免费/公开/现有 broker 数据可考古。**

## TOP 1：SIGNED / AGGRESSOR FLOW（任务书 §八 = TOP DATA BLIND SPOT）
- 状态：**DATA GAP（未解决）**
- 现状：FXTM feed 为纯报价（bid/ask），`volume=0`（staging_fxtm 全部 0 实测）；DUKA bi5 = 报价更新（非 trades）。
  → 主动成交方向（谁在 aggress）**从未被直接观测**。activity≠order flow、volume≠signed flow 纪律维持。
- 考古尝试记录：
  - FXTM MT5 tick `volume/volume_real` 恒 0 → 该通道无 trades 数据（9-06/9-07 实测）。
  - DUKA 免费 bi5 = 5 秒级报价（2023-09..2024-03 + 2026-08 已 assembled）→ 无 T&S 成交流。
  - 无 L2/queue/深度（RQ-07 v0 已记录：无 L2/queue）。
- 可能免费解（未验证/待办，不花钱）：
  - MT5 **Demo** 账户 tick（若含 real-time trades 字段）→ 免费可测（待用户一次性注册）。
  - 公开 T&S 数据集考古（GC 期货 CME 类）→ 之前 ZERO-BUDGET 考古结论：GitHub/CME 样例无可用 GC 数据集；
    唯一未测层 = Databento GC MDP3（$25 采购门，**非免费，待批**，S-07）。
- 绝不：用 volume 字段冒充 signed flow（当前 volume≡0，冒充 = 造假）。

## 执行反馈（任务书 §七，长期解锁模块）
- 状态：**模块已定义 + 代码就绪（demo_exec_instrument.py），等待免费 MT5 Demo**
- 定义字段（未来接入即记录）：`request_time / quote_time / fill_time / requested_price / filled_price /
  spread / slippage / reject / latency`（+ market/limit 标记）
- 输出目标：`exec/*.json`（供 RQ-07 Execution Reality Gate 校准；v0 无 L2/queue）
- 红线：真实账户交易 API 绝不触碰；不自动下单；不花钱。Demo 成交乐观 = 下界（已标注于 README）。

## 其他已知缺口（登记不重复考古）
| 缺口 | 状态 | 影响 |
|---|---|---|
| tick 级成交流（aggressor side） | DATA GAP | 执行层唯一可能藏每日可重复钱的位置，未观测 |
| L2 深度/queue | DATA GAP | 无深度动态解读；有 signed flow 后可降级为锦上添花 |
| DUKA HTTP feed 2026-08-05+ 空体 | 维持 | 跨 feed 验证窗关闭（9-06 记录） |
| 2023-12 DUKA tick 整月服务器侧不可达 | 维持 | 长期基准少一个月 |
| MT5 tick 历史接口（copy_ticks_range 部分返回空） | 观察 | live 采集 9-06/07 多次 NO_NEW_TICKS；terminal 开着但 history 无新 tick —— 待下个交易时段复核，若持续则属采集器故障需上报（宪章 E 类） |
| 期权曲面/skew（D5/D7） | DATA GATE(贵) | 非 HF 目标，不主动解锁 |

## 时间戳与维护
- last_updated_utc: 2026-09-07T00:00:00Z（首次建档）
- 维护者：money-hunter 周评审（每轮核对"缺口是否已被免费手段关闭"；发现新免费源才更新，不重复考古已登记项）
