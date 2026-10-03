# DATA_PIT_STATUS — 数据与研究状态
只读取 `data_sources/*`、`state/evidence_registry.jsonl`、`state/macro_releases.jsonl`、`agents/macro_global/*`、`research/*`、既有审计。

## 1. 数据源（当前实际）
- **唯一取数入口** = `data_sources/router.py`（commit `359e495`：router = sole data entry；移除 hidden env override）。
- 源优先级（`registry.py`）：历史=`[mt5, local_fxtm, yahoo]`；gold_spot=`[mt5, sina, tencent, local_fxtm]`。
- 当前实际选用（agent1 latest）：gold_spot=**mt5**、silver=mt5、gold_comex=sina、dxy=sina(DINIW)、ust10y=tencent(usUST **代理**)、vix=sina(znb_VIX)、gld=tencent(usGLD)；全部 `_fallback_level=0`（未走 fallback）。
- 宏观源：`sina/tencent`（国内直达）；**已移除** Yahoo/CFTC/BLS（不可达）。

## 2. PIT 状态
| 层 | 状态 | 依据 |
|---|---|---|
| K 线（5m/15m/60m/4h/1d） | **PASS** | `PIT_VALIDATION_REPORT.md`：未收盘 bar=0、单调递增；`get_asof` 不可变 as-of 缓存（`a6229b1`） |
| 报价 freshness | 按 `data_ts` 判定（非取回时刻） | `8b6f064`：freshness from data_ts + health 入门（FAIL→REJECT, DEGRADED→WAIT） |
| 宏观发布时刻 | **FAIL_UNKNOWN** | `macro_releases.jsonl` 878/878 `release_timestamp_unknown=true`；`point_in_time_confidence=low`；38 行 `revision_changed=true` |
| 证据库（news/evidence） | **UNKNOWN** | `evidence_registry.jsonl` 75,394 行 **`point_in_time_valid=unknown` 100%**；73,315 个 id 带 `previous_content_sha256`（内容被覆盖、旧版未留存） |
| 决策证据引用完整性 | **部分缺失** | 1,482 条决策引用的 evidence_id 不在 registry |

## 3. 数据覆盖与缺口
- 覆盖：新闻/证据 2026-09-11 → 2026-10-02；宏观 878 行；K 线由 MT5 提供（V2 独立实例）。
- **Agent2 缺口（5）**：中央行政策利率(无直连 API) · BLS 宏观(403) · COT/CFTC(403) · 全球黄金 ETF 流量(WGC JS 未取) · 央行购金(无源)。
- 跨市场代理：UST10Y 用 **7-10Y ETF 代理**（非 ^TNX）、实际利率用 **TIP 代理** → 语义为“代理”，非真值。

## 4. 研究状态
| 项 | 状态 |
|---|---|
| V2 自身候选 | **无**（决策层 `reference_rules` 占位器，非研究候选） |
| 最近研究结论（V3 线，独立于 V2） | **`NO_VALIDATED_EDGE`**；F2b-R2 / E / F / Phase2 多轮 → NO_VALIDATED_EDGE（COST_INSUFFICIENT 等） |
| R8-B（Hermes 预测） | **UNSUPPORTED**（Hermes-A balanced acc 0.4056 vs 冻结基线 0.5444；ECE 0.1616；弃权 0） |
| KEEP / REJECT / UNCERTAIN | 无 KEEP；候选族多为 REJECT / UNCERTAIN；`CANDIDATE_RESEARCH=0` |
| 正在运行的实验/任务 | **V3 Temporal Hold**（每日同源数据覆盖核查，等 G1≥90d，ETA ~2026-11-02；`TEMPORAL_HOLD RUNNING`）——与 V2 独立 |
| 未完成实验 | V3 时间窗未达（G1 pending）；V2 本身无“未完成成交实验”（0 成交） |

## 5. 判定
- 行情/PIT（K 线）**合格**；**宏观与新闻证据的 PIT 不可认证**（发布时刻缺失 + 内容版本不可复原）。
- V2 决策层**未使用**这些证据做可交易决策（`reference_rules` 占位器）；证据被记录但**未被消费为信号**。
