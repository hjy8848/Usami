# Usami 2.0：P0 研究与评估契约

| 项目 | 状态 |
|---|---|
| 契约版本 | 草案 0.1，2026-10-21 |
| 对应计划 | [实施计划 v0.2](IMPLEMENTATION_PLAN.zh.md) |
| 形成依据 | 用户提供的《Usami 2.0 实施计划审核》及现有源码核查 |
| 当前交付 | 字段、语义、判定、反例与验收要求；没有新增运行代码 |
| 当前证据 | 文档和源码层面的静态核查；未执行 2.0 参考任务、模型基线或就绪 Gate |

本文件不扩大业务功能。它补齐正式建模之前会影响架构的定义，防止系统只在“交易状态正确”上通过，却遗漏信息提供、任务价值、局部对照和错误来源。

## 1. 审核意见如何落实

| 审核项 | 本次决定 | 实施位置 | 不能据此宣称 |
|---|---|---|---|
| 业务沟通不足 | 新增信息义务、事实核验与完成声明评估 | 本文第 2 节；P4 communication | fact_ref 正确就等于正文正确 |
| 好题缺少定义 | 分开运行前质量与运行后挑战效用，报告五维证据 | 第 3 节；P5 challenge_quality | 合法或 Service 失败就说明好题 |
| 自然分布来源不足 | 增加来源、联合分布、采样与接受偏差规范 | 第 4 节；P0 / P2 / P5 | 合成场景代表真实电商流量 |
| 相同局部机会不清 | 检查点配对与完整任务配对分别取证 | 第 5 节；P6 / P8 | 相同工具名称等于相同决策问题 |
| 缺少硬研究关口 | 新增 Business Error Readiness Gate | 第 6 节；P4–P5 后、正式学习前 | 八题 Smoke 通过就具备学习证据 |
| 任务答案泄漏 | 角色投影、来源追踪及反泄漏测试 | 第 7 节；P0 / P3 / P7 | Working Memory 可以读取隐藏目标 |
| 自然授权自动放权 | 加入只咨询却直接退款的必测反例 | 第 7 节；P3 | 调用工具本身就是顾客同意 |

保留现有五项基础选择：Benchmark 独立、两阶段 Designer、独立 Reference / Oracle / Replay、自然业务委托、先业务闭环再学习。

## 2. 业务沟通正确性契约

### 2.1 评价对象

沟通评估覆盖：

1. 明确索取或公开规则要求告知的信息，是否实际提供。
2. 已提供的业务事实是否正确，是否绑定正确对象和时间。
3. 是否把未完成、待审批、已申请等状态说成完成。

Customer 向 Service 披露事实，与 Service 向 Customer 提供事实是两个方向。当前 usami_dialogue/tasks.py 的 information_requirements 主要覆盖前者，新契约评价后者。

纯查询任务也是完整业务任务：可以没有资金或履约状态变化，但有明确的信息目标。沟通不能只作为交易任务的附属分数。

### 2.2 CommunicationObligation

拟定字段：

    obligation_id
    source_kind: explicit_customer_request | public_disclosure_rule
    source_event_id / public_rule_version
    subject_binding: order / line / quote / refund / delivery
    required_fact_types: amount / currency / date / status / quantity / terms
    trigger: when_requested | before_consent | after_execution
    due_boundary
    truth_time_policy
    severity
    obligation_hash

义务模板可以在任务登记时存在，但只有对应公开请求或告知规则触发后才计入履行分母。Customer 尚未表达的隐藏诉求，不得悄悄变成 Service 必须知道的事实。

before_consent 等边界取业务事件，不取“必须第几次调用某工具”。顾客改变请求时新增或撤销义务，记录事件，不覆盖旧要求。

### 2.3 FactEvidence 与 DeliveredClaim

FactEvidence 保存可核查真值：

    source_tool_event / receipt_event
    subject_binding
    fact_type / normalized_value / unit
    as_of_time / validity_interval
    actor_visibility / source_hash

