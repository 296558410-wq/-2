# 06_LLM_HERMES_AUDIT — LLM 与 Hermes 审计（2026-09-06）
## LLM（本系统=OpenClaw runtime）
- 实际职责: 控制器/研究者/审计者/文档者; **从未作为信号源**(正确)。
- 测试证据: deterministic rules/随机对照在一切地方都解释了结果; LLM 若被用于"生成候选"会变成工厂(宪章 §32 已禁)。
- 判定: **保留为控制器与解释器, 权限不变; 永不加为预测组件**。价值 = 跨证据综合与对抗审稿(本审计即例); 复杂度代价低。
- 弱项: 单次会话记忆有限 → 靠文件继承; 已用文件化治理弥补(有效)。
## Hermes
- 本日真实贡献(诚实盘点): 10-13 轮中 **2 个 material**: (a) HERMES-13 equity→gold 转嫁质疑(催生 Gold Options 任务, 结构性发现成立), (b) HERMES-12 免费/低价数据考古(GC/GVZ 路径, 催生 ACCESS/ZERO-BUDGET 任务)。其余多轮为 CONFIRM/REFINE(有用但低边际), 存在重复搜索与理论堆积。
- 问题: 触发过宽(自主连发多轮)、无 STOP 条件、web_search 不可用时考古能力减半。
- 重新定义 TRIGGER(仅当): 1) 出现 material 矛盾(本地证据与文献/架构冲突); 2) 特定数据解锁前的定向考古(EXISTS/ACCESSIBLE/AUTOMATABLE 验证); 3) 幸存候选的对抗外部审稿(ATTACK 模式)。STOP: 无 material 输出即停; 单任务 ≤1-2 精确问题; 禁止广谱搜索。
- 降权建议: 从"常驻情报层"改为"按触发调用"(已在宪章 spirit 内, 建议明文)。
## 分工终态
Hermes = 按需对抗情报(精确问题); LLM(本机) = 控制器/综合/审计; 一切计算 = 确定性代码; 概率/EV 语言 = 数学, 非叙述。
