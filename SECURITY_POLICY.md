# SECURITY_POLICY.md — 归档安全策略

## 1. 铁律（不可协商）

- **绝不**把真实密钥（API key / token / password / `.env` / 私钥 / 证书 / cookie）提交或推送。
- 发现真实密钥 → **立即停止上传**，记录路径+类型，生成 `SECURITY_BLOCK_REPORT.md`，
  构造脱敏副本，**不修改原文件、不轮换凭据**。
- 不修改、不移动、不删除源仓库 `C:\AIQuant` 的任何内容。

## 2. 密钥排除清单

以下**已排除、绝不入库**（源仓库根目录）：

| 文件 | 类型 | 处理 |
|---|---|---|
| `.env.mt5_demo` | MT5 demo 凭据 | EXCLUDED（未复制、未修改） |
| `.env.mt5_v3_calib` | V3 校准凭据 | EXCLUDED（未复制、未修改） |
| `.env.v3_jin10` | jin10 凭据 | EXCLUDED（未复制、未修改） |

`.gitignore` 另外硬排除：`.env* *.key *.pem *.p12 *.pfx *.secret credentials* secrets* *.crt *.cer id_rsa*`。

## 3. 运行时/易变资产策略

见 `archive/RUNTIME_EXCLUSION_POLICY.md`；所有被排除项逐条记录在
`archive/ARCHIVE_MANIFEST.json#excluded_runtime_assets` 与 `archive/EXCLUDED_RUNTIME_ASSETS.jsonl`。

## 4. 密钥扫描闸门（提交前强制）

1. 优先级：`gitleaks` → `detect-secrets` → 自定义健壮扫描器。
2. 本机 **无 gitleaks、无 detect-secrets**，故使用**自定义扫描器**（见 `SECURITY_SCAN_REPORT.md`）。
3. 自定义规则覆盖：AWS / OpenAI / Anthropic / GitHub / Slack / Google API key、
   私钥块、JWT、`Authorization: Bearer`，以及关键字赋值
   （`API_KEY|SECRET|TOKEN|PASSWORD|PRIVATE_KEY|...`），并附带 `.env/*.key/*.pem/*.p12/credentials*/secrets*`
   文件名检查。
4. **失败即封闭（fail-closed）**：任一真实密钥 → 阻断提交。

## 5. 账户标识脱敏

- 注册表中只记录 `system ID / magic / mode / broker server`；
  **账户标识记为 `[DESENSITIZED]`**，不含真实账号。
- 若扫描在正文中发现账号/密钥样式字符串，按需脱敏（本归档中未发现）。

## 6. Git 操作禁令

- 无 `git push`、无 `git push --force`、无 remote 创建。
- 不删除/不重写本地历史，不覆盖已存在仓库。
