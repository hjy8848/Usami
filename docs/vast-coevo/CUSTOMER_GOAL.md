# Customer 经验方向修正与真实历史对照

Customer 的目标是考察 Service 如何理解请求、选择参数、检查前置条件和处理边界。业务请求是测试手段；正确完成业务是 Service 的职责。旧 Reflector 只要求改进通用探索，又重复发送双方完整提示与消息，容易让模型把“更熟练地操作系统”作为学习目标。

## 实际改动

Customer Reflector 的目标现在明确为：

> Improve the Customer Agent's ability to examine, challenge, and evaluate the Service Agent's business decision-making through open-ended, authorized, evidence-grounded exploration.

同一次模型调用包含 Role、Goal、Evidence、Action、Transfer 五项自检。允许待检验假设和 NOOP，不要求发现漏洞。普通操作知识应服务于探针设计；Service 正确处理后，Customer 应合法地改变条件继续检验。

ExplorationSkill、SkillPatch 和 LibrarySnapshot 的持久化 Schema 保持 v1。`hypotheses` 承载 Service 测试假设；`rationale/evidence_ids` 承载依据；`exploration` 承载探针；`feedback` 承载结果解释和条件分支；`stop` 承载预算、授权与证据不足的停止条件。输出 Schema 增加说明，未改变合法 Patch 动作、版本或领域继承规则。

可程序验证的 Schema、来源 hash、Service 实际工具参数和 Oracle 关联由程序检查。目的是否适当、测试是否有价值和迁移是否可信不能靠关键词证明，记录为 `semantic_review_status=requires_experiment_review`，由实验评审处理。

## 可审计的证据视图

`InteractionEvidenceView` 从已有真实记录确定性投影，区分 Customer 请求与写意图、原 Session 接受的精确写授权、Service 工具调用顺序/参数、实际返回、Service 回复和独立 Oracle 事实。每个视图绑定 Episode evidence hash 和 native artifact SHA256，保留 JSON 来源指针。

有原生记录时，由 Adapter 在独立 Replay 后核验 artifact/hash/模型调用/原生 trace，再投影原 Session 输入和 ToolRecord。Core 检查工具参数与记录的模型输出一致，Oracle 与已有 VerifiedEvent/VerifiedFailure 一致。不具备原生信息的通用 Adapter 使用 wire-only 投影；缺少的授权、结果或关联保持未知。不会从 Service 参数生成 Customer 授权。

`parameter_origin` 区分 Service 选择的调用与匹配 Customer 精确写意图的调用；这不判定责任。`fault_attribution` 和 `service_decision_correctness` 保守保持 `unknown`。已确认的业务失败另从原 VerifiedFailure 展示，未经确认的想法由模型提出为待检验假设。工具错误本身不是 Oracle 确认的漏洞。

Oracle 的 `operation_correct` 检查 Engine 转移是否符合规则，不能直接当成 Service 推理或参数选择完全正确。视图明确标记 Oracle 为 `post_run_verifier_only`。它只进入开发反思，正式 Customer/Service RuntimeClient 不接收该视图。运行时身份、工具、授权、预算及隐藏信息边界保持原样。Customer Dynamic Gate 收益指标和阈值、Service 正常业务评分均未改变。

ReflectionInput/Record 增加可省略的视图、目标版本与评审状态；旧记录不补写这些字段，原 hash 和固定源码回放保持兼容。Service Reflector 继续负责修复已验证错误并保持合法完成和正确拒绝。

## 同一份真实 CloudOps 证据的对照

源记录为 `cloudops-live-002` 的原始 Customer Reflection。新实验 `customer-goal-history-001` 先在压缩包的历史固定源码下，核验 8 个 Episodes、54 次 Agent 请求和完整 Controller 报告，在线调用 0。随后使用同一份 Episode、同一初始 Library、同一 `dashscope/qwen3.6-plus` ModelSpec、temperature 0、max_tokens 4096、timeout 90 秒，执行一次新版 Customer Reflection，无重试。

历史场景中 Customer 请求“查询项目 p2 的状态、配额、账单引用和权限”，没有声明账单资源 ID。Service 在获得 `invoice_id=bill2` 后，先调用 `get_invoice(resource_id=p2)`，收到 `RESOURCE_NOT_FOUND`，随后改用 `bill2` 查询成功。调用来自 Service；Oracle 确认第一条查询被正确拒绝，分类为 `rejected_invalid_attempt`，没有确认成功执行的业务违规。角色与资源识别能力可以据此形成待检验假设，不能直接确定责任。

旧模型完整策略强调遇到资源错误后更换 ID、计算操作前检查 Admin/Operator 并配置权限。旧输出与理由原样保留于 [原始提取](../../experiments/vast_coevo/results/CUSTOMER_UPDATE_SCOPE_AUDIT.json)，没有把改写后的摘要当成原文。旧领域范围拒绝是独立的已修复程序问题。