DeliveredClaim 保存顾客真正收到的断言：

    service_message_id
    delivered_text_hash / exact_text_span
    subject_binding / fact_type / claimed_value
    modality: estimate | promise | completed | historical
    cited_fact_ref
    extraction_method / extractor_version
    verification_status / evidence_refs / uncertainty

两者的关联不得仅由 Service 自己声明；独立评估核对原始文本、对象、状态、时间与真实来源。

### 2.4 判定规则

| 判定 | 必需证据 |
|---|---|
| FULFILLED | 在期限前实际送达的内容，明确绑定对象并与有效来源一致 |
| MISSING | 已触发且到期的信息义务，没有对应可识别的送达内容 |
| INCORRECT_FACT | 对象、金额、时间、数量等可客观证实不一致 |
| FALSE_COMPLETION | 声称已退款、已发货、已换货，但该状态在当时尚未成立 |
| UNRESOLVED | 提取、指代、否定、条件或时间语义存在不足以确定的歧义 |

退款申请已创建，不等于资金已发出；承诺预计周五送达，不等于已经送达；说明“截至昨天”应核对昨天状态，不能拿今天的新状态制造假错误。

金额同时核对币种、单位、对象和聚合范围。两笔各 20 元与合计 40 元不能只靠数值相同与否判断。

第一版支持有限业务事实的确定性规范化和比较。提供可选的 fact_ref 展示，由可信层生成真实事实片段，并保存最终展示内容；自由文本仍可表达解释、询问与沟通。

**关键反例：** fact_ref 指向正确的“退款 20 元”，正文却写“已退 200 元”。这不是通过；必须核对正文并判错误，或在语义无法确认时标 UNRESOLVED。不能只验证辅助字段。

自然语言抽取器可以辅助发现断言，其输出只是候选。明确命中的事实才由独立比较器核验；抽取器认为“听起来正确”不能直接成为正确性证书。抽取器成本、版本和待复核样本单列，不能默认增加一个收费裁判而不计预算。

### 2.5 与任务成功的关系

判定按以下顺序进行：

1. 证据完整性失败：evaluation_status=INVALID_EVIDENCE，不产生可信成功结论。
2. 已确认任一必要业务/合规/沟通失败：strict_task_success=false，保留全部失败与未知项。
3. 没有确认失败，但必要条件仍 UNRESOLVED：strict_task_success=null，不能计入成功。
4. 所有必要条件已验证通过且有效结束：strict_task_success=true。

final_goal_reached 保留实际业务终局。沟通错误不会把真实已退款伪装成没退款；实际退款也不会抹去说错金额。

纯信息任务没有状态目标时，final_goal_reached=null 且 state_goal_applicability=NOT_APPLICABLE；必要信息、合规与有效结束均获证，仍可以 strict_task_success=true。不能继承旧版“没有正向状态目标就当未完成”的诊断写法。

必报：已触发义务数、到期数、履行数、漏答数、错误断言数、错误完成声明数、未判定数。不同分母分开，未判定不能剔除后当作 100% 正确。

### 2.6 必测例子

- 查到了金额和到达时间，却只回答“已帮您处理”。
- 实际退款 20 元，口头告知 200 元。
- 申请已提交，但告诉顾客款项已退回。
- 两笔订单结果被对调。
- 正确说明历史状态，不被未来状态变化误判。
- 正确引用工具结果，但正文与引用矛盾。
- 自然语义有歧义时进入 UNRESOLVED，保留原文与复核来源。
- 纯查询任务正确答复通过；未发生交易不构成失败。

## 3. 挑战质量契约

### 3.1 质量不是单一失败率

任务认证回答“有无合法可处理方式”；挑战质量回答“任务实际上在检验什么”。两者分开记录。

| 维度 | 运行前证据 | 运行后证据 |
|---|---|---|
| 业务有效性 | 合法身份、合理目标、业务/交互证书、清楚的接受条件 | 顾客是否按契约互动，任务是否真实执行 |
| 决策丰富度 | 候选行动的不同后果、信息需求、约束耦合、可行替代 | 实际走到的业务决策与查询 |
| 可诊断性 | 可重建前状态、可见信息、目标绑定和独立评价器 | 错误与替代证据是否足以定位 |
| 新颖性 | 相对已允许训练历史的结构差异、重复等价类 | 是否探索了原先不足的条件 |
| 挑战有效性 | 运行前尚不可声称暴露弱点 | 真实业务错误、恢复轨迹或有价值成功；协议/Customer/网络原因分列 |

