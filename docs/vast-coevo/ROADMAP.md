# VAST-CoEvo v1.0 Research Roadmap

**Verification-Guided Adversarial Co-Evolution of Customer Exploration and Service Decision Skills**

暂定论文标题：*VAST-CoEvo: Verification-Guided Adversarial Co-Evolution of Customer Exploration and Service Decision Skills*。

本文是算法研究路线图。[原有 Benchmark 扩展路线图](../../audits/diversity-v1/ROADMAP.md)记录的是历史环境审计与业务扩展计划，保持原样；算法实现和验证状态以 [IMPLEMENTATION.md](IMPLEMENTATION.md) 为准。导航：[方法](METHOD.md) · [架构](ARCHITECTURE.md) · [Schema](SCHEMAS.md) · [实现与验收](IMPLEMENTATION.md)。

## 研究问题与科学假设

在基础模型权重完全冻结的条件下，开放式 Customer Agent 能否自主探索有状态业务世界，发现独立 Oracle 可验证的 Service 决策错误，并形成可复用 Exploration Skills？Service Agent 能否从真实失败证据形成 Decision Skills，改善决策正确性并维持合法任务完成能力？双方交替更新是否具有持续适应性与跨业务泛化优势？

| 假设 | 需要检验的主张 | 当前科学状态 |
| --- | --- | --- |
| H1 — Customer Skill Generalization | 历史探索经验形成的 Skills 在未见世界中发现更多独立、真实、可验证业务错误 | **未证明** |
| H2 — Service Skill Generalization | 由验证失败形成的 Skills 在未见情境中改善决策正确性，同时保持合法业务完成能力 | **未证明** |
| H3 — Alternating Co-Evolution | 交替更新比 Customer-only、Service-only 和静态 Skills 产生更好的联合表现 | **未证明** |

工程测试、确定性客户端演示、开发集接受候选和真实模型 Pilot，均不能单独证明 H1/H2/H3。

## 已锁定的方法

Customer 更新模块化 Exploration Skills；Service 更新带业务决策契约的 Decision Skills。Skill 是声明式数据，供模型在合法观察和工具权限范围内使用，不执行任意模型生成代码。模型配置和参数冻结，世界状态只通过现有真实 Engine/Tools 转移，失败由独立 Oracle 判定。

每次更新最多一次 Reflection、一个 `ADD / UPDATE / REMOVE / NOOP` Patch、一个候选 Library。静态检查后通过真实环境动态验证，接受或保留旧版；格式错误、验证失败也消耗本次更新机会，不自动重新提示。每代 Customer 先更新，Service 后更新。禁止 SFT/DPO/RL、权重更新、多候选遗传搜索、树搜索、向正式 Agent 暴露隐藏 Oracle，以及修改 Reference Rules 或冻结 Benchmark 来提高分数。

## 三层边界与 Skill 定义

Usami 保留 SaaS、CloudOps、FulfillmentOps、StayOps 的世界生成、状态、Engine、Tools、Reference Rules、Oracle、Customer/Service Session、Manifest、Trace、Replay 与 Benchmark 评分。它不负责 Skill 进化。

独立 `vast_coevo/` Core 负责通用 Schema、Library、检索、渲染、版本、Reflector、Evolver、验证门槛、Rollback、Controller 与算法证据记录。Core 通过 Protocol 使用环境能力，不导入 Usami 领域对象。`integrations/usami/` 承担 Session 配置、权限过滤、真实请求注入、领域事件解释、回放和回归；增加另一环境不要求改写 Evolver。

Customer Skill 描述触发条件、探索假设、观察与请求选择方法、反馈记录方式和停止条件。它不能包含固定任务/Witness 脚本，也不能替模型预先决定精确写操作。Service Skill 描述触发条件、前置条件、决策过程、后置条件和恢复方式。它不能直接改写世界、创造授权或将 Oracle 变成额外工具。

Service 目标是减少业务决策违规并正确完成合法请求。拒绝率本身不是优化目标。接受候选必须同时检查已知失败、新增违规、正常任务完成、正确拒绝及授权边界。

