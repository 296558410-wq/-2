# AIQuant 研究环境规范 (environment.md)

> 更新：2026-09-03（工作站 V1 任务）

## 1. Python 双轨制

| 环境 | 版本 | 路径 | 用途 | 原则 |
|---|---|---|---|---|
| 系统 Python | 3.14.7 | C:\Users\surface\AppData\Local\Programs\Python\Python314 | **仅 OpenClaw 运行时** | 不动、不装量化包 |
| 研究 venv | **3.12.x** | **C:\AIQuant\.venv** | 一切 AI Quant 工作 | 默认解释器 |

创建/进入：
```powershell
# 创建（安装 3.12 后执行一次）
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv C:\AIQuant\.venv
# 使用（每次）
C:\AIQuant\.venv\Scripts\python.exe  # 或 activate: C:\AIQuant\.venv\Scripts\Activate.ps1
```

为什么 3.12：numpy 2.5/scipy 1.18 要求 ≥3.12；sktime/vectorbt/nautilus 等 <3.15；
numba/cupy 等科学计算生态对最新版 Python 支持滞后。3.12 是当前唯一全兼容点。

## 2. pip 镜像策略（已批准）

- venv 内 `pip.ini` 指向**清华 TUNA**（官方机构维护的 PyPI 镜像）：
  `index-url = https://pypi.tuna.tsinghua.edu.cn/simple`
- 不修改 Windows 全局 pip/网络配置；不使用第三方代理软件
- torch 大轮子 TUNA 缺失/超时 → 回退官方 PyPI
- 记录：任何额外镜像须登记 原始源/镜像源/可信度/获取方式

## 3. 依赖锁定（可复现）

| 文件 | 内容 | 维护 |
|---|---|---|
| environment/requirements.in | 顶层直接依赖（人工） | 增删包时更新 |
| environment/requirements.txt | pip freeze 全量锁定 | 安装/升级后重新生成 |
| environment/install.log | 安装过程日志 | 每次安装追加 |
| environment/environment.md | 本文件 | 变化时更新 |

重建环境 = `python -m venv` 重来 + `pip install -r requirements.txt`（锁定）。

## 4. 可复现五元组（每个实验必须记录）

1. 代码版本：git commit hash
2. 依赖版本：requirements.txt + Python 版本
3. 数据版本：输入文件 manifest（路径+大小+SHA256）
4. 硬件：tools/snapshot_env.py 输出（GPU/驱动/CUDA/torch）
5. 随机性：seed（random/numpy/torch 三件套）+ 参数文件

## 5. 已批准软件栈分类（详见 docs/software_stack.md）

- CORE：numpy pandas scipy numba pyarrow polars duckdb statsmodels arch
  scikit-learn xgboost lightgbm torch pandera mlflow hydra-core matplotlib pytest
  vectorbt backtesting
- OPTIONAL：nautilus_trader arcticdb MetaTrader5 cupy quantstats statsforecast dvc
- REJECT：backtrader zipline great-expectations mlfinlab 等（见 software_stack.md）

## 6. Windows VC++ 运行库修复（torch 2.14+cu126 必需，2026-09-04）

**症状**：`import torch` → `OSError: [WinError 1114] ... c10.dll` / `[WinError 126] ... torch_cpu.dll`

**根因**：2026 版 torch 轮子需要较新的 MSVC 运行库卫星 DLL（`vcruntime140_threads.dll` 等），
本机 System32 仅有过旧的 msvcp140 14.36，且系统从未安装过 VC++ 2015-2022 Redistributable。

**修复（免管理员、不改系统）**：把官方 VC 运行库 DLL 复制到 **Python312 目录**（应用目录优先于 System32 加载）：
```powershell
$dst = "$env:LOCALAPPDATA\Programs\Python\Python312"
# 来源：官方 vc_redist.x64.exe (aka.ms/vs/17/release) 解包出的 amd64 CRT (14.44.35211)
# 备份位于 C:\AIQuant\cache\vcredist\y_a12\（vc_redist.x64.exe 也在 cache\vcredist\）
# 文件：msvcp140(+_1/_2/_atomic_wait/_codecvt_ids).dll vcruntime140(+_1/_threads).dll concrt140.dll
```
**复发处理**：若 Python312 升级后被清掉，从 `C:\AIQuant\cache\vcredist\y_a12\` 重新复制。
**根治选项（需管理员，可选）**：安装官方 VC++ Redistributable（winget Microsoft.VCRedist.2015-2022.*）

## 7. 环境变更纪律

- 每次安装记录到 install.log（时间/命令/结果/版本）
- 环境级故障恢复：删除 .venv 重建（不触碰系统 Python）
- 禁止：修改系统 Python、修改全局 PATH 不可逆项、安装 CUDA Toolkit（未经批准）
