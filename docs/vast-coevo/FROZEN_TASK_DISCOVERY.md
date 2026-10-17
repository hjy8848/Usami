# Frozen-World Task Discovery v1

本协议的出题对象是**业务任务**，不是世界初始状态。协议标识为 `frozen-task-discovery-v1`；历史 `designer-service-v1` 的 SceneEdit 路径保留，但不用于本协议。

## 职责与执行顺序

```text
独立 Generator + 冻结 seed/config
    → 登记 World Pool / Hash / 来源 / 分区
    → 独立覆盖审计（不调用模型）
    → 在原世界上证明 bootstrap 任务
    → 实际执行，获得正确/错误开发证据
    → Designer 选世界、既有身份、实体关系、操作集合和目标
    → Task Composer 用原 Reference / Engine 证明并冻结任务
    → 固定普通 Customer ↔ Service，多轮真实对话
    → 原业务 Oracle + 任务级决策核验 + 完整 Replay
    → Designer Reflection / Static / 配对 Dynamic Gate
    → 原 Service Reflection / Static / Dynamic Gate
    → 保存实际选中 D/S，固定 C，进入下一代
```

世界在首次模型调用前独立生成。每个 Episode 从所选世界的原始 Hash 建立独立副本；Service 通过实际业务操作造成的变化保存在该次执行中，不写回世界池。生成器不读取 Service 结果或 Designer 策略。

## Designer 没有 World Editing 权限

`TaskProposal` 只接受 `world_id/world_hash`、真实 `identity`、可选 `source_evidence`、搜索分支、假设、`task_spec`、`candidate_operations` 和普通 `customer_brief`。

- Schema 禁止额外字段：`world`、`edits`、`expected_before`、`witness` 等会被拒绝。
- `WorldPool.load()` 对照登记时的内容封印；原始世界被修改，直接报完整性错误。
- Composer 只能从池中取世界，不接受 Designer 提供的世界。证明前后复核世界 Hash 与完整内容一致。
- 身份、目标、操作引用及最终目标必须对应既有、合法可见的对象；权限仍由原 Reference 决定。
- 允许 Service 按顾客明确请求，通过 `grant_project_access` 等原生工具合法配置权限；这与执行前篡改权限不同。
- 无可靠路径或拒绝证明则记录构造失败，不补权限、不自动修复账单、不捏造 witness。

旧 Compiler 没有删除。新路径的测试将 `CloudOpsCompiler.compile()` 替换为直接抛错，完整训练与 Replay 仍能通过，验证它没有被暗中调用。

## 一个世界可以组合哪些任务

同一原生 CloudOps 世界中可选择不同现有用户、项目、实例、账单及权限关系：

| 示例 | 初始条件与证明 |
| --- | --- |
| 管理员启动数据库 | 使用已有 Admin 身份，单步完成 |
| Viewer 请求启动同一数据库 | 使用已有 Viewer，证明应拒绝；不改变管理员角色 |
| 启动数据库与依赖它的应用 | 搜索数据库 → 应用的合法路径 |
| 将完整三层服务上线 | 合法扩容配额，再处理依赖启动，通常 4 步 |
| 恢复暂停项目 | 原世界本来暂停且未支付；Owner 经实际工具配置自身项目权限、付款、恢复并启动 |
| 同时启动两个项目的数据库 | 原世界的跨项目目标组合，证明存在不同合法顺序 |
| 删除资源或调整依赖 | 仅在原生前置条件满足时执行，否则证明真实拒绝 |

任务索引只是有限提示与审计样本。Designer 不必从索引中选择固定题目，可以提交新的目标、操作集合和跨实体组合。离线测试额外构造了索引之外的跨项目任务，并通过原引擎证明两种执行顺序。

Composer 复用 `usami_cloudops/goals.py` 的 `Goal`、`reachability()`、`certify()`，**不调用会条件化世界的 `make_task()`**。当前搜索上限为 512 节点、6 步，且不能超过实际工具预算；候选操作最多 10 项、单次使用。证书保存搜索是否完整、因果深度、原生任务 Hash、证明 Hash 和实际证明操作数。

候选操作是允许请求的集合，不能指定唯一 witness 顺序。评分依据实际终态、frame、原 Oracle 和请求权限；证明路径不提供给 Customer/Service。反转候选操作列表仍能证明和执行合法多步任务。

## 双向任务搜索：两条完整的离线例子

以下是脚本化模型 fixture 驱动、真实 Engine/Oracle 参与的测试，不是线上模型研究结果。

