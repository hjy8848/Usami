# Frozen-World 最终离线覆盖审计

- seed：42、43、44；原生生成器，未编辑世界。
- 登记世界 3，有效业务结构 **1**。
- 333 次有界模板尝试，294 个有证明实例；去重后 15 种任务结构、50 种语义。
- 339 个 Reference 搜索节点、438 次原生证明操作；模型调用 **0**。
- `world-pool.json`：完整世界、生成器 Hash、配置、分区与结构签名。
- `world-pool-audit.json`：角色、操作、状态、拒绝码、多步路径与构造缺口。
- `coverage-gaps.json`：未覆盖原生写操作及去重结果，绑定原审计 Hash。
- `audit-source-pins.json`：独立核验用的完整源码 Hash。

这是软件覆盖审计，不是新 Benchmark，不是 Service 错误发现实验。现有生成器 seed 主要改变名称，不能支撑跨业务结构泛化声明。完整方法及限制见 `docs/vast-coevo/FROZEN_TASK_DISCOVERY.md`。

最终全量回归：**1037 项通过，457.19 秒**；原始终端输出见 `full-regression.log`。包含真实业务引擎参与的脚本化模型测试，不代表真实模型效果。
