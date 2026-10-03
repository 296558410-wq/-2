# automation — 长期研究任务自动化设计

目标：以后跑几小时/几天的研究任务，不因单任务失败丢失全部结果。

## 设计原则

1. **日志**：每任务独立日志 `logs/<experiment_id>.log`
2. **checkpoint**：任务按阶段持久化中间结果（parquet/json），重启后从断点续跑
3. **deterministic seed**：seed 由 experiment_id 派生或显式传入，全链路固定
4. **failure recovery**：子任务失败标记 SKIP/FAIL，不中断整体；重跑只补失败段
5. **resumable task**：每个任务幂等（输出带版本，重复运行覆盖自身）
6. **元数据**：experiment_id / timestamp(UTC) / machine info / git commit hash / 参数快照

## 标准任务结构（模板）

```text
experiments/<exp_id>/
├── meta.json          # id/时间/机器/commit/seed/参数
├── params.yaml        # 参数（入 Git 用 configs/ 模板）
├── checkpoint/        # 中间状态（可续跑）
├── outputs/           # 最终产物
└── logs/              # 运行日志
```

## 运行器契约（第一版，见 task_runner.py）

```python
run_experiment(name, fn, params, seed, data_manifest) -> exp_dir
```

- 写入 meta.json（含 machine snapshot 与 git commit）
- fn 内部分段 checkpoint（parquet/json）
- 失败重试 ≤3 次；仍失败 → 记录原因并继续队列下一任务

## 未来集成

- mlflow 记录每个实验 run（本地 sqlite）
- 每日 cron 驱动的批量研究队列（OpenClaw 编排）
- 与 research_engine（CPU/GPU 后端）统一

## 当前状态

- 目录与设计：✅
- task_runner.py：v0.1 骨架（见文件）
- 真实长任务：研究阶段启动后接入
