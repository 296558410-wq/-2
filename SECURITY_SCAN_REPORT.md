# SECURITY_SCAN_REPORT.md — 提交前密钥扫描闸门

- 归档时点：2026-10-03（Asia/Shanghai）
- 扫描目标：`C:\AIQuant-XAUUSD-Systems`（**排除 `.git/`**）
- 扫描工具：**自定义健壮扫描器**（本机**未安装** `gitleaks`，也**未安装** `detect-secrets`；
  故按策略回退到自定义扫描器）
- 结论：**SECRET_FOUND = false**（未发现真实密钥）→ 闸门**通过**，允许本地提交。

## 1. 覆盖的检测规则

| 类别 | 规则 |
|---|---|
| 云/平台密钥 | AWS `AKIA...`、OpenAI `sk-...`、Anthropic `sk-ant-...`、GitHub `ghp_/gho_/ghu_/ghs_/ghr_` + `github_pat_`、Slack `xox?-`、Google `AIza...` |
| 凭据块 | `-----BEGIN ... PRIVATE KEY-----`、JWT (`eyJ...`)、`Authorization: Bearer <token>` |
| 关键字赋值 | `api_key|secret|token|password|access_key|private_key|client_secret` 赋值且值长度≥12 且香农熵≥3.0（排除占位符/`os.environ`/`getenv` 等） |
| 敏感文件名 | `.env*`、`*.key`、`*.pem`、`*.p12`、`*.pfx`、`credentials*`、`secrets*`、`*_rsa`、`id_ed25519` |

## 2. 结果

| 指标 | 值 |
|---|---|
| 扫描文本文件数 | 5226 |
| 敏感文件名命中 | **0** |
| 真实密钥命中 | **0** |
| 疑似命中（false positive） | **1** |

### 唯一疑似命中（已判定为**误报**）

```
file : V3/opportunity_engine/v1_close_runid_forensic_r20/_v1_close_runid_r20.py
type : KEYWORD_ASSIGNMENT  (key = TOKEN)
match: "V1_RUN_20260924_RESET_01"
```

- 说明：该处 `TOKEN` 是**运行 ID（run id）字符串**，不是凭据；因熵值触发关键字规则。
- 处置：**判定 false positive**，不阻断，不修改文件。

## 3. 源仓库 `.env` 清单（已排除，未复制、未修改）

| 文件 | 存在 | 是否复制 | 是否修改 |
|---|---|---|---|
| `C:\AIQuant\.env.mt5_demo` | 是 | 否 | 否 |
| `C:\AIQuant\.env.mt5_v3_calib` | 是 | 否 | 否 |
| `C:\AIQuant\.env.v3_jin10` | 是 | 否 | 否 |

## 4. 弱项与缓解

- 无 `gitleaks`/`detect-secrets`：自定义扫描器覆盖常见密钥形态 + 文件名规则；
  对非标准/自定义密钥格式的召回弱于专业工具。
- 缓解：`.gitignore` 硬排除敏感文件；本归档**不 push**（`GitHub clone verification = PENDING_REPO_CREATION`），
  推送前可在此环境补装 `gitleaks` 复扫。

## 5. 判定

```
SECURITY_SCAN_GATE = PASS
SECRET_FOUND = false
SECURITY_BLOCK_REPORT = not required
```
