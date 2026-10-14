# VAST-CoEvo 架构与依赖边界

[路线图](ROADMAP.md) · [方法](METHOD.md) · [Schema](SCHEMAS.md) · [实现与验收](IMPLEMENTATION.md)

## 依赖方向

```text
研究 CLI / 外层实验配置
    ├── vast_coevo Core ── EnvironmentAdapter Protocol
    └── integrations.usami ── 实现 Protocol ── 原有 Usami Sessions
                                               └── Tools / Engine / Rules / Oracle / Replay
```

Core 的唯一环境输入是通用协议与版本化证据。集成层可以导入 Core 和 Usami；Usami 不需要导入或安装 Core，Core 不导入 `usami`、`usami_cloudops`、`usami_fulfillment`、`usami_stayops` 或 `usami_harness`。目录分开之外还需自动依赖边界测试与无 Usami 导入验证。

## 责任归属

| 层 | 拥有的职责 | 不跨越的边界 |
| --- | --- | --- |
| Usami 环境 | 四域 World/Generator、Engine、Tools、Reference Rules、独立 Oracle、Session、授权、Trace、Replay、Benchmark 评分 | 不实现 Skill 进化；冻结 Manifest/历史报告不改写 |
| `vast_coevo` Core | 结构化 Skills、Library/检索/渲染、内容寻址版本、双 Reflector/Evolver、静态/动态门槛、Rollback、证据 archive、代际控制器 | 不接收领域私有对象；不硬编码业务裁判 |
| `integrations/usami` | Session 初始化、合法观察提取、模型客户端注入、四域真实执行、Oracle Evidence 转换、回归和回放、可比性检查 | 不修改规则；不从 Service 调用生成 Customer 授权 |
| 外层研究运行 | Split、固定模型/环境配置、Snapshot hash、调用预算、运行日志与验证报告 | 正式 Test Evidence 不进入 Reflection/候选选择 |

## 四领域现有接口差异

实现前检查表说明为什么 Adapter 必须逐域处理，不能假设所有构造器和 Trace 相同。

| 领域 | 既有 Customer 入口 | Service / 配置特点 | Replay |
| --- | --- | --- | --- |
| SaaS | `usami.interaction.runner.InteractionSession(config, customer_client, service_client)` | `usami.service.runner.ServiceSession`；独立 `InteractionConfig` 和 `Experiment`；`IntentAdapter` 先准备精确授权 | `usami.interaction.runner.replay_interaction` |
| CloudOps | `usami_cloudops.customer.InteractionSession` | 领域自有 `InteractionConfig`、Customer Action/IntentAdapter、ServiceSession、Budget/Experiment；采用其观察与工具 Schema | `usami_cloudops.customer.replay_interaction` |
| FulfillmentOps | `usami_fulfillment.customer.CustomerSession` | 薄封装 `usami_harness.customer.CustomerSession`；注入领域 adapter；共享 harness 的 Experiment、Service 与授权语义 | `usami_fulfillment.customer.replay_interaction` |
| StayOps | `usami_stayops.customer.CustomerSession` | 同样复用共享 harness，但库存、日期/房间、业务工具和 Oracle 属于 StayOps adapter | `usami_stayops.customer.replay_interaction` |

原会话拥有单次授权、固定身份、持续世界和独立审计。集成层必须保留 Customer 意图先于 Service 决策，Trial 之间重置且 Trial 内状态持续的语义。

## 通用协议与证据

`vast_coevo/protocols.py` 定义 `CompletionClient.complete(request)` 和 `EnvironmentAdapter`。环境协议包含 `run_episode(config, customer, service, episode_id)`、`run_service_task(config, task_ref, customer, service, episode_id)`、`run_failure_case(source, customer, service, episode_id)`、`replay(evidence, customer, service)`、`public_capabilities(config)`、`initial_observation(config)`。Episode 配置与 Snapshot 都是 Core 模型；业务对象留在 Adapter 内部。换环境时实现这些能力，Evolver 本身不变。

`integrations.usami.UsamiAdapter` 使用 profile registry、task registry、client factory 和 artifact root 连接四域；`config_for` 将领域 profile 转换为冻结通用配置。动态门槛比较通用 `config_hash`，不直接比较领域私有 World 对象。

