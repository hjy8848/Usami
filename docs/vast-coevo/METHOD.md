# VAST-CoEvo 方法与实验协议

当前默认训练为 [RunConfig v3 单链递归协议](RECURSIVE_TRAINING.md)：移除训练中的 selected 比较探索和四组 cross；交叉评估为独立只读入口。历史协议/实验保留原解释，Skill/Reflection/Service Gate 不变。

> 当前选择机制已更新为 [Customer Static-Only Selection](CUSTOMER_STATIC_ONLY.md)。下文中的 Customer 性能 Gate 是历史机制或显式诊断，不能决定当前 Customer 版本。Service 动态验收保持原样；历史结果不改判。


[路线图](ROADMAP.md) · [架构](ARCHITECTURE.md) · [Schema](SCHEMAS.md) · [实现与验收](IMPLEMENTATION.md)

## 状态与目标

Agent 由冻结基础模型、固定模型配置和指定 Skill Library Snapshot 组成。版本更新只改变声明式 Skill 内容，不修改模型权重、业务规则、Oracle、授权控制器或固定测试世界。

Customer 进行无固定任务的自主探索，从合法可见状态和 Service 实际回复决定查询、精确写意图、探索方向与停止。它的开发阶段指标包括有效动作、执行错误、原始成功违规及独立失败类型；被拒绝的非法尝试不能当作成功发现。Service 根据业务信息、Customer 意图及真实工具反馈完成合法业务、正确拒绝非法请求、缺授权时澄清、工具失败时恢复，不以更高拒绝率为目标。

H1（探索泛化）、H2（决策泛化）和 H3（交替更新优势）都未得到正式实验证明。一个候选被开发集接受，仅说明满足当时预先配置的门槛。

## Skill Runtime

Customer Exploration Skill 包含领域、触发条件、探索假设、探索过程、反馈方法、停止条件。Service Decision Skill 包含领域、触发条件、前置条件、过程、后置条件、恢复策略。字段及示例见 [SCHEMAS.md](SCHEMAS.md)。世界具体 ID 可以存在于原始轨迹中，但不应成为可复用 Skill 的核心条件。

Retriever 只读取 Agent 当前合法观察，按领域、触发和稳定排序确定性选择，限制 Skill 数量与上下文预算；无匹配时沿用基础 Agent。Renderer 将完整结构化 Skill 渲染成有明确边界的指导块，在正式模型请求前注入，并记录命中的 Skill ID/Version、Snapshot hash 和最终实际请求。Skills 不改变工具清单、Customer 意图 Schema、身份、授权生命周期或信息可见性。

反思能够使用开发阶段经独立 Oracle 验证的失败。正式执行 Agent 仍不可调用 Oracle 或得到隐藏答案。合法公开业务政策与运行后研究反馈必须在数据来源上区分。

## 每次更新只有一次 Reflection

对于角色 `r` 和已接受 Library `L`：

1. 固定开发反馈、当前 Library、预算与冻结反思模型配置，保存 Reflection 输入及将发送的请求。
2. 标记该更新的反思机会已消耗，再调用一次配置的模型客户端；保存完整响应或错误。
3. 严格解析唯一 `SkillPatch`。数组、多 Patch、格式错误、未知字段、权限越界或无效版本导致拒绝，不能重新提示。
4. `NOOP` 保持原快照。其他合法 Patch 只形成一个候选 `L'`，候选不替换当前已接受指针。
5. 执行不依赖 LLM 的静态门槛，再经 Environment Adapter 做动态验证。
6. 根据冻结验收规则接受 `L'` 或保持 `L`，记录原因、候选和实际选中版本。

失败后的新一轮反思只能属于一个明确的新更新/新代，不能作为同一更新的重试。持久化检查点必须防止重启后再次调用已完成的 Reflection。若调用已发出而结果未落盘，应记录不确定终止，不能声称恰好一次请求已得到有效结果。

`ADD` 产生新 Skill ID；`UPDATE` 引用存在的 Skill 并递增其版本；`REMOVE` 删除候选快照中的存在 Skill；`NOOP` 不创建虚构演化版本。所有旧快照可恢复，拒绝候选的证据和成本仍保留。Service 缺乏可用验证失败时应合理 NOOP，不编造修复依据。