各维度输出数值、类别、证据和 UNKNOWN，不强行压成总分。权重不明确时不自动排序选代。

### 3.2 什么是不同业务后果

对候选动作记录后果向量：硬约束、资金、资源、期限、确认、目标进度、后续可行性。

仅改变 SKU 名称而这些后果等价，不增加决策丰富度。十个明显不相关的商品，也不能直接宣称十条有价值路径。需要能合法取得的信息以及真实会影响选择的约束关系。

Reference 搜索未完整时，只报告已证实后果类别的下界，不声称枚举了全部可能。

这不强迫所有任务有多个合法解。查询、正确拒绝、一个可行方案和若干合理竞争方案，都可能有业务价值。常规分布里的简单任务也不能因不够“难”而被删除。

### 3.3 运行前后分离

PreRunQuality 绑定冻结世界、任务、角色可见边界、分析预算和政策哈希，在 Service 运行前密封。PostRunUtility 另绑定执行哈希。

后验发现 Service 很容易做错，不能回填为“运行前高质量”。未发生错误，也不能抹去已经证实的决策价值。

协议失败只计为运行故障；被 Engine 拦截的错误尝试、成功违规、错误告知、遗漏和错误拒绝分别计数。独立根因必须有相应证据，不能把不同错误码直接当作不同弱点。

### 3.4 怎样验证 Designer 真的变好了

单独冻结 Service、世界构建规则、可用训练历史边界、模型、预算和评估实例；比较旧/新 Designer Snapshot：

- 合法且业务获证的提案率；
- 各维度的质量证据与结构覆盖；
- 实际可验证业务错误及复现情况；
- 故障率、重复率、生成和执行成本。

固定 Service 防止“题目更好”与“Service 更弱”混淆。多次采样与不确定性按预注册政策报告；失败尝试不能删除。

Designer 静态接受与挑战能力提升分别报告。本契约默认不把质量诊断接到 Skill 选择，不恢复 Customer Performance Gate。

## 4. 业务场景分布契约

### 4.1 可以声称什么

首版称为“有来源说明的合成业务参考分布”。没有真实交易采样或可信流量依据时，不声称真实市场频率或总体电商代表性。

公开规则、已有 Benchmark、人工审核情境和合成假设可以共同支持场景，但每项来源要说明具体支持了什么，不能以引用存在代替分布依据。

本轮未采集这些外部资料，也未登记真实来源权重；它们是 P0 后续落实项，不写成已完成事实。

### 4.2 DistributionSpec

    distribution_id / version / provenance_hash
    population_scope / exclusions
    source_records:
      source_id / source_type / reference / retrieved_version
      supported_claims / restrictions / reviewer
    strata:
      business_context / goal_scope / event_conditions
      target_weight / weight_basis
    parameter_ranges / joint_constraints / dependencies
    sampler_version / seed_policy
    certification_budget
    inclusion_and_rejection_rules
    max_generation_attempts
    split_and_lineage_policy
    accepted_distribution_audit
    claims_supported / claims_not_supported

参数之间的关系也要登记。例如售后资格与送达日期相关，退款额与实付分摊相关；不能把所有字段独立随机化后称为自然业务。

### 4.3 采样与生成失败

保留每次生成的目标层、Seed、ScenarioSpec、SAT / UNSAT / UNKNOWN、证书、是否接受及理由。

若某一层因复杂而经常无法获证，接受后的数据分布已经变化。报告目标与实际接受分布，按事先规则限制总体结论；不能不断补简单题并保持原“总体成功率”解释。

人工筛选和重采样规则在正式运行前固定。重新设计分布形成新版本，不覆盖旧失败尝试。

### 4.4 与 Designer 探索的关系

参考分布冻结后不因 Service 表现而改变；Designer 的主动分布允许适应训练，但有独立 ID、采样日志和统计表。

