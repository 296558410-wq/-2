# R8 冻结前/后 Diff（R8_BEFORE_AFTER_DIFF）

> 目标：R8 冻结（**2026-09-28T10:47:20Z**，见 R8-A registry `frozen_at_utc`）前后，V1 **runtime** 是否有任何差异。
> 只读；差值均由 git 事实给出。

## 1. R8 冻结锚点
- **R8-A 目标注册表冻结**：`v1_r8_target_redesign/registry/v1_r8_target_registry.json`，`frozen_at_utc = 2026-09-28T10:47:20.540486+00:00`，`frozen_before_any_validation = true`，`registry_hash = 7ac48d2adefbbc26…`（AMENDMENT_1 → `..._v2.json` hash `368392de43aeafa8…`，SELECTED_HORIZON 16→4）。
- **R8-B 盲验证**：SCENARIO@H=4，N=32 → **UNSUPPORTED**。
- **路线归档**：`v1_hermes_prediction_route_archive/`，生成 `2026-09-28T12:03:12Z`，`GIT_HEAD 9e8c4f9…`，`CHANGED_FILES = 1`（仅新增归档目录）。
- **Git 可见的 V1 相关提交**：R8 冻结当日（09-28）git 记录中**无任何 V1 runtime 提交**；最近的上游 V1 提交在 **09-20**（`acaef08` mt5-isolation），其后到 R8 冻结之间**没有 V1 runtime 代码改动**。

## 2. Runtime 差异表（冻结前 vs 冻结后）
| 维度 | 冻结前（≤09-28T10:47Z） | 冻结后 | 差异 |
|---|---|---|---|
| V1 runtime .py 文件集 | 19 tracked（旧 engine）+ v1_upgrade | 同 | **无（0）** |
| 删除/重命名 | 0（除 09-24 state 重置，非代码） | 0 | **无** |
| import 边 | 未变 | 未变 | **无** |
| 数据/PIT 代码 | 未变 | 未变 | **无** |
| RiskGuard/风控代码 | 未在冻结点改动 | 10-02 才有改动（`63d5a22`/`eceeec2`） | 冻结点**无**；冻结后为独立后续任务 |
| Scheduler 入口 | 未变（`v1-upgrade-demo-cycle` cron） | 未变 | **无** |
| State 恢复/初始化 | 09-24 reset 已清空重开 | 同 | 与 R8 无关 |
| Truth/Forensic | 尚未存在（10-02 `ec0907e` 才建） | — | **N/A（时间上晚于 R8）** |

## 3. 结论
- **R8 冻结点前后，V1 runtime 代码 = 零差异。** 冻结只发生在**研究工件**（R8 目标注册表/路线归档），runtime 未变。
- 冻结后出现的 V1 runtime 改动（10-02 的 riskguard/risk-hardening/truth）是**后续独立任务**提交，时间上晚于 R8、内容上不属“僵尸清理”。
- **无任何“清理动作”落在 R8 冻结窗口内的 V1 runtime 上。**

## 4. 证据等级
- R8 冻结时间/哈希：`FACT`（直读 registry）。
- “零 runtime 差异”：`FACT`（git 历史 + 文件集对比）。
- R8 树 **untracked**（`git ls-files = 0`，无 ignore 规则）：⇒ R8 工件的 git provenance 缺失 = `DATA_GAP`（见 `DATA_GAPS_AND_UNKNOWN.md`）。
