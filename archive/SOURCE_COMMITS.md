# SOURCE_COMMITS.md

来源仓库（只读快照）：`C:\AIQuant`（单一 git root，V1/V2/V3 共用）。

- 当前分支: `research/v2-grand-architecture-phase2`
- HEAD: `665bf2950302b57a5d8fa8bb539083c2df653286`
- 提交总数: 374
- 首个提交: `03bd487842a678f32b1ef8308fe8f6b91f801940` (2026-09-04 13:28:38 +0800)
- 最后提交: (2026-10-03 19:43:09 +0800) fix(v2-grand-arch-phase2): exclude volatile shadow/ runtime state from SHA256SUMS
- remotes: (none configured)
- dirty: total=682 modified=51 deleted=1 untracked=630 (runtime churn, NOT code change)

## Branches (per-system HEAD)

| system | branch | commit | date | subject | current |
|---|---|---|---|---|---|
| V2 | `research/v2-grand-architecture-phase2` | `665bf2950302` | 2026-10-03 19:43:09 +0800 | fix(v2-grand-arch-phase2): exclude volatile shadow/ runtime state from SHA256SUMS | * |
| V2 | `research/v2-grand-architecture` | `13769ef5d231` | 2026-10-03 12:39:48 +0800 | fix(v2-grand-architecture): regenerate SHA256SUMS to match committed runners |  |
| V2 | `research/v2-historical-strategy-decay-lab` | `23116019e2a4` | 2026-10-03 07:53:39 +0800 | research(v2-historical-strategy-decay-lab): historical archaeology (85 systems, 141 trades) |  |
| V2 | `fix/v2-full-system-repair-20260917` | `2b6a14d454ff` | 2026-10-03 07:06:32 +0800 | docs(v2-phase3): record artifact commit hash in SHA256SUMS |  |
| V2 | `main` | `7fe4828eab19` | 2026-09-16 19:12:06 +0800 | docs(trader_v2): ISSUE note - broker auto-close reconcile state sync (FIXED) |  |
| V2 | `fix/v2-gc-spot-price-space` | `42e8b5843b74` | 2026-09-17 09:29:12 +0800 | docs(audit): V2 full independent read-only audit 2026-09-17 |  |

## Tags

| tag | commit | subject |
|---|---|---|
| `V2_FULL_AUDIT_BASELINE` | `fa935489743c` | fix(trader_v2): repair V2 blockers |
| `V2_REPAIRED_RUN_START` | `a772e1a53a3e` | run(V2_REPAIRED): start V2-PAPER-20260914-231126-5fe2 |
| `v2-pricespace-validated-cf31862` | `06e317589562` | V2 price-space fix frozen baseline |

> V1/V2/V3 **没有各自独立的 git 历史**：三者都在 `C:\AIQuant` 这同一个 git 仓库内。本归档保存当前快照 + 提交/分支/标签注册表，未重写任何本地历史。
