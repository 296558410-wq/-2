# V3_GPU_INFRA — 状态报告（计算基础设施，无任何交易结论）

- 位置：`research/hermes/trader_v3/gpu_infra/`
- 边界遵守（任务书 GPU 段）：**只建设基础设施**；无新 Alpha Sweep、无新假设、无参数寻优、无信号生成、无 DEMO/LIVE。自检全部使用**合成数据**。
- 判定：**`GPU_INFRA_BUILT`（自检 8/8 PASS）**

## 1. 设备

| 项 | 值 |
|---|---|
| GPU | NVIDIA RTX A2000 Laptop GPU（capability 8.6） |
| VRAM | 4095.6 MiB 总 / 3290 MiB 空闲 |
| 栈 | torch 2.14.0+cu126 · CUDA 12.6 |

## 2. 构件

| 文件 | 内容 |
|---|---|
| `v3_gpu_lib.py` | R4 语义核（sign-flip permutation / block bootstrap，CPU 参考实现 + GPU 分块实现）；**OOM 回退**（减半 chunk → 最终 CPU）；**4GB VRAM 字节预算分块**；向量化 tick 特征（spread/ret/滚动 |ret|，batch 模式） |
| `run_gpu_selftest.py` | 合成数据自检 + benchmark（写 `GPU_SELFTEST_RESULTS.json`） |

## 3. 自检结果（8/8 PASS）

| 测试 | 结果 |
|---|---|
| CPU/GPU 精确一致性（同一符号矩阵） | PASS（0.5107446276861569 两者相同） |
| 分块累积不变性 | PASS（chunked == full，逐位相同） |
| 同种子可复现性（GPU 两次） | PASS |
| **OOM 回退**（注入合成 OOM → 自动降 chunk 重试） | PASS（恢复后与参考解一致） |
| 极小 chunk=1 路径可运行 | PASS |
| VRAM 无泄漏（3276→3278 MiB） | PASS |
| tick 特征 CPU/GPU 一致性（500k ticks） | PASS（max|diff| 7.03e-18） |
| 4 路 batch 处理 == 单次全量 | PASS |

## 4. Benchmark（合成数据，如实报告）

| 核 | CPU | GPU | 结论 |
|---|---|---|---|
| sign-flip permutation（reps=4000, n=1000） | 0.088 s | **0.026 s** | GPU **3.4×** |
| block bootstrap（reps=2000, nblocks=50, n=1000） | **0.009 s** | 0.087 s | 此规模下 CPU 更快（GPU 启动/索引开销占优） |

**使用指引（诚实）**：permutation 在高 reps 时用 GPU；小规模 bootstrap 用 CPU；GPU 收益随 n/reps 规模增长（本轮未做大规模压测，属未验证项）。

## 5. 复用方式与限制

- 任何后续冻结协议若需要 bootstrap/permutation，可直接 `import v3_gpu_lib`（结果与 R4 统计口径同定义，仅执行设备不同）。
- **不授权任何交易用途**；GPU infra 不产生方向、不生成信号、不连接 MT5。
- 未验证项：多 GPU、>4GB 数据单次驻留、mixed precision（均不需要，未做）。
