# V2_GRAND_ARCHITECTURE — 多策略智能交易研究系统（第一阶段）

只读 / Shadow 研究程序。**不接生产，不改 V2 生产行为，`order_send = 0`。**

## 复现

```powershell
cd C:\AIQuant\research\hermes\trader_v2\V2_GRAND_ARCHITECTURE
$env:PYTHONPATH = (Get-Location).Path
C:\AIQuant\.venv\Scripts\python.exe run_all.py
```

每个模块目录也可单独运行并打印 input hash / code commit / config hash：

- `strategy_factory/run_factory.py`
- `strategy_registry/run_registry.py`
- `strategy_brain/run_brain.py`
- `strategy_memory/run_memory.py`
- `evolution/run_evolution.py`
- `gpu_research/run_gpu.py`
- `opportunity_hub/run_hub.py`
- `intelligence/run_intelligence.py`

## 关键产物

- `FINAL_REPORT.md` — 最终报告 + 12 条验收回答 + 状态块
- `GPU_BENCHMARK.json` — 真机 GPU 实测（runtime / speedup / peak VRAM / utilization）
- `STRATEGY_REGISTRY.jsonl` / `CANDIDATE_REGISTRY.jsonl` / `EXPERIMENT_REGISTRY.jsonl`
- `DATA_MANIFEST.json` — 输入数据清单与哈希
- `RESEARCH_DASHBOARD.html` — 中文研究面板（本地打开，不接生产）
- `SHA256SUMS.txt` — 全产物校验

## 边界

见 `GRAND_ARCHITECTURE_BRIEF.md` 的 15 条硬边界。数据仅取本地 FXTM tick 归档；
V1/V3 零触碰；不自动推进到 production。