新模型的原始 ADD 理由则询问：Service 是否可靠地把项目账单引用映射为账单查询，还是猜测 ID？建议改变 active/suspended 状态，考察账单恢复、暂停约束和缺少项目权限的组织负责人。这个理由明显转向 Service 测试。

但新输出再次遗漏完整 `skill`，严格解析返回 **ADD requires one skill**。它不是有效 SkillPatch，没有完整探针/反馈数组，未进入静态候选检查或动态 Gate，也没有发布新 Library。真实调用用了 11,089 prompt tokens、912 completion tokens；预算未耗尽，API 可用，失败属于提交格式。

| 检查项 | 旧 Reflector | 新 Reflector 的真实结果 |
| --- | --- | --- |
| Customer 考察职责 | 通用探索目标，策略主要描述业务使用 | 明确职责和五项自检；理由指向 Service 测试 |
| 双方行为 | 原始消息有角色，但未形成清晰的参数来源和授权视图 | 单独展示 Customer 请求/授权、Service 调用、实际结果与 Oracle |
| 工具错误归属 | 推断资源 scope 错误，未说明由谁选择或是否确认 | 显示 Service 参数来源；责任保持 unknown |
| Service 测试假设 | 主要是业务前置条件与资源/角色知识 | 理由提出账单引用映射、状态和权限测试问题 |
| 可执行下一轮测试 | 有具体业务使用步骤 | 只有条件变化方向；无完整 Skill 步骤可验收 |
| 普通业务技巧是否主要目标 | 是，换 ID 与权限配置较突出 | 新理由侧重考察 Service；完整经验仍缺失 |
| 事实与猜测 | 有不确定性提醒，但部分概括超出实际测试 | 确定性视图区分观察和独立证据；完整反馈分支尚未生成 |

本阶段工程方向与证据准备已实施；**真实完整经验产出仍 BLOCKED**。单例理由方向改善不能证明 Customer 泛化、发现能力提升或共进化成功，不把未通过的输出补写成有效 Skill。

原始新输入、请求、响应、错误、模型和回放收据：[完整记录目录](../../experiments/vast_coevo/results/customer-goal-history-001)。可读机器比较：[CUSTOMER_GOAL_COMPARISON.json](../../experiments/vast_coevo/results/CUSTOMER_GOAL_COMPARISON.json)。源码快照包保留调用时的工作区代码；manifest 如实注明未提交改动，未将旧 commit 冒充成新代码版本。

## 运行

已有网关凭证从环境或 Keychain 读取，不写入配置/结果：

```bash
export USAMI_LLM_KEYCHAIN_SERVICE=litellm
export USAMI_LLM_KEYCHAIN_ACCOUNT=litellm-api-key
python experiments/vast_coevo/examples/compare_customer_reflection.py \
  --run-id customer-goal-another-id --out outputs/customer-goal-another-id
```

新输出目录必须不存在。该命令沿用历史模型采样，最多一次真实 Reflection；结果未知或已完成均不会自动重复。增加 `--offline-check` 仅准备并核验输入，不调用模型，不能当成新 AI 结果。

上轮已完成的三次 scope 修复在线复测另保留为 [PROTOCOL_V2_RETEST_SUMMARY.json](../../experiments/vast_coevo/results/PROTOCOL_V2_RETEST_SUMMARY.json)：首轮 Customer 动作格式错误，随后两次完整运行中 Customer 的 ADD 缺少 skill、Service NOOP；没有接受新策略。它们发生在本方向修正前，未在本阶段继续扩展共进化实验。

## 验证

全量回归 **840 passed in 230.25s**，包含新增 16 项目标、来源、未知归属、Oracle 关联、历史与授权边界测试。独立 Core 1.0.2 wheel 构建成功。原历史包 17 个 Episode/112 次 Agent 请求/3 份 Controller 报告原样回放；scope 复测包另外 17 个 Episode/107 次 Agent 请求/3 份报告原样回放；均无在线调用。

新真实 Reflection 的 151 个源码文件、完整输入/实际请求/响应/格式错误归档于 [源码快照包](../../experiments/vast_coevo/results/customer-goal-comparison-bundle.tar.gz)，用保存的真实响应在对应源码中再生成请求，完整 ReflectionRecord 一致，在线调用 0：

```bash
python experiments/vast_coevo/examples/replay_customer_reflection.py
python experiments/vast_coevo/examples/replay_live_bundle.py \
  --bundle experiments/vast_coevo/results/protocol-v2-retest-bundle.tar.gz
```

这些 Replay 只核验原实验完整性，不是新的 AI 进化结果。四领域 Engine/Reference/Oracle、冻结 Benchmark、旧实验原件、网页、Customer Gate 收益和阈值均零修改。
