# GITHUB_ARCHIVE_VERIFICATION

> 上传后验证（post-upload）。目标 **私有** 仓库：`https://github.com/296558410-wq/-2`（Private）。
> 生成：2026-10-03（本机 GMT+8）。

## 目标与分支

- `REMOTE = https://github.com/296558410-wq/-2.git`
- `BRANCHES = main, archive/2026-10-03-baseline`
- `PUSH_MODE = 首次推送到新建空仓库（目标此前 0 refs）` — **无 force、无覆盖、无历史重写**
- `CONTENT_COMMIT = 795aa0e614a76dd3551d9f54daefc102a8e4ee8f`（V1/V2/V3 归档内容）
  — 本验证文档为追加（additive）提交，位于该内容提交之后。

## 远端 refs（已核对）

| ref | sha |
|---|---|
| `refs/heads/archive/2026-10-03-baseline` | `795aa0e614a76dd3551d9f54daefc102a8e4ee8f` |
| `refs/heads/main` | `795aa0e614a76dd3551d9f54daefc102a8e4ee8f` |

（核对方式：`git ls-remote --heads origin`）

## 验证方法与结果

- `git fetch origin` + `git diff --stat main origin/main` → **空（树完全一致）** → `TREE_MATCH = PASS`
- `git diff --stat archive/2026-10-03-baseline origin/archive/2026-10-03-baseline` → **空** → `PASS`
- `git ls-tree -r --name-only origin/main` → **5249** 文件 → `FILE_COUNT_MATCH = PASS (5249)`
- 顶层树：`.gitignore ARCHITECTURE.md GITHUB_ARCHIVE_VERIFICATION.md README.md REPRODUCTION.md
  SECURITY_POLICY.md SECURITY_SCAN_REPORT.md SOURCE_BASELINE.json SOURCE_REPOSITORY_REGISTRY.json
  SYSTEM_REGISTRY.json V1 V2 V3 VERSION_REGISTRY.json archive docs shared`
- `SECRETS_IN_REMOTE_TREE = 0`（远端树无 `.env` / `.key` / `.pem` / `.p12`）
- 三系统均在：`V1 ✓ V2 ✓ V3 ✓`
- `FULL_CLONE_BACK = NOT_COMPLETED`：本机到 GitHub 链路出现间歇性 `early EOF`；
  改用等价的 **fetch + tree-diff**（对象本地已存在，diff 为空 ⇒ 远端树与本机逐字节一致）→ 判定 `REMOTE_VERIFIED = PASS`

## 边界（本次上传全程）

- `Production changes = 0 · Trading changes = 0 · order_send = 0 · 未停止任何任务`
- 源仓库 `C:\AIQuant` **未修改**；三个 `.env.mt5_*` 未上传、未改动
- 旧仓库 `296558410-wq/-` 的 `main`（协作层）**未被触碰**
- 早前按临时指示向 `296558410-wq/-` 误推过一个 `archive/2026-10-03-baseline` 分支（内容相同），可随时删除

## 状态

```
REMOTE_VERIFIED = PASS
TREE_MATCH      = PASS
SECRETS         = 0
STATUS          = GITHUB_ARCHIVE_COMPLETE
```
