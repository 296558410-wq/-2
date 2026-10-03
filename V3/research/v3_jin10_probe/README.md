# v3_jin10_probe — 金十数据 PIT 可行性只读探针

`READ ONLY` · 不含 order / trade / account / MT5 / broker 任何内容。

## 结论（2026-09-25T01:31:46.566249+00:00）

```text
JIN10 中国内网连通性 : PASS（www / flash / rili / mcp 均可直连，无 VPN/代理）
官方数据获取能力     : FAIL（页面为 SPA 空壳；官方 MCP 需 OAuth；flash-api 502）
最终判定             : JIN10_PIT_FAIL（可达但无法建立 PIT）
```

## 用法

```powershell
C:\AIQuant\.venv\Scripts\python.exe research\v3_jin10_probe\probe.py --connectivity
C:\AIQuant\.venv\Scripts\python.exe research\v3_jin10_probe\probe.py --inspect
```

## 凭据

探针**不需要**任何凭据。若将来获得合法 Token，只允许写入 `C:\AIQuant\.env.v3_jin10`，
由 `os.getenv("V3_JIN10_TOKEN")` 读取；**不得**写入 git / 报告 / JSON / 日志。