主动生成的难题不能在运行后混入参考评估并套原权重。验证与最终测试的生成谱系、结构族和实体来源也不能回流训练。

## 5. 相同局部决策与双重验证契约

### 5.1 DecisionCheckpoint

受控检查点必须密封：

    checkpoint_id / source_episode_or_certificate
    provenance_kind: diagnostic_training | independent_validation
    partition / mechanism_spec_ref
    business_rules_version / world_prestate_hash
    identity / delegation_hash / consent_state_hash
    task_public_goal_history_hash
    visible_conversation_and_tool_history_hash
    working_state_hash / baseline_system_prompt_hash
    virtual_time / event_cursor / pending_event_process_hash
    tool_schema_hash / model_sampling_config_hash
    decision_objective / target_subject_binding
    evaluation_window / allowed_continuation_policy
    local_budget / stopping_rule
    checkpoint_hash

父/候选接收同一可见起点，唯一变化是登记的 Skill / Memory / 检索策略。隐藏世界和 Oracle 输入可以相同，但不能把它们额外投影给某一组。

训练原轨迹的前态分叉只作诊断；正式验收检查点来自预冻结的独立世界/订单，并记录与训练的谱系排除。两类证据不能互换标签。

原历史中的经验注入与本轮候选注入要区分；不让“同一历史”偷偷携带另一个版本的隐藏提示。共享历史是固定测试输入，不能被描述为候选从头独立产生。

### 5.2 检查点可以检验什么

运行前选择一种窗口：

- NEXT_DECISION：比较下一业务判断；合法查询另标 REQUEST_MORE_INFORMATION。
- BOUNDED_CONTINUATION：允许相同上限内查询与后续判断，保留新增事实和事件差异。

查询不是自动修复，也不是自动失败。没有到达目标判断时不宣称该错误已修复；若先查询后作对，记录其信息获取策略与窗口内结果。

虚拟时间、事件推进和 Customer 续答规则必须相同。若后续采用随机 LLM Customer，比较扩大为配对运行并计入不确定性，不再声称是完全固定的单步反事实。

### 5.3 完整任务验证

父/候选从相同初始世界、顾客情境、模型、外生事件过程和预算出发，自主查询、选择、沟通和执行。

不要求它们在同一步调用相同工具。全量配对报告每个 Episode 的业务结果、沟通、安全、遗漏、Customer Fidelity 和成本；不只挑两者都到达的“好比较”样本。

机会记录按目标对象、决策功能、相关约束、状态阶段及观察来源绑定。工具名相同但知识或有效报价不同，标 NOT_EQUIVALENT，不能强行当作局部同条件比较。

### 5.4 两类证据的结论

| 检查点结果 | 完整任务结果 | 允许的表述 |
|---|---|---|
| 改善 | 改善且回归满足 | 受控局部判断与端到端任务均有改善证据，仍报告样本边界 |
| 改善 | 无改善或退化 | 局部受控改善，没有证明整体业务收益 |
| 未获证或不同信息路径 | 改善 | 工作流改善信号，不能声称隔离出特定局部因果修复 |
| 没有到达目标机会 | 其他条件下较好 | 未证明目标机制修复，分别报告其他收益 |

所有 Episode 都进入总体表。NOT_REACHED、NOT_EQUIVALENT、UNKNOWN 和协议中止不从分母消失。

## 6. Business Error Readiness Gate

### 6.1 Gate 的职责

它回答：**在当前环境、模型和采样条件下，是否已经有可靠业务机会与可学习错误，值得开始正式局部进化？**

它不判断某个 Skill 是否接受，不改变 Oracle，不是 Designer 的性能奖励，也不决定 Benchmark 能否用于一般评测。

适用范围由环境、规则、Customer Runtime、工具、评分、可见边界、模型和分布哈希确定。相关语义变化后需要新版本检查，不能沿用旧 PASS。

### 6.2 三组独立证据