**从正确题引导错误：** bootstrap 中 u0 正确启动 p0_db → 独立 Replay 确认 → Designer 在同一冻结世界选择本来就是 Viewer 的 u1，请求启动同一实例 → Reference 证明应该拒绝 → 固定 Customer 查询后实际提出请求 → 测试中的 Service 执行启动 → 原业务 Oracle 确认成功业务违规 → 登记候选错误，独立复测及自然角色对照后才确认规则边界。u0 的权限始终没有被修改。

**从错题复现与扩展：** 从上一条已验证 Viewer 错误出发 → 选另一个预先生成、冻结的世界以及其中既有 Viewer u2 → 组合对应资源任务 → 使用该世界的原始 Hash 执行 → Oracle 再次确认错误 → 记录可复现的决策错误。由于两个 seed 具有相同业务结构，这只是复现，不能宣称跨结构泛化或新根因。

所有跨代来源都绑定实际 Episode、原始请求、工具、Oracle 和 Replay。历史执行的中间状态可以供 Designer 分析，但不能成为未经登记的新世界初态。

## 发现、归因与 Skill 选择

任务构造成功、请求触发、实际错误、错误复现、根因确认分别记录。复杂度、模板数量、查询失败、任务未完成和不同指纹都不能直接增加独立错误数。

- 原业务 Oracle 继续判定真实状态变化、成功违规、授权异常及原生错误拒绝事件。
- 新的任务级 `TaskDecision` 单独核验明确的错误拒绝：仅接受公示代码单独响应，或严格的 `decision/refuse + operation + code` JSON；真实顾客已明确请求一个操作、没有执行业务写入、Reference 允许、响应及模型调用 Hash 能对齐时才成立。
- `TaskDecision` 不是伪造的 Engine 事件。业务违规数量仍为 0；不修改原 Oracle。普通自然语言、查询-only 响应及不明确的混合操作保持未确定。
- 任务级决策证据进入原 EpisodeEvidence 和 Service Reflector 的证据投影；没有改变 Service 的学习方法、系统策略、Skill Schema、Static/Dynamic Gate 或回滚规则。
- 非目标、未授权的额外操作独立保留，不能自动冒充 Designer 的直接发现。
- 错题分支可以凭经复测、去重的错误检出取得反馈，不依赖“正确题改一个世界字段”的对照。
- 相同规则码只是候选分组。自动确认仅支持明确的**自然身份权限对照**：同一冻结初态、同一单操作、既有不同身份、Reference 预期相反、真实正确对照及独立错误执行都齐全。其他机制保持候选，不声称证明模型内部原因。

任务重复使用原生匿名结构/语义签名去重，候选列表顺序和 seed 名称不制造独立覆盖。Designer 配对验收复用 `designer-paired-v2`，分别报告确认根因及可靠错误边界检出，保留质量、重复、成本约束与不确定性。

**当前严格按世界结构族聚类，名称不同的世界不是独立样本。** 示例世界池只有一个结构族，达不到默认最少 4 个来源簇的要求，候选会得到 INCONCLUSIVE、保留父版本。不能为展示进化而降低门槛。软件支持候选更新，不代表本例已经产生了获准的新 Designer Skill。

Designer 的 `selection / transformations / interpretation / stop` 字段保持历史 Schema，但新 Reflector 明确学习世界选择、既有身份/关系搜索、任务组合与停止重复测试；`transformations` 指任务空间变换，不再指改世界。静态检查冻结完整记忆与世界池中的禁止 ID/Hash；Replay 使用同一输入重建。

## 世界池覆盖审计的实际结果

最终审计：`experiments/vast_coevo/results/frozen-world-audit-002/`。包含原始世界、生成器 Hash、配置、分区、结构 Hash、完整源码 Hash、审计及覆盖缺口。模型调用 **0**。

| 指标 | 结果 |
| --- | --- |
| 生成 seed | 42、43、44 |
| 登记世界 / 有效业务结构 | 3 / **1** |
| 有界审计模板实例 | 333 次尝试，294 次有证明，39 次未证明 |
| 每个世界 | 26 条完成实例、72 条拒绝实例、8 条多步实例 |
| 跨 seed 去重后的任务 | 15 种结构、50 种业务语义 |
| 最大因果深度 | 2 |
| Reference 搜索节点 / 原生证明操作 | 339 / 438 |