| 实际模块职责 | 路径 |
| --- | --- |
| 通用模型 / Protocol / 原子存储基础 | `vast_coevo/models.py`、`protocols.py`、`schema.py` |
| Skill 模型 / Library / 检索 / 渲染 / 静态验证 | `vast_coevo/skills/` |
| 双 Agent 模型请求注入 | `vast_coevo/agents/runtime.py` |
| CustomerReflector / ServiceReflector | `vast_coevo/reflection/reflector.py` |
| 动态门槛 / 双 Evolver / 代际状态机 | `vast_coevo/evolution/gates.py`、`evolvers.py`、`controller.py` |
| 通用失败指纹 / Evidence Archive | `vast_coevo/evidence/signatures.py`、`archive.py` |
| Run / Generation 持久化 | `vast_coevo/storage/runs.py` |
| 领域 registry / Session 适配 / Oracle 解析 | `integrations/usami/domains.py`、`adapter.py`、`evidence.py` |

以上列明分工；各模块当前是否已实现/测试通过，以实现报告为准。

`EpisodeEvidence`、`VerifiedFailure`、`SkillPatch` 和 `EvolutionRecord` 使用明确 Schema 版本与受约束字段；领域完整 Trace 可以作为带环境版本/hash 的附属原始文件保存，不能让它代替通用协议。领域事件的解析、Operation 参数、Oracle 码与相关前态的选择都留在集成层。

Core 持有内容不可变的 Library Snapshot；当前已接受版本通过独立代际记录指向快照。候选创建与选中提交分离，失败不能覆盖父版本。存储采用原子替换或等价事务，加载时核对内容 hash 和父版本。历史版本保留，Rollback 恢复引用，而不是在原 Skill 上逆向修改。

## 双 Agent 注入与信息边界

Retriever 根据合法观察选择 Skill，Renderer 生成带角色、ID/Version 和边界的指导块。集成层应优先通过模型客户端 wrapper，在已有请求进入真实客户端之前注入，避免改动旧 Session/源码固定值。最终 wire request、原始 response、实际 Skill 内容、Snapshot hash 和命中记录必须持久化。若旧 Session 保存的是注入前请求，外层记录必须保存实际请求并提供匹配的 Replay wrapper；不能声称两种请求 hash 相同。

Customer 正式请求不能含固定 Benchmark 目标、Witness、私有完整 World State、隐藏 Reference 结果或未来事件。Service 正式请求不能含 Oracle 作为可调用工具或基于隐藏规则的硬编码判定。Reflection 使用开发集独立验证反馈，但运行时政策、合法观察与反馈来源必须分开记录。

Skill 是声明式方法：不会直接调用 Python、改写世界或创建新的工具权限。实际操作仍由原 Session 的工具协议解析并通过 Engine 执行。静态门槛与权限过滤共同防止越界；自然语言文本筛查不能代替运行时授权控制。

## Controller、恢复与成本

控制器每代严格按当前探索 → Customer 更新 → 再探索 → Service 更新 → 跨代执行推进。每一步保存实际父版本、唯一 Patch、候选快照、选中快照、验证报告与终止原因。NOOP 和拒绝可以让相邻 Generation 引用相同 Snapshot。

反思调用前保存已消耗机会的标记；完成记录存在时不再次调用。未知中断状态不得静默再反思。Episode 与代际预算包含 Customer/Service、Reflector、动态验证和交叉执行的实际调用，不能只统计主探索。Adapter 提供可比性签名，防止候选和父版世界、身份、预算或模型不同。

## 历史兼容与验证

VAST-CoEvo 运行使用独立外层记录和 Schema 版本，引用原环境版本/源码 hash，不改写冻结 Manifest、历史 Benchmark 报告、规则或 Oracle。旧 Benchmark 继续独立运行；新请求对应新 hash。旧历史回放与新 Skill 注入回放分别测试。

验收必须覆盖：Core 单元与依赖隔离、四域真实 Engine/Rules/Oracle/Session、双 Agent 实际请求注入、真实事件转换、Replay、两代以上控制器与拒绝/NOOP/恢复、全仓库回归、真实模型 Pilot 或可审计阻塞。具体模块、命令、实际结果与限制只在 [IMPLEMENTATION.md](IMPLEMENTATION.md) 标记，设计文字本身不构成测试证据。