## Customer-first / Service-second

| 阶段 | 固定对象 | 执行与输出 |
| --- | --- | --- |
| A 当前探索 | `C_g`, `S_g` | 开放多轮 Episode 与 Oracle Evidence |
| B Customer 更新 | `S_g` | Customer 单次反思；唯一候选；静态/动态验收；选定 `C*` |
| C 更新后探索 | `C*`, `S_g` | 新真实 Episode；新增或重复失败进入 archive |
| D Service 更新 | `C*` | Service 单次反思；唯一候选；已知失败、合法任务与授权回归；选定 `S*` |
| E 交叉执行 | 确定版本 | `C_g×S_g`, `C*×S_g`, `C_g×S*`, `C*×S*`；实际 Snapshot 可相同 |
| F 下一代 | `C*`, `S*` | 保存代际选择、预算与状态，成为下一代父版本 |

开发验证比较必须固定世界、身份、工具、预算、模型配置和相对角色版本。正式测试 Evidence 不进入反思或候选选择。交叉运行需标明是开发诊断还是最终 Held-out 评估，不能让后者影响后续训练流程。

## 两级候选验证

静态门槛检查 Schema、角色/类型一致、Scope/Trigger、ID/Version、Patch 引用、重复 ID、允许工具、权限声明、代码注入与授权越界。静态拒绝不调用动态验证、不污染已接受版本。此门槛是确定性防护，不能声称可从任意自然语言中完美检测语义恶意指令。

Customer 动态门槛用同一冻结 Service 和同一组开发世界对比父版与候选，检查真实动作、工具错误及验证发现；规则在运行前配置。Service 动态门槛覆盖已知失败、合法直接完成、多步骤合法任务、正确拒绝、缺授权澄清和失败恢复，分别报告违规、完成、拒绝与授权指标。不能用 Mock 宣称业务修复；Core Mock Tests 只证明控制逻辑。

候选拒绝即保留旧快照，仍持久化所有静态/动态结果、成本和拒绝原因。开发规则可采用简单确定性阈值；小规模或有限场景通过不等于普遍正确。

## 失败证据与指纹

`successful_business_violation` 要求实际执行成功且独立 Oracle 判定业务违规。`rejected_invalid_attempt`、`authorization_only`、`false_rejection`、`legal_execution` 与 `unscored` 单独记录。同一事件既包含业务与授权问题时保留 Oracle 的完整 violations，主分类仍服从原环境分类，避免另造一套裁判。

失败指纹使用领域、规则错误码、操作、相关执行前事实、权限范围、因果前提和期望/实际关系。归一化应消除无关实例 ID，同时保留影响业务判断的关系：满容量 10/10 后添加第 11 人，与 20/20 后添加第 21 人可归为同类；不同规则或因果路径不能因操作同名而合并。v1 指纹是明确算法下的保守归并，不是语义唯一性证明。原始全轨迹保留，未来可重新归并。

Replay 不调用在线模型：用保存的实际请求/响应重建模型交互，复用真实 Engine/Oracle 回放工具轨迹，核验初始世界、内容 hash、身份、Skill 内容、请求与事件顺序、最终状态和 Oracle 结果。请求注入后必须核对新请求，不能沿用注入前的旧 hash。

## 研究评测准备

正式实验冻结 Split 与结构组合、Snapshot、模型/采样配置、预算、环境与 Oracle 版本、候选门槛和失败归并算法。至少比较静态、Customer-only、Service-only 与交替更新；多 Seed，匹配总调用成本，报告持续适应与合法任务回归。隔离 Test World/Composition，并防止 Test Evidence 进入反思、验证或提示调参。

工程验收分别回答：机制能否执行和恢复、真实 Engine/Oracle 是否正确接入、开发规则是否接受候选、是否有新真实 LLM 调用。未来科学验收才回答：H1/H2/H3 是否成立。未开展大规模 Held-out 评估不是本次机制实现的失败。
