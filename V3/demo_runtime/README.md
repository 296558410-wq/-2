# V3 高频 Demo 交易机器与研究机器

tick 驱动、每秒决策，冻结的 30 秒周期实验策略，持续真实 Demo 成交与独立前向研究。主协议见 [PROTOCOL.md](PROTOCOL.md)。

## 组件

- `features.py`：可复现增量 L1 特征，不使用旧分钟线全样本波动分组。
- `train.py`：仅历史已污染开发数据，固定 Ridge 模型，输出全部五个周期诊断；正式测试窗口不读。
- `broker.py`：逐单核验 Demo 身份、隔离实例、账户/品种、手数、券商止损和保证金。
- `engine.py`：持久化意图、成交确认、持仓退出、未知结果处理、重启恢复、完整费用与对账。
- `research.py`：独立进程，延迟标签成熟后评估各周期，记录报价代理与随机方向控制。
- `dashboard.py`：中文只读面板，真实策略净盈亏与研究报价代理分别展示。
- `supervisor.py`：独立监督三个服务，交易进程异常后从账本恢复；系统级任务可在登录时启动。

## 使用

在当前目录，用 `C:\AIQuant\.venv\Scripts\python.exe`：

```powershell
python -m unittest discover -s tests -v
python -m demo_engine.train
python -m demo_engine.run --preflight
python -m demo_engine.run --observe-only --duration 90
```

训练一次后模型冻结；再次训练需新实验版本和独立运行目录。交易授权文件位于 `runtime/authorization.json`，绑定账号、协议、配置和模型哈希，记录用户明确指令。缺失、撤销、哈希不一致均禁止开仓。

运行 `start.ps1` 启动监督进程；打开 `http://127.0.0.1:8793/`。运行 `stop.ps1` 请求停止开仓并平掉本实验持仓，随后退出。`runtime/STOP` 是停机标志。停止时应查看面板确认空仓。

`autostart.ps1` 可用于登录后恢复监督进程，并尊重持久化 STOP 标志。安装登录启动项需要用户明确授权；当前运行的服务不依赖该启动项。OS 文件锁阻止重复交易实例。

## 输出与运行状态

- `runtime/status.json`：当前运行、报价年龄、每秒决策理由、持仓、风险和处理延迟。
- `runtime/strategy_ledger.jsonl`：耐久、哈希链接的策略订单与券商成交。真实净盈亏来自逐笔 broker deal 的 profit+commission+swap+fee。
- `runtime/forward/`：tick 与冻结模型预测的追加流。
- `runtime/research.json`：五周期成熟样本、净报价代理、随机控制、预测误差。
- `runtime/logs/`：各服务独立日志。
- `artifacts/model.json`：本地冻结模型，不上传 GitHub。
- `artifacts/development_diagnostics.json`：已污染开发样本诊断，不作为 OOS 或 Alpha 证明。

只有出现满足成本与置信余量的信号才开仓。运行正常且 WAIT 是合法状态，工程就绪不能替代策略价值验证。

MT5 接口依据：[order_send](https://www.mql5.com/en/docs/python_metatrader5/mt5ordersend_py)、[账户类型](https://www.mql5.com/en/docs/constants/environment_state/accountinformation)。FXTM Broker 时间偏移经独立 Demo 预检实测，并与原始 broker 时间一起保留。
