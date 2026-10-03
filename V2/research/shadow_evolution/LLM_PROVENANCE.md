# LLM_PROVENANCE — 真 LLM endpoint 配置与验证（可审计）

结论：**本环境当前无可用真实 LLM chat 端点** ⇒ 三侧中 `true_llm_agent` 全程显式 `LLM_UNAVAILABLE`（**未**静默退化为 heuristic）。

## 1. 探测证据（只读，2026-10-02T14:26Z 前后）
### a) 环境变量（仅列名称，未打印值）
匹配 `OPENAI|DEEPSEEK|ANTHROPIC|LLM|API_KEY|MODEL|AZURE|OLLAMA|...` 的环境变量：
```
OPENCLAW_CLI / OPENCLAW_GATEWAY_PORT / OPENCLAW_GATEWAY_SERVICE_PID / OPENCLAW_PATH_BOOTSTRAPPED /
OPENCLAW_SERVICE_KIND / OPENCLAW_SERVICE_MARKER / OPENCLAW_SHELL / OPENCLAW_SYSTEMD_UNIT / OPENCLAW_WINDOWS_TASK_NAME
```
⇒ **无任何 LLM API key 环境变量**。

### b) 仓库 `.env*`（仅列变量名）
`.env.mt5_demo`(MT5) · `.env.mt5_v3_calib`(MT5) · `.env.v3_jin10`(Jin10 token) ⇒ **无 LLM key**。

### c) 本地 OpenAI 兼容端点探测
| 端点 | 结果 |
|---|---|
| `127.0.0.1:19432`（OpenClaw `llama-cpp` provider） | `/health → 200`；`/v1/models → 200` 仅 `embeddinggemma-300m-qat-q8_0`（`--embeddings`）；**`/v1/chat/completions → HTTP 400`** ⇒ **嵌入专用，非 chat** |
| `127.0.0.1:18789`（Gateway） | `/v1/models → 404`；`/api/models → 404`；根路径返回 Control UI HTML ⇒ **非 OpenAI API** |
| 其他端口（11434/1234/8000/8080/5000/3000/7860/8888/9090/4000/5001/8799/18790） | 均未监听 |

### d) OpenClaw 配置中的 provider baseUrl（仅 URL，未取密钥）
```
builtin-platform      https://openclaw-ai-gw.updrv.com/v1
custom-yuanyuaicloud-cn  https://yuanyuancloud.cn/v1   (原文: https://yuanyuaicloud.cn/v1)
deepseek              https://api.deepseek.com
llama-cpp             http://127.0.0.1:19432/v1   (嵌 入专用)
```
⇒ 远程 provider 均**需凭据**；本环境未持有，且**不采集/不打印**任何密钥（政策）。

## 2. 判定
- 任务要求 1「配置并验证当前可用的真实 LLM endpoint」：**验证结果为「无可用 chat 端点」**（上述证据）。
- 按硬边界：**`LLM_UNAVAILABLE` 明确标注**，禁止静默退化冒充真实 Agent → 已遵守。

## 3. 启用契约（不改 harness，仅注入端点）
```
V2_SHADOW_LLM_URL=<OpenAI-compatible base，如 https://api.deepseek.com/v1/chat/completions>
V2_SHADOW_LLM_KEY=<key>        # 仅经密管/环境注入；不入仓库、不打印
# model = deepseek/deepseek-v4-flash ; temperature=0 ; response_format=json_object
```
- 注入后重跑 `python shadow_three_way.py --limit 120 && python true_agent_outcomes.py` 即得真 LLM 侧。
- `TRUE_AGENT_DECISIONS.jsonl` 中该侧将由 `LLM_UNAVAILABLE` 变为真实决策，`agent_llm="OK"`，并写入 `prompt_hash/input_hash/decision_hash`。

## 4. 可审计性
- 每次调用保存：`prompt_hash`（system+user+model 规范化 hash）、`input_hash`（context_hash+候选）、`decision_hash`（decision/opportunity/reason/plan/regime 规范化 hash）。
- 未调用时同样记录 `LLM_UNAVAILABLE` + 原因（`V2_SHADOW_LLM_URL/KEY unset`），保证"未运行"也可审计。

---

## 5. 本轮“配置并验证真实 endpoint”的实测结果（2026-10-02T15:23Z）

按任务书执行“配置 → 单次连通性/模型验证”，逐一实测**全部候选端点**，结果如下（**均失败**）：

| # | 候选 | baseUrl | 结果 |
|---|---|---|---|
| 1 | 密管 `secrets list` | — | **store empty**（无任何已存凭据） |
| 2 | 环境变量扫描 | — | **无任何 LLM/API key 变量** |
| 3 | `custom-yuanyuaicloud-cn`（OpenClaw 已配置） | https://yuanyuaicloud.cn/v1 | **HTTP 401** `Invalid token`（key 已失效；key_len=51，未打印） |
| 4 | `builtin-platform`（OpenClaw 已配置） | https://openclaw-ai-gw.updrv.com/v1 | **HTTP 403** `insufficient_user_quota / no active subscription`（key_len=48，未打印） |
| 5 | `llama-cpp`（本地） | http://127.0.0.1:19432/v1 | 仅 **embeddings**（`embeddinggemma-300m-qat-q8_0`）；`/chat/completions → HTTP 400` |
| 6 | 其它本地端口 | — | 未监听 |

- 验证脚本：`llm_setup.py`（只打印 provider/baseUrl/models/key_len，**绝不打印 key 值**；单次 chat 调用做连通性/模型验证）。
- 端点裁决：**无可用 OpenAI-compatible chat 端点**。

### 判定与停止理由
- 任务书验收：“120/120 有真实 LLM decision；**否则停止并报告缺失**”。⇒ 本轮**按此停止**。
- 硬边界：“LLM 不可用时必须 `LLM_UNAVAILABLE`，禁止静默 fallback 冒充真实 LLM”。⇒ `true_llm_agent` 侧**全程 `LLM_UNAVAILABLE`**（120/120），**未**降级为 heuristic。
- 未向任何端点成功发送有效请求；**0 次真实 LLM 决策**（成功率 **0/120**）。

### 恢复路径（用户可一键启用）
1. 更新任一 provider 的 key（或充值 `builtin-platform` 订阅）；或
2. `set V2_SHADOW_LLM_URL=<OpenAI 兼容 /v1/chat/completions>` + `set V2_SHADOW_LLM_KEY=***`（经密管/环境）；可选 `V2_SHADOW_LLM_MODEL`。
3. 然后重跑：`python shadow_three_way.py --limit 120 && python true_agent_outcomes.py`（harness 零改动）。

### 安全声明
- key 仅**进程内**读取/使用，**未**写入仓库、日志、产物、会话或 SHA256SUMS；
- 本轮未产生任何真实订单（`order_send=0`）；V2 Production 零代码/参数/配置/ledger 变更。