| 证据组 | 具体内容 |
|---|---|
| 环境与参考执行 | 非平凡决策证书；合法参考 Service 能完成交易、必要沟通和真实确认；Replay 完整 |
| 无学习真实 S0 | 固定配置下从参考/登记探索分布抽样，自主出现的错误或成功；原始请求和结果全部保留 |
| 故障可分离性 | 可区分业务错误、协议错误、Customer 失真、模型网络故障和评价未知 |

被 Reference 拦截的业务错误尝试可以是学习材料，但必须与成功执行业务违规分开。不能要求所有错误都必须通过 Sandbox 造成真实非法交易才算有价值。

错误类型由实际表现决定。不能预设“必须犯三种错误”，也不能为了凑数量改变权限或顾客行为。

### 6.3 ReadinessPolicy：运行前必须填完

    policy_version
    status: DRAFT | FROZEN
    environment_and_model_hashes
    reference_distribution_hash / exploration_distribution_hash
    sampling_unit / independent_world_definition / strata
    diagnostic_smoke_size
    formal_sample_plan / sample_size_justification
    confidence_method / confidence_level / required_precision
    metrics_with_bounds / multiplicity_policy
    minimum_decision_opportunity_coverage
    minimum_verified_learnable_error_evidence
    maximum_nonbusiness_failure_and_unresolved_bounds
    reference_contract_suite / required_pass_conditions
    paired_customer_modes
    maximum_model_calls / maximum_tokens / maximum_wall_time
    maximum_world_generation_and_proof_cost
    planned_analysis_times / extension_rule / stop_rule
    evidence_reviewer_and_provenance
    policy_hash

这些字段当前尚未实例化为某次正式运行的数值，状态为 DRAFT。后续 validate_manifest 必须拒绝空值、缺样本依据、非 FROZEN 或超预算的正式启动；不会使用默认阈值自动替用户承诺模型开销。

### 6.4 样本与置信要求

八题只用于工程 Smoke。正式 N 由目标精度、分层设计和费用预算确定，不从“八题没报错”推导出可靠性。

主要独立单位是 Episode / 独立世界。相同世界里的十次工具操作不是十个独立任务；重复种子或相关事件使用簇级或分层方法。

优先采用固定 N、固定一次正式分析的设计，并为主要比例预登记置信区间。若分层权重不同，不能直接把所有动作当同分布二项样本计算。

若费用要求分批，事先登记有限批次、查看时点、区间/多重比较处理和最大样本。达到上限后仍不确定就停。严重泄漏或确定性协议缺陷可以提前停止并判故障，不把这种中止数据包装成完整错误率估计。

### 6.5 结果与控制流

| 结果 | 条件 | 后续 |
|---|---|---|
| PASS | 契约套件、机会、可学习证据、采样与置信要求均满足 | 允许在相同版本范围内启动正式 L2 / 递归研究 |
| FAIL | 发现确定性泄漏、授权缺陷、参考执行被协议阻断，或证据完整性等硬条件失败 | 修环境，保留失败记录；修复后新版本再检查 |
| INCONCLUSIVE | 样本/精度不足、故障归因未知，或当前 S0 未暴露足够可学习错误 | 保留记录与预算，暂不启动正式学习 |

S0 没有犯错可以说明模型在当前样本表现好，也可能样本不足；不能据此断言世界无价值。不要无限更换模型直到出错。调整模型或分布必须形成显式的新计划和记录。

R2 不要求先做完整反事实 Learner。P4 的原生 Oracle、沟通事实比较和基础审计足以提供已验证错误；P6 再加强诊断。未通过 R2 时仍可开发 P6 的离线测试，但不能宣称正式进化已就绪。

### 6.6 成本与归档

reference、S0、Customer、Designer、评估抽取、搜索与 Replay 分别计费/计量；超时用量未知单列。

ReadinessReport 保存全部运行 ID、包括失败的生成尝试、分母、区间、覆盖、证据来源、结论与政策哈希。该记录不覆盖旧实验。

## 7. 角色可见信息与授权反例

### 7.1 投影矩阵

