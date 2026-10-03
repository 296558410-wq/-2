# 05_EXECUTION_AUDIT — 执行审计（2026-09-06）
## 核心自问: "信号"与"执行"是否被分得太死? —— 是。
证据: MTF Lab 管理对比(V0-V3)证明在无信号时执行管理只能搬运 drift; 但反向问题从未被检验: **当执行成本本身高度时变时, WAIT/ENTER/CANCEL 的 EV 可能独立于方向信号而存在**。我们在零售报价口径上测过(上界 0.1bps<1.7bps 成本 → 死), 但:
1. 该上界是"报价 spread"口径; 真实可交易成本含 last-look/拒单/排队, 其**时变性结构**(何时拒单率高/何时排队深)从未被观测——因为无执行通道;
2. 若通道成本降至 ECN 级(~0.3-0.6bps), 0.1bps 上界仍不够, 但差距从 17× 缩到 3-6×——值得重测, 而非维持"0.1bps=永久死"。
## 结论
- "无法稳定成交的信号不是 MONEY" —— 正确, 维持。
- "弱信号 × 执行时变 = EV 变化" —— 理论成立, 本地不可测(无通道); 标记 EXECUTION_GATE 而非 DEAD。
- 修正建议: 把 Execution Alpha 从"下游成本层"提为"一等研究对象的候选", 触发条件 = 任一免费/低价通道(MT5 demo 或 ECN demo)到位后, 预注册测量 spread/slippage/fill 的**时变结构**, 再决定是否值得作为对象。
## Signal×Execution 关系重定义
EV(signal, t) = P(fill | t, state) × E[payoff | fill, state] − P(reject)×cost(reject) − spread(t) − slippage(t)
当 spread/slippage/fill 存在可预测时变 → 执行本身是 EV 项, 不是常数扣除项。此为 08 的机制基础。