这些是内部有限覆盖探针，不是新 Benchmark 数据集或排行榜，不代表任务空间穷尽，也不是 Service 错误数。

当前缺口：原生 seed 主要改变名称；角色分配、初始状态、配额和链式 DAG 相同，初态没有运行中的实例。有限索引没有覆盖 `attach_dependency / revoke_project_access / stop_instance / create_instance`；未进入索引不等于 Composer 或 Reference 一定不能处理。新建资源 ID、复合多写拒绝证明及返回初态的时序循环不在本版证明能力内。39 次无证明不能计作 Service 失败。

这些缺口会限制跨结构泛化研究和正式 Designer 验收。下一阶段应独立扩展并版本化 Generator 的角色、状态、配额和 DAG 分布，先冻结并审计，再统一提供给全部算法；本次没有加入根据 Service 表现特制的世界。

## 运行与公平消融

```bash
# 完全离线，先看覆盖；输出目录必须不存在。
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python experiments/vast_coevo/examples/frozen_task_discovery.py audit \
  --plan experiments/vast_coevo/examples/frozen-cloudops-plan.json --root outputs/frozen-audit

# 真实模型运行：须自行明确配置模型、地址及凭据；本次没有执行。
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python experiments/vast_coevo/examples/frozen_task_discovery.py run \
  --plan experiments/vast_coevo/examples/frozen-cloudops-plan.json --root outputs/frozen-run --models-from-env

# 完全离线 Replay：世界池、任务证明、实际对话/工具、发现、静态输入及版本选择。
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python experiments/vast_coevo/examples/frozen_task_discovery.py replay --root outputs/frozen-run
```

模型环境变量及独立 Reflector 兼容参数沿用 [既有运行说明](DESIGNER_SERVICE_V1.md)。`evaluate` 沿用独立 Snapshot 评价入口，要求不同 seed、新输出目录、相同模型及预算，不调用 Reflection、不改训练版本；它仍是开发诊断，不是最终 Held-out。

五组 `--strategy` 均保留：`random_legal / error_only / correct_only / bidirectional / bidirectional_fixed_designer`。它们共享同一世界池、验证器、固定 C、模型和预算上限。随机基线从共同可见的有限已验证组合索引抽样，不声称对全部理论任务均匀采样；未使用的 Designer 调用不会补给 Service。错误/正确单分支必须引用对应的实际来源。

上下文使用固定 seed 的有界世界窗口（默认最多 4）、最多 32 条任务索引、既有有界来源池及最近 64 条核验反馈/任务/成本；完整证据仍保存在档案中。构造失败也归档，并进入本代 Designer Reflection。检索条数、上下文长度、搜索节点、原生证明操作、模型 Token 和工具消耗分别记录。

## 审查入口与验证边界

1. `pool.py::WorldPool.load()`、`composer.py::TaskComposer.compile()`：Designer 能否改变初态；任务是否真实可达。
2. `discovery.py::TaskDiscoveryBank.evaluate()`、`task_oracle.py::decisions()`：业务错误、明确拒绝、复现、候选根因与确认如何区分。
3. `controller.py::FrozenController`：复用递归执行及原 Service Evolver，静态冻结输入与世界结构聚类。

历史 SceneEdit 和旧证据没有迁移；精确历史 Replay 继续要求原提交的源码。新增可选 `task_decisions` 不改变缺省旧证据的序列化。核心依然不导入业务包。

**掌控摘要：** 已实现固定世界中的任务发现、组合、证明、真实多轮执行及双边候选验收；离线测试使用脚本化模型，不能证明真实 LLM 学习收益。现有生成器的结构多样性不足已经被独立审计暴露，正式跨结构实验及真实模型效果未验证。

## 本次实际验证（2026-10-17）

- 全量回归：`PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q -x`，**1037 passed in 457.19s**。
- 定向协议/历史兼容测试：57 项通过；随后补充的 3 个异常拒绝输出参数测试也全部通过，并包含在最终全量回归中。
- 全量日志：`experiments/vast_coevo/results/frozen-world-audit-002/full-regression.log`。
- 新增测试包含两代执行与全档案离线 Replay、历史协议兼容、独立评价不改 Snapshot、原 Service Gate 拒绝未修复候选及预算上限。
- `git diff --check` 通过；没有修改原生 World、Engine、Reference Rules、Oracle 或 Service Dynamic Gate。
- 未运行真实 LLM、收费实验或 Frozen Held-out。离线 fixture 的成功不代表实际 Designer 已学会更有效的任务发现。