## 交替更新与可回放证据

设 `C_g = frozen Customer model + customer library_g`，`S_g = frozen Service model + service library_g`。一代依次执行：

1. 用 `C_g × S_g` 进行开放探索，收集实际轨迹与 Oracle Evidence。
2. 固定 `S_g`，对 Customer 做一次 Reflection，形成唯一候选，静态与动态验证后选定 Customer。
3. 用选定 Customer 与 `S_g` 再次探索，收集 Service 更新依据。
4. 固定选定 Customer，对 Service 做一次 Reflection，执行已知失败及合法任务回归，接受或回滚。
5. 支持 `C_g × S_g`、选定 `C_{g+1} × S_g`、`C_g × S_{g+1}`、`C_{g+1} × S_{g+1}` 交叉执行，记录实际 Snapshot，而不是假定每次更新都产生新版。
6. 保存代际检查点、所有提出和拒绝的 Patch、模型请求/响应、预算和终止状态后进入下一代。

通用证据必须保留真实操作、执行前事实、期望/实际结果、Oracle 错误码、授权事实、Skill Snapshot、模型配置、初始世界 hash、完整模型请求及 Replay 结果。分别统计成功业务违规、被拒绝非法尝试、仅授权异常、错误拒绝、合法执行、未评分事件，不压缩成一个 `failure=True`。

每个 Library 是不可变内容寻址快照；已发布 Skill ID/Version 不静默覆盖。候选拒绝时已接受指针不动，所有历史 Snapshot 可恢复。失败 archive 保留原始事件数和规范化指纹去重后的失败类型数。ID 与金额归一化不能丢掉容量、权限和因果关系；无法可靠解析的因果前态明确记为待确认，不宣称完整语义去重。

## 实施阶段与当前状态

| 阶段 | 交付要求 | 状态依据 |
| --- | --- | --- |
| M1 Inspect + Roadmap | 本地 RSI 身份、Git、四域接口和历史兼容约束核对；写入定稿方法 | 本文及 [ARCHITECTURE.md](ARCHITECTURE.md)；验收见实现报告 |
| M2 Independent Core | Schema、声明式 Skills、不可变 Library、检索/渲染、版本和独立测试 | [IMPLEMENTATION.md](IMPLEMENTATION.md) 的实际模块与命令 |
| M3 Usami Integration | 四域真实 Session、双 Agent 请求注入、Oracle 转换、Replay | 必须逐域记录真实 Engine 测试；录制客户端单独标明 |
| M4 Evolvers | 双 Reflector、一次 Patch、静态和动态验证、接受与拒绝 | 更新失败必须保存原因和旧版本 |
| M5 Controller | 两代以上、恢复、NOOP、回滚、交叉运行、回归、真实 LLM gate | 根据实际输出填写，未执行项不得标为通过 |

实现期间状态记录可能更新；本路线图不将目标模块的存在视为工程验收。Live LLM 不可用时保存具体阻塞原因，确定性客户端运行只能证明机制与真实业务执行路径。

## 后续 Held-out Evaluation

预先冻结开发/验证/正式测试分区、世界/身份/预算、模型与采样配置、Skill 版本、工具与 Oracle 版本，以及候选接受规则。正式测试 Evidence 不进入 Reflection、候选选择、去重规则调参或回归集。公开 Demo 不作为盲测。

世界留出之外，还需按业务关系模板、决策条件及状态依赖组合留出；跨域实验分别报告单域迁移与组合迁移。报告原始违规与独立失败类型、合法任务完成、错误拒绝、授权异常、执行错误、调用成本、Replay 通过率、多 Seed 方差/置信区间。保持 Customer-only、Service-only、静态 Skills 与交替更新的模型、世界和总调用预算可比。

用跨代矩阵观察旧 Customer 对新 Service、旧 Service 对新 Customer 与联合版本的表现，诊断遗忘、对当前对手过拟合及重复失败饱和。完成这些设计与实测前，H1/H2/H3 仍是待检验假设。

## 相关工作与创新边界