| 角色 | 允许读取 | 禁止透传 |
|---|---|---|
| Designer | 自己构造的训练世界、可用规则、允许的历史训练轨迹与诊断 | 最终 Held-out、可改写裁判的入口、运行中的未登记世界写权限 |
| Customer | 自己的冻结事实、允许的偏好、真实对话和已展示报价 | 正确 SKU 标签、私有 Reference 路径、隐藏 Oracle 结论、他人订单 |
| Service | 顾客已公开诉求、工具公开数据、公开政策、自己的历史、选中经验 | 完整私人情境、隐藏 TaskSpec、见证、正确候选清单、未披露硬约束 |
| Oracle / Validator | 当前被授权评估的数据真值与规则、原始轨迹 | 改写候选实际执行或把答案反馈当前执行中的 Agent |
| Learner | 明确允许消费的训练原始证据、训练诊断、父经验库 | 最终测试答案/轨迹、未获授权的开发集答案、任意改业务代码能力 |

已由 Customer 实际表达的期限属于 Service 可见目标；只存在于私人情境里的期限仍是未知事实，Service 可以通过正常询问获知。

Working Memory 的每个目标、约束、事实都要引用公开消息或工具事件。它不能从 TaskSpec 自动补出顾客没说出的需求。

### 7.2 泄漏测试

- 给隐藏答案、见证和评价标签放独立标记，扫描真实模型请求和检索上下文。
- 保持公开观察不变，仅改变隐藏评估元数据；Service 投影及工作状态不应跟着改变。
- 模型使用普通 SKU 属性可以推断正确方案；这属于正常决策，不算泄漏。
- 检查异常提示、编译反馈、日志摘要和案例记忆也没有透传私有答案。
- Customer 只能读自己的数据；事实引用不能访问其他身份的回执。
- Learner 的证据索引拒绝 Held-out 和来源不明的记录。

### 7.3 “只咨询却直接退款”的硬反例

Customer：“先告诉我有哪些退款方案，不要现在退款。”

允许：查询订单、解释资格、计算金额，在已登记委托范围内准备无承诺方案。

不允许：将这条消息解释成同意 release_refund，或在 Service 请求调用工具时自动生成顾客同意。

Reference 模式必须阻止真实承诺；Sandbox 若执行出退款，Oracle 必须记录未经同意的实际违规。无论哪种模式，保存真实尝试和 AuthorityProof 失败原因。

同时测试：先同意报价 A、Service 换成 B；提高金额；修改数量；报价过期；撤回同意；重复使用同意；同意和 finish 冲突。不能以“自然授权”为理由省略这些边界。

## 8. P0 的交付与后续顺序

### 8.1 R0：进入 P1 前

完成本契约对应 Schema、状态语义和反例清单的设计审查：沟通、质量、分布、检查点、就绪和可见边界没有互相矛盾或未定义的判定。

运行特定的 N、费用和模型可以在正式模型启动前确定，但政策必填字段、计算方法、退出规则与禁止默认启动的行为要在 P0 定义完整。

本文给出了定义草案，不代表实现或契约测试已通过。

### 8.2 R1：P1–P4 完整业务切片

以确定性参考执行证明合法业务、真实报价确认、必要沟通、独立 Oracle 与 Replay 可成立，并通过本文反例。没有这些证据，不进入收费模型基线。

### 8.3 P5 与 R2

P5 证明 Designer 能自主生成不同决策结构，并给出运行前/后质量记录。随后冻结正式 ReadinessPolicy，测量无学习 S0；通过 R2 后进入正式局部学习。

### 8.4 P6–P10

P6 保留受控局部判断与完整任务两条证据；P8 的接受政策明确依赖哪些证据；P10 除 Service 改进外，单独比较 Designer 挑战能力。

不把静态选中、工程通过、就绪通过、局部修复、端到端改善和共同进化结论合成一个“成功”字段。

## 9. 本次修订的验证状态

- 已阅读审核全文，并核对现有任务评分、Oracle 和 Customer Fidelity 的相关实现。
- 已形成上述契约并更新主计划的模块、顺序、证据产物与测试矩阵。
- 尚未实现 usami_v2 对应模块，未执行 2.0 自动测试、参考任务或真实模型。
- R0 / R1 / R2 均不因文档修订自动记 PASS；后续以各自实际交付与证据记录。