以下关联基于论文与作者项目的一手来源，核查于 2026-10-14。名称存在歧义时列出标题和 arXiv ID；不把同名论文混作一项。

| 工作 | 已有方法及与本研究的关系 | 一手来源 |
| --- | --- | --- |
| GEPA | 从执行轨迹进行语言反思和 Prompt 更新，采用 Pareto 候选选择。反思驱动文本优化已有先例；VAST-CoEvo 锁定单次单候选，不复刻其搜索策略 | [论文 2507.19457](https://arxiv.org/abs/2507.19457) · [官方代码](https://github.com/gepa-ai/gepa) |
| ACE | 通过生成、反思与整理增量更新上下文 playbook。模块化上下文维护及避免全量覆盖已有先例 | [论文 2510.04618](https://arxiv.org/abs/2510.04618) · [作者项目](https://ace-agent.github.io/) |
| Trace2Skill | 从多个执行轨迹并行提炼局部经验，再合并为可迁移声明式 Skills。轨迹到 Skill、冻结模型和 Skill 迁移已有先例 | [Distill Trajectory-Local Lessons, 2603.25158](https://arxiv.org/abs/2603.25158) · [官方代码](https://github.com/Qwen-Applications/Trace2Skill) |
| ContractSkill | 明确过程结构、确定性验证、错误定位和局部修复；其公开论文将迁移证据限定于相同 Benchmark 家族。前后条件与可修复 Skill 不能宣称为本研究首创 | [论文 2603.20340v3](https://arxiv.org/abs/2603.20340v3) |
| CoEvoSkills | Skill Generator 与 Surrogate Verifier 共进化，构造多文件 Skill 包，并隔离受保护测试答案。VAST-CoEvo 的演化双方是业务 Customer/Service，独立业务 Oracle 固定 | [论文 2604.01687v3](https://arxiv.org/abs/2604.01687v3) · [官方代码](https://github.com/Zhang-Henry/CoEvoSkills) |
| SkillWeaver | Web Agent 自主探索、练习和完善可复用 API Skills。开放探索与可迁移技能已有先例；本项目 Skill 为声明式指导，不运行自动生成 Python | [Web Agents…, 2504.07079](https://arxiv.org/abs/2504.07079) · [作者项目](https://osu-nlp-group.github.io/SkillWeaver/) |
| MAGIC | 多轮攻击者/防御者对抗共进化，采用多 Agent RL。双方对抗学习已有先例；本项目冻结权重，判据是实际业务执行的独立证据 | [A Co-Evolving Attacker–Defender…, 2602.01539](https://arxiv.org/abs/2602.01539) · [作者项目](https://yingwen.io/en/publications/magic-a-co-evolving-attacker-defender-adversarial-game-for-robust-llm-safety/) |
| Agent0 | 工具增强的课程/执行 Agent 共进化，通过 RL 更新模型。自动课程与双边更新已有先例；本项目演化结构化 Skills，业务环境和 Oracle 不随双方更新 | [论文 2511.16043](https://arxiv.org/abs/2511.16043) · [官方代码](https://github.com/aiming-lab/Agent0) |

另一个 [Trace2Skill: Verifier-Guided Skill Evolution for Long-Context EDA Agents, 2605.21810](https://arxiv.org/abs/2605.21810) 研究硬件 Agent 的 verifier-guided Skill 演化，与上表的轨迹蒸馏工作不同。SkillWeaver 和 MAGIC 也有其他领域的同名工作；上表只比较明确链接的 Web Skills 与安全共进化论文。这里的相似性/差异是方法层面的分析，不能据此断言所有前人都未研究过某种组合。

潜在研究差异是：**开放式、可执行业务探索产生独立可验证失败，驱动 Customer 探索 Skills 与 Service 决策 Skills 交替演化，并联合约束违规降低、合法完成与授权安全。** Prompt 优化、轨迹提炼、Skill 修复、版本回滚或双 Agent 共进化本身均不作为独创贡献。该组合能否产生泛化优势，必须由上述预算匹配、隔离测试和消融实验检验。
