# Usami 2.0 实施计划书

## 从真实业务决策，到可验证的局部学习与递归进化

| 项目 | 内容 |
|---|---|
| 文档状态 | 实施前计划；本文件中的新模块、接口与命令均为拟实现内容 |
| 计划版本 | 0.1，2026-10-21 |
| 依据 | 用户提供的《Usami 2.0 总体重构方案》及当前代码核查 |
| 代码基线 | hjy8848/Usami，feature/after-sales-dialogue-protocol-v3 |
| 基线提交 | c47565e7ff4b14e1fa402e47a1c16d1bcafb99e3 |
| 第一实施领域 | 电商与售后；其他七领域维持原有运行与回放能力 |
| 本轮交付范围 | 详细改动计划，不实施业务重构，不启动模型实验 |

## 1. 我准备把系统改成什么

我会把 Usami 2.0 做成两个可以独立使用、又能连接起来的部分。

**第一部分是业务 Benchmark。** 它提供可以查询、操作、发生外部变化的真实业务世界，以及自然的顾客交互和独立评估。任何 Service Agent 都可以接入，不要求使用我们的 Designer、Skill 或进化算法。

**第二部分是自主进化系统。** Designer 依据过去的训练表现设计新情境与挑战；Service 自主处理业务；系统保存和分析决策；Learner 提出经验更新；Validator 在独立实例中验证；被接受的版本进入下一代。

连接两者的是一组版本化的数据契约，而不是一段把所有功能揉在一起的 Demo。

    Benchmark：
    业务规则 + 世界构建 + 顾客情境 + 工具执行 + 独立评估 + Replay

    进化：
    训练证据 → Designer / Learner → 候选经验 → 独立验证 → 下一代

### 1.1 第一个必须实现的具体能力

第一条完整链路要回答一个直接的问题：

> 顾客买了两件商品，希望退掉其中一件，另一件换成满足规格、预算和送达期限的替代商品。Service 能否调查信息、比较方案、取得真实确认，并正确执行两项业务？

这个任务里，错误可以来自商品选择、金额、期限、目标遗漏或交易确认。任务不要求某条唯一的工具调用顺序。

实现这一条链路后，再逐步加入动态库存、独立诊断、经验更新和多代运行。不会先搭出一套空的多 Agent 框架，再等待业务内容填进去。

### 1.2 整个重构的四条边界

1. 旧实验、旧业务版本和旧 Replay 解释保持可恢复；新实验显式声明 2.0 协议。
2. 业务世界新增能力必须由确定性模型、执行逻辑和独立规则支撑。
3. Agent 可以改变挑战与经验，不能改变裁判、权限真值、最终测试数据。
4. 工程跑通、经验更新、局部修复、泛化提升分别验收，不能互相替代。

## 2. 当前代码给了我们什么，具体缺少什么

以下是本次对基线源码的核查结果，不把方案中的设想算成已实现能力。

| 当前实现 | 已有能力 | 2.0 的具体缺口与处理 |
|---|---|---|
| [usami_aftersales/models.py](../../usami_aftersales/models.py) | Product、订单行、工单、报价、退货、退款、替换记录 | Product 只有单一 stock；没有独立 SKU、多仓库存和替代规格模型；建立新版本电商模型 |
| [usami_aftersales/transitions.py](../../usami_aftersales/transitions.py) | 退款、换货、补发的真实状态变化 | 换货/补发仍围绕原 product_id；报价不能表达多候选 SKU、仓库、差价与部分数量；新业务执行器补齐 |
| [usami_dialogue/engine.py](../../usami_dialogue/engine.py) 的 DialogueSession | 独立 Customer 身份、单次操作授权、报价展示、事件轨迹 | 每次写操作绑定精确 grant，和自然的业务委托不同；2.0 新运行时分离委托、准备和成交 |
| [usami_dialogue/agents_v3.py](../../usami_dialogue/agents_v3.py) | v3 模型交互、明确的报价引用、Customer 可见业务进度 | 不直接修改旧运行语义；在新运行时提供自然业务交互 |
| [usami_dialogue/preflight.py](../../usami_dialogue/preflight.py) | 身份、已知信息、跟进请求等静态兼容检查 | 不能证明完整对话可完成；增加独立的交互可达性证书 |
| [usami_benchmark/abstract_challenges.py](../../usami_benchmark/abstract_challenges.py)、[grounder.py](../../usami_benchmark/grounder.py) | 抽象挑战、在现有冻结世界内绑定实体 | 不能根据约束创造新的 SKU、库存与物流关系；新增 World Builder，保留原冻结世界发现路径 |
| [usami_benchmark/designer_batch.py](../../usami_benchmark/designer_batch.py) | 世界索引、批量提案、验证与失败留档 | 作为旧对照和可复用交互组件；不让 Batch Designer 承担新世界全部内部字段的生成 |
| [usami_dialogue/tasks.py](../../usami_dialogue/tasks.py) | 已有对象目标、新建对象目标、拒绝目标和证书 | 单字段目标不足以表达费用、规格、数量、时间和多对象联合约束；新 TaskSpec 增加业务谓词 |
| [usami_dialogue/decision_audit.py](../../usami_dialogue/decision_audit.py) | 逐操作事实审计、原生分类、Replay 绑定、同任务配对诊断 | 目前明确不证明因果根因；新增观察重建、合法替代与局部分叉验证 |
| [vast_coevo/skills/](../../vast_coevo/skills/) | SkillPatch、静态检查、不可变 LibrarySnapshot、检索和渲染 | 直接复用；Episodic Memory 和 Working Memory 分别增加清晰的数据契约 |
| [vast_coevo/skills/retriever.py](../../vast_coevo/skills/retriever.py) 的 SkillContext | domain、public_text、intents、available_tools | 增加独立的决策状态投影层；不能把隐藏 Oracle 特征塞进检索 |
| [vast_coevo/reflection/reflector.py](../../vast_coevo/reflection/reflector.py) | 单次 Reflection、训练证据边界和结构化 Patch | 其默认 boundaries 仍描述“每次写入精确授权”；新协议显式传入新业务契约，不改历史输入默认值 |
| [vast_coevo/evolution/evolvers.py](../../vast_coevo/evolution/evolvers.py) | Customer 静态选代、Service 默认动态验收、NOOP、失败保留父版本 | 复用快照与选代机制；新增 2.0 适配，不直接用旧 valid_actions 等聚合量评价新业务学习 |

这里必须区分框架和实际入口：Evolver 的 Service 动态验收默认开启，但 Frozen Controller 的当前配置可以关闭两方动态门控；After-sales 三任务 Live Smoke 也显式关闭动态门控。此外，现有 aftersales_coevo_live.py 的“v3”是外层实验协议，它导入的仍是旧 TaskRunConfig / run，不能等同于 agents_v3.run_v3。新 2.0 入口会直接接新 Runtime，并在 Manifest 写明实际执行协议和选代策略，不从文件名推断。

### 2.1 复用与新建的判断

**直接复用：** 哈希、不可变记录、模型调用客户端、原始请求日志、Skill Schema、SkillPatch、LibraryStore、静态安全校验及证据归档。

**通过适配复用：** 通用 Engine、Replay 机制、Reference 证书思想、EpisodeEvidence、Service Gate 的配对运行和版本发布结构。

**必须新增：** 丰富电商模型、业务委托与报价同意模型、世界约束构建、联合业务目标、局部决策证据、Episodic Memory、当前任务工作状态。

**不能假装直接复用：** 旧售后单商品状态机、旧精确 grant 交互语义、只覆盖旧字段的任务搜索器。给它们换个名字不会得到 2.0。

## 3. 模块与版本组织

我建议新增一个明确的实验性命名空间 usami_v2，而不是继续在旧 agents_v3.py 中累积 v4、v5、v6 分支。

    usami_v2/
      commerce/
        models.py              # 商品、SKU、库存、订单、账务、报价、履约
        operations.py          # 真实业务工具与参数
        transitions.py         # 实际状态变化
        reference.py           # 独立合法性与预期结果
        invariants.py          # 结构、数量、资金与权限不变量
        adapter.py             # 接入通用 Engine 的边界
      scenarios/
        schema.py              # ScenarioSpec 与 TaskSpec
        builder.py             # 约束生成合法世界
        solver.py              # 确定性枚举/可选求解器接口
        certification.py       # 世界、业务与交互可达性证明
        events.py              # 冻结外部事件规则
        designer.py            # 两阶段 LLM Designer
        signatures.py          # 业务决策结构签名
      runtime/
        session.py             # 新交互会话与可信授权转换
        delegation.py          # 顾客业务委托
        consent.py             # 报价展示、明确同意、撤销与失效
        customer.py            # Customer 接口、LLM 实现和确定性夹具
        observations.py        # 各角色可见投影
        working_state.py       # 当前目标、事实来源、报价和待处理事项
        runner.py              # 独立业务任务执行
      evaluation/
        outcomes.py            # 终局目标、硬约束与合规
        replay.py              # 2.0 解释器与原生轨迹验证
        pairing.py             # 冻结条件下的配对运行
        metrics.py             # 分开报告指标
        partitions.py          # 数据用途和来源隔离
      analysis/
        decisions.py           # 决策前观察、动作、结果与目标状态
        alternatives.py        # 独立合法替代枚举/搜索
        counterfactual.py      # 从真实前状态分叉执行
        dependencies.py        # 错误依赖与下游影响
      learning/
        routing.py             # 错误是否可学，适合改哪个组件
        episodes.py            # 经验证的案例记忆
        retrieval.py           # 仅用公开决策状态的检索
        learner.py             # 调用现有 Reflector，形成候选更新
        snapshots.py           # Skill + Memory + 策略的组合版本
      evolution/
        models.py              # Manifest、GenerationRecord、SelectionRecord
        controller.py          # 单条递归训练链
        validation.py          # 2.0 候选验收适配
      cli.py

这份目录是模块职责清单，不要求第一个 PR 把所有空文件都建出来。只在相应功能开始实现时新增文件。

旧八领域注册表维持原语义。新领域先使用独立 domain 标识 commerce，业务版本 commerce-2.0.0；研究协议使用 usami-rsi-v2。是否正式并入统一 Benchmark 注册表，在新领域可以独立运行后再决定。

沿用当前 Python / Pydantic 技术栈，首轮不顺手提高全仓 Python 最低版本。Hypothesis 作为测试依赖，求解器作为可选依赖；真正引入前验证与现有支持版本兼容，并锁定运行环境。

### 3.1 一次运行必须固定哪些版本

Manifest 至少固定：

- source_commit，以及必要的源码归档哈希；
- business_rules_version、world_schema_version；
- scenario_dsl_version、task_schema_version、event_schedule_version；
- customer_runtime_version、authorization_policy_version；
- oracle_version、analyzer_version、selection_policy_version；
- 模型与采样参数、工具 Schema 哈希、Prompt 组装版本；
- Skill、案例记忆、检索策略、Working Memory 策略的选中版本；
- 世界、身份、顾客情境、任务、数据分区、随机种子与总预算。

同一个 JSON 字段在新版本里有新语义时，必须切换协议版本。不会通过修改默认值重新解释历史运行。

### 3.2 先固定哪些边界接口

以下是拟定接口，先写成 Schema 与契约测试，再实现内部逻辑：

| 接口 | 输入 | 输出与保证 |
|---|---|---|
| build_world | ScenarioSpec、Seed、BuildBudget | BuildResult：状态、FrozenBusinessWorld、约束证据或失败原因 |
| certify_task | 冻结世界、TaskSpec、CustomerScenario、ProofBudget | CertificationResult：业务证书、交互证书、私有见证引用或 UNKNOWN |
| run_episode | 认证任务、SystemSnapshot、Customer、Service、RunBudget | EpisodeRecord：真实模型记录、事件、结果、成本和密封哈希 |
| replay_episode | EpisodeRecord、版本化 Adapter、可信源数据 | ReplayResult：逐事件重建、权限重算、结果和完整性验证 |
| analyze_decisions | 已 Replay 的 Episode、AnalysisBudget | DecisionRecords：观察事实、替代证据、依赖和不确定性 |
| propose_update | 允许的训练证据、父 Snapshot、LearningPolicy | CandidateUpdate：单次提案、静态结果或 NOOP，不自动发布 |
| validate_candidate | 父/候选版本、冻结开发集、ValidationPolicy | SelectionRecord：配对证据、接受结论、原子选中版本 |
| run_generation | 上代选中版本、训练配置和预算 | GenerationRecord：全部尝试、证据消费索引和下代版本 |

认证器输出的私有见证只给验证/回放层。Runner 给 Service 的是公开工具、任务对话和合法观察，不是整个 CertificationResult。

## 4. 第一项具体实施：电商世界与交易模型

### 4.1 第一版的业务范围

第一版实现单商家、单币种、多商品订单、多 SKU、多仓库存、退款/换货/补发、部分数量、审批和退货事件。

暂不加入多币种换汇、跨商家清分、复杂税制、真实物流或真实支付系统。这些不是当前验证局部业务决策学习的必要条件。

所有金额使用整数最小货币单位，时间使用有时区的虚拟时间。外部支付与物流提供确定性模拟，不会发生真实扣款或发货。

### 4.2 数据模型怎么改

| 模型 | 关键字段与约束 | 能产生的业务决策 |
|---|---|---|
| Product / SKU | 品牌、型号、规格、兼容属性、替代关系、售后政策版本 | 看似相似的商品是否真的满足需求 |
| InventoryBalance | sku_id、warehouse_id、on_hand、reserved、shipped | 有货、可承诺与已预留不是同一概念 |
| DeliveryOption | 仓库、方式、费用、预计到达时间、适用区域 | 便宜但晚，或按时但有额外费用 |
| Order / OrderLine | 原购买 SKU、数量、行级实付分摊、已退/已换/待处理数量 | 部分处理、多诉求及重复申请 |
| RemedyCase | 订单行、处理数量、证据、资格、审批、已完成阶段 | 是否允许处理，以及还差什么条件 |
| BusinessQuote | 目标 SKU、数量、仓库、配送、退款/补款、有效期、条款版本 | 哪个方案能被真实执行和确认 |
| Consent | 顾客、报价条款哈希、委托范围、同意时间、状态 | 顾客到底同意了什么 |
| PaymentLedger | 订单行分摊、已退款、补款、渠道、幂等键 | 不能超额退款或重复支付 |
| Fulfillment / Return | 实际替换商品、数量、发货/退货状态 | 不能只把订单枚举改成“成功” |
| CustomerScenario | 真实已知信息、目标、硬约束、软偏好、可接受妥协 | 业务方案是否真正满足顾客 |

订单行不会只依赖一个 refunded/exchanged 枚举表达全部业务。数量要能分解成未处理、处理占用、已退款、已替换等互斥部分，并由数量守恒校验。

优惠先在原订单中形成冻结的行级实付分摊；退款依据可退实付余额计算，不能直接拿标价乘数量。首版规则要把差价正负、补款与退款渠道写清楚。

### 4.3 工具怎么提供

第一版公开工具按职责划分：

| 信息获取 | 业务准备 | 交易与履约 |
|---|---|---|
| list_customer_orders | open_remedy_case | commit_accepted_quote |
| get_order_details | verify_submitted_evidence | schedule_authorized_return |
| search_catalog | request_policy_review | release_accepted_refund |
| get_sku_details | prepare_remedy_quote | cancel_pending_commitment |
| get_inventory | refresh_quote | |
| estimate_delivery | | |
| get_refundable_balance | | |
| get_case_status | | |

名称是拟定接口，最终由业务契约测试固定。每个工具都要有严格参数、权限级别、确定性返回、状态变化、错误代码和对应的 Reference 判断。

暂不提供“自动选择最优方案”的万能工具。查询可以返回真实候选数据，Service 自己组合规格、预算和期限作判断。prepare_remedy_quote 也不能偷偷替模型换成正确 SKU。

多商品第一版允许逐行准备、逐项确认和部分成交。批量原子成交以后再加；不能在未实现事务语义时，假装一个列表调用就是全有或全无。

### 4.4 业务真值与实际执行怎么保持独立

实际 transitions 负责执行状态变化；reference 负责从执行前状态独立判断是否允许、应出现哪些结果。Oracle 再比较真实结果与规则。

可以共享数据 Schema、不可变政策配置和基础整数运算定义；不能让 Reference 调用实际 transitions，再用两份相同结果宣称独立验证。

### 4.5 两类不变量与 Sandbox

**结构性约束**包括身份不可伪造、对象引用有效、事件链完整、账本平衡及操作参数类型。这些约束在所有模式下维持。

**业务约束**包括售后资格、可退额度、规格/期限、审批和交易确认。Reference 模式阻止不合法操作；研究用 Sandbox 可以观察在可表示范围内执行出的违规，并保留独立判断。

Sandbox 不得把无权访问的其他顾客数据变成可读数据。出现污染状态后，后续样本必须标注依赖关系或不可评估，不能继续当成正常世界里的独立失败。

新模式边界写入 2.0 Manifest，不改变旧 Sandbox 的历史解释。

### 4.6 验收

- 相同 Seed 和约束得到相同世界。
- 合法方案可以真实成交；不合法方案有独立可验证的拒绝理由。
- 数量、库存、退款额度、差价和幂等性通过例子测试与属性测试。
- 故意实现错误变更的测试夹具能被独立 Reference / Oracle 抓住。
- 至少存在两个合法结果时，两种结果均能通过评分，不强制唯一 SKU。

## 5. 第二项具体实施：自然委托、报价与 Customer

### 5.1 三层权限如何落地

| 层级 | 独立来源 | 生命周期 | 示例 |
|---|---|---|---|
| 身份与数据范围 | Harness 在任务开始前绑定 | 会话或已登记身份周期 | 可以读取自己两笔订单，不能读取别人订单 |
| 业务委托 | 冻结顾客情境 + Customer 明确表达的业务需求 | 委托有效且未撤销期间 | 调查损坏商品、验证已提供材料、准备替换方案 |
| 交易同意 | Customer 对实际展示报价的明确接受 | 绑定条款与有效状态，成交后消耗 | 接受 SKU D、补款 20 元、周五送达 |

准备操作是否需要单独同意，由业务契约逐项登记。例如会占用稀缺库存的 reservation 不能简单归入无成本准备。

### 5.2 怎样接到现有 Engine

通用 Engine 仍接收内部可信 Request。新 Runtime 根据**已经独立存在的身份、业务委托或报价同意**生成授权证明，再为当前操作注册 Request。

不能因为 Service 请求执行了某个工具，就自动构造一个“Customer 已同意”的 Request。这与此前 Playground 参数自动授权的问题完全不同。

内部精确绑定仍可以存在，用于审计；Customer 和 Service 不需要手工拼接 action_id 或 grant JSON。

新 Oracle 必须从冻结身份、原始 Customer 事件、已展示报价和前状态独立重建委托与同意，再核对内部 Request。不能直接信任 Runtime 写出的 granted=true。若底层 Engine 的证据字段不足，优先在新 Session 外层保存 AuthorityProof，并由版本化 Adapter 关联；不改旧 Request 的授权定义。

### 5.3 报价同意绑定什么

Consent 的条款哈希至少覆盖：

    customer_id
    order_id / line_id / quantity
    case_id
    remedy_type
    target_sku / warehouse / delivery_terms
    refund_amount / extra_charge / payment_channel
    return_requirement
    quote_revision / valid_until

报价先由真实业务工具生成。Service 使用 present_quote(quote_ref, message) 展示；Customer 对当前实际展示报价接受、拒绝或继续询问；Harness 记录绑定。

自然语言“可以”只在唯一、清楚且已展示的当前报价上下文中允许形成确认。多报价歧义、条件性同意、只说“谢谢”都不能默认成交。Customer 的结构化输出保留极小的 offer_response 字段，但报价明细和哈希由系统绑定。

顾客改了数量、SKU、配送或价格，或者报价失效时，原同意不能沿用。若业务规则要求退货到账后单独确认释放退款，Runtime 展示这一新承诺的真实条款并单独获取同意。

finish 与本轮接受冲突时，Runtime 必须让 Service 有机会处理明确的待执行承诺，或返回可恢复的澄清；不能静默吞掉同意，也不能把结束对话变成新增同意。

### 5.4 Customer 的实现

Customer 接收：

- 认证身份对应的私人情境；
- 自己知道的订单、商品问题和事实；
- 允许改变的偏好、明确的硬约束；
- 当前真实对话与合法公开的业务进度；
- 当前实际呈现的报价。

它不接收正确 SKU 列表、Reference 路径、Oracle 分数和隐藏审批结果。

确定性层检查事实披露来源、偏好范围、当前报价绑定和结束语义。它可以要求格式澄清，不能替 Customer 决定“接受哪个更正确”。

确定性 Customer 保留为工程夹具；真实 LLM Customer 是正式交互实现。两者共用协议与 Fidelity 检查，但报告分开。

### 5.5 新增交互可达性证书

任务认证除了证明“业务操作有解”，还要证明“所选 Customer 情境确实能够提供必需信息，并允许形成必要的交易同意”。

证书包含两个不同结论：

1. 业务可达：存在合法业务执行路径。
2. 交互可达：所需事实、可接受选项和确认状态在登记顾客契约中可实现。

这只是存在性证明，不保证某个随机 LLM Customer 必然合作或成功。真实运行中的 Customer 失真仍独立记录。

## 6. 第三项具体实施：两阶段 Designer 与世界构建

### 6.1 第一阶段提交 ScenarioSpec

Designer 使用可组合约束，而不是指定题型编号，也不生成完整 World JSON。

拟定输入示意：

    protocol: commerce-scenario-v1
    customer:
      order_count: 1
      line_count: 2
    catalogue:
      replacement_pool_min_size: 5
    constraints:
      - exists: compatible_candidate
        where: [within_budget, arrives_before_deadline]
      - exists: compatible_candidate
        where: [cheaper, arrives_after_deadline]
      - exists: compatible_candidate
        where: [arrives_before_deadline, exceeds_budget]
      - exists: candidate
        where: [incompatible_required_attribute]
    resources:
      warehouse_count: 2
    event_policy: registered_before_execution

具体字段最终由 Schema 固定。这里的意思是：允许 Designer 描述实体、关系、数量、区间与联合条件；业务法规、售后资格公式和评分代码不属于可修改字段。

首版 DSL 的组合元件包括实体变量、属性比较、关系、计数、金额/时间约束、事件触发约束。它们可以自由组合，不等于几套硬编码退款模板。

### 6.2 World Builder 怎么生成

流程是：

    Schema 校验
      → 约束规范化
      → 生成/求解候选业务数据
      → 校验业务不变量
      → 保存约束满足证据
      → 冻结世界与事件规则

先实现有上界的确定性构造和枚举；将求解器封装成接口。若金额、库存、时间组合使枚举成为明确瓶颈，再接入一种约束求解器，不同时引入 Z3 和 OR-Tools 两套依赖。

Builder 返回 SAT、UNSAT 或 UNKNOWN，并记录预算。超出搜索预算不能当成“世界无解”，更不能自动放宽顾客约束。

Designer 可以收到是哪项结构约束冲突，但不能收到后续任务的隐藏参考执行路径。

### 6.3 第二阶段提交 TaskSpec

世界冻结后，Designer 再选择其中现有身份与实体，定义：

- 顾客自然请求；
- 多个业务目标与目标间关系；
- 必须满足的硬约束；
- 允许妥协或排序的软偏好；
- 信息与确认需求；
- 可接受的完成、替代方案或拒绝条件。

此阶段不能继续改世界。如果世界不足以支持想出的任务，返回明确失败，或开启一个新的场景构建尝试；两次尝试分别留档。

### 6.4 新 TaskSpec 怎么评价多种正确答案

TaskSpec 使用受限业务谓词，例如：

    all_of:
      - line_refund_quantity(line_B) == 1
      - fulfilled_replacement_quantity(line_A) == 1
      - compatible(actual_replacement(line_A), customer.required_attributes)
      - actual_extra_charge(line_A) <= customer.max_extra_charge
      - promised_arrival(line_A) <= customer.deadline
      - has_valid_consent_for_each_commitment()
      - unaffected_order_quantities_preserved()

谓词通过白名单解析，不执行 Designer 提交的 Python。

软偏好如果只是“更喜欢早到”，合法但较晚的方案不能自动算业务错误。只有任务预先定义了最优性要求和可计算比较标准，才能报告可验证的次优选择。

“没有可接受方案”通过约束或有界完整搜索证明；没有证明时标 UNKNOWN，不用拒绝目标掩盖任务未获证。

### 6.5 动态事件怎样冻结

事件由虚拟时间或登记的业务状态触发，例如审批申请后固定延迟返回、某批库存按计划失效。触发器不能读取模型正确与否、Oracle 标签或未来 Service 答案。

两个配对 Agent 使用相同外生事件过程与随机种子。由于动作不同，事件被观察到的业务阶段可以不同，不能为凑结果在执行后移动事件。

保存事件未触发、已触发、重复触发被拒绝等记录；一次超时或模型重试不能让业务时间偷偷前进。

### 6.6 多样性与预算

自然任务池按冻结业务分布采样；主动探索池由 Designer 根据训练证据设计。两者均保存来源。

结构签名基于目标数、规格/金额/时间耦合、资源竞争、信息依赖、确认阶段及事件关系。改 ID 不增加结构多样性。

Designer 不被要求“本轮必须发现权限错误”。它可以从成功轨迹中的恢复、重复查询或方案权衡入手。成功样本的可疑挣扎先作为假设，不直接贴错误标签。

提案修正是显式预算项：每个尝试保留初稿、验证反馈和修订。修正次数、探索调用、求解预算在运行前固定；编译器只修格式归一化，不能替模型挑选正确目标。

## 7. 第一条端到端样例具体怎么做

我会用下面这个完全可解释的样例作为首条业务链路验收，不把它当作最终题库或训练脚本。

顾客有两条订单行：A 是损坏的设备，原实付 200 元；B 是需要退回的一件配件，实付 20 元。顾客要求 B 退款，A 换成兼容接口的设备，补款不超过 30 元，三天内送达。

| 候选 | 兼容规格 | 补款 | 送达 | 硬约束结论 |
|---|---|---:|---|---|
| SKU A | 不兼容 | 0 元 | 两天 | 规格不满足 |
| SKU B | 兼容 | 无需补款 | 六天 | 超期 |
| SKU C | 兼容 | 40 元 | 两天 | 超预算 |
| SKU D | 兼容 | 20 元 | 两天 | 可接受 |
| SKU E | 兼容 | 10 元 | 三天 | 可接受 |

D 和 E 都允许通过任务评分。若顾客未要求唯一最优结果，Service 选择任一方案并取得确认都可以。

### 7.1 实施顺序

1. 先由确定性 Builder 创建并冻结这个世界。
2. Reference 从初态证明至少一条合法业务路径。
3. Customer 契约证明必要事实、偏好和确认都可以出现。
4. 工程夹具通过公开业务工具完成两个目标，保存真实账本和履约记录。
5. 加入错误夹具：选错接口、超期限、重复退款、遗漏 B、未经确认成交。
6. 独立 Oracle 对每个夹具给出预期结果；Replay 可以发现篡改。
7. 再接入真实 Service 和真实 Customer，观察自然发生的业务错误。

工程夹具用于检查环境，不计为 AI 自主学习或模型实验。随后 Designer 要能从 DSL 自主构造具有不同结构的情境，不要求复刻这张表。

## 8. 第四项具体实施：独立结果评估与局部诊断

### 8.1 Outcome & Compliance Oracle 的输出

每条运行至少保存：

| 字段 | 含义 |
|---|---|
| final_goal_reached | 登记业务终局是否达到 |
| per_goal_results | 每项诉求的实际结果与未完成原因 |
| hard_constraints_satisfied | 规格、金额、时间、数量等硬约束 |
| compliance_violations | 真实执行的业务违规 |
| invalid_attempts | 被拒绝的不合法操作尝试 |
| false_rejections | 有客观替代证据支持的错误拒绝 |
| customer_fidelity | 顾客是否遵守登记情境 |
| protocol_and_transport_errors | 格式、工具或外部服务故障 |
| strict_task_success | 业务结果、合规和有效结束共同成立 |
| evaluation_status | VERIFIED、UNRESOLVED 或 INVALID_EVIDENCE |

最终退款成功但中途违规，必须保留 final_goal_reached=true 与 strict_task_success=false 两个事实。Service 提出错误动作但被 Reference 拦截，也不能算成功执行的违规。

### 8.2 每个局部决策记录什么

DecisionRecord 至少包括：

    decision_id / episode_id / event_id
    prestate_hash / observation_hash / customer_context_hash
    exact_model_request_hash / visible_fact_sources
    goal_progress / active_constraints / presented_quote
    selected_action / parameters / actual_tool_result
    state_delta / poststate_hash / native_oracle_facts
    alternative_search_status / alternatives / proof_refs
    attribution_level / dependency_edges / uncertainty

保存完整世界用于独立裁判，但 Agent 当时看到什么必须单独重建。世界里存在一个正确 SKU，并不代表 Service 已经查询到它。

### 8.3 诊断结论分三级

1. **观察事实：** 实际选择了什么，哪些规则不满足，是否被拦截，改变了什么。
2. **局部替代获证：** 从同一个前状态执行另一真实合法动作，可以满足哪些局部约束。
3. **机制修复获证：** 候选经验在独立配对任务中减少对应错误，并通过正常行为回归。

LLM 提出的“可能因为没注意期限”保留为 hypothesis，不升级为事实。一个 Oracle 错误码也不自动等于一个独立根因。

### 8.4 局部反事实具体怎么执行

第一版只实现有界、可重复的局部验证：

1. 从真实前状态和事件游标恢复分叉，不重生成世界。
2. 冻结相同身份、委托、已取得信息、虚拟时间和当前有效报价。
3. 只枚举该决策阶段的白名单替代动作，例如另一个已查询 SKU 或刷新报价。
4. 使用独立 Reference 筛查，再通过真实 Engine 执行。
5. 比较硬约束、资源变化、费用和局部目标。
6. 保存替代动作、轨迹、规则版本和可重放证书。

如果一个更好的动作需要新信息，诊断要报告“当时可以合法继续查询”，不能假装模型已经知道答案。

如果必须继续多轮 Customer/Service 才能判断终局，则局部单步不能证明整体成功。完整后续配对另算运行预算，并明确 Customer 条件、采样和不确定性。

### 8.5 如何避免错误数膨胀

建立依赖边：错误报价 → 无效确认 → 错误成交 → 污染状态下后续失败。它们保留各自事件，但是否属于同一机制要依证据判断。

原始次数、独立规则、诊断机制和获证根因分别统计。未完成全部必要前提排除的诊断，不算“新增独立根因”。

重复查询只有在状态、参数、可见信息和任务目的等价，而且没有事件或必要刷新时，才标为确定性重复。查询次数多本身不构成错误。

## 9. 第五项具体实施：Experience Learner 与三种记忆

### 9.1 先把可学习对象限定清楚

第一版冻结模型权重、工具、世界规则、Oracle、Customer 协议和 Working Memory 的基础机制。

允许学习：

- Designer 的声明式探索 Skill；
- Service 的声明式决策 Skill；
- 经验证、去实例化后的 Episodic Memory 条目。

Working Memory 先作为固定工程能力，帮助 Agent 看见当前任务状态。以后允许演化其受限策略时，再单独开启实验版本和消融，不把一次 Runtime 修复混入 Skill 学习收益。

如果 Working Memory 在早期无学习诊断之后加入，早期记录保留为工程证据；新的 Skill 配对必须让父版本和候选都使用相同的 Working Memory 配置重新运行，不能跨运行时直接比较。

### 9.2 三种记忆分别如何实现

| 组件 | 内容与来源 | 生命周期 | 验证方式 |
|---|---|---|---|
| Skill Memory | 现有 DecisionSkill / DesignerSkill，带触发条件和适用范围 | 跨任务、不可变版本 | 现有 StaticSkillGate + Service 候选动态验证 |
| Episodic Memory | 实际情境特征、错误/成功决策、已验证替代、证据引用 | 跨任务、版本化案例库 | 来源 Replay、字段去泄漏、案例与结论一致性 |
| Working Memory | 当前多目标、已获事实、未完成事项、待确认承诺、报价有效状态 | 仅当前 Episode | 真实工具结果和 Customer 消息驱动的确定性更新 |

Working Memory 不得调用 Oracle 确认“任务已得分”，也不能偷偷替 Service 增加新业务请求。它记录顾客实际表达的目标以及已经观察到的执行结果。

### 9.3 Learner 怎样决定该学什么

先通过确定性 eligibility 检查：

- 证据是否 Replay 完整；
- 错误来自业务决策、Customer 失真还是协议/传输；
- 有无足够信息形成可迁移结论；
- 是否属于污染状态的下游结果；
- 有无已经存在的相同经验及证据。

随后允许一次真实 Reflector 提案。输出可以是 SKILL_PATCH、EPISODE_PATCH 或 NOOP；接口故障只形成工程 issue，不允许模型自动改代码、规则或裁判。

经验必须包含触发条件、适用领域、观察与推断的区别、建议行为、证据来源和限制。禁止固定订单 ID、测试集标签和“遇到此类请求全部拒绝”。

Skill Patch 继续使用现有 SkillPatch / apply_patch / LibraryStore。Memory Patch 使用独立 Schema，不给旧 SkillPatch 强塞另一种语义。

### 9.4 状态驱动检索怎么做

每个关键业务阶段，Runtime 从**公开的当前执行上下文**构建 DecisionContext：

    domain / phase / active_goals
    entity_types / observed_constraint_types
    available_tools / valid_quote_status
    evidence_freshness / working_state_hash

先用确定性标签、字段和规则匹配选择少量 Skill / 案例；只有出现可测量的召回问题，再评估向量检索。

记录每次检索输入、命中条目、版本、内容哈希、最终注入文本和输入 Token。新经验是否真正参与决策，从真实请求核验，而非只看 Snapshot 哈希变化。

持久案例不携带可执行指令层级标签，不把历史对话当系统指令。案例里的私有原始标识通过本次绑定解析，不跨顾客复用授权。

### 9.5 组合 Snapshot

定义 SystemSnapshot，引用而不复制各组件：

    service_skill_snapshot_hash
    designer_skill_snapshot_hash
    episodic_memory_snapshot_hash
    retrieval_policy_hash
    working_memory_policy_hash
    runtime_protocol_hash
    parent_system_snapshot_hash

选代发布一个完整组合版本。候选失败保留父版本；中途异常不能出现“Skill 已切换、Memory 仍是旧版”的半发布状态。

## 10. 第六项具体实施：候选验收与递归训练

### 10.1 Service 候选怎么验收

复用现有 Service 验收的核心要求：修复真实错误、保持合法完成与正确拒绝、不增加授权异常、证据可以 Replay。

新协议增加面向局部机制的配对证据，但不会在旧 Gate 中悄悄改默认公式：

1. 静态与来源校验：候选内容合法，范围合理，来源非 Held-out。
2. 目标修复：独立实例中，实际到达相关决策机会，候选减少对应错误。
3. 正常回归：合法业务仍完成；不能以不操作避免所有违规。
4. 迁移与代价：检查新约束组合、其他机制、Customer/Service 分别成本。
5. 根据冻结政策选择 ACCEPT、REJECT 或 INCONCLUSIVE；后两者均保留父版本。

没有到达目标决策机会，记 NOT_REACHED，不算修复成功。父版本在验证中没有复现目标错误，也不能声称候选修复了它。

阈值、样本量、配对方法和最低机会数量必须在正式运行前写入 Policy。不会把随意选的“五个百分点”写成通用科学标准。

这意味着 2.0 正式学习入口会显式选择新的 Service 验收策略；当前 evidence_only_static 或关闭门控的 Smoke 仍保持原意。工程 Smoke 可以验证更新/继承，但只有独立验证通过的候选才在新的研究运行中被记作“经效果验收接受”。

### 10.2 Designer 和 Customer 怎么选代

Customer 在新研究链路中是固定模拟器，不参与 CustomerEvolver。

Designer Skill 仍先使用当前的静态安全选代方式，探索收益单独诊断；不借 2.0 重构恢复旧 Customer Performance Gate。合法任务认证是题目能否进入执行的条件，不等于 Designer Skill 的性能验收。

如后续要研究 Designer 动态选代，必须显式选择新的 Designer 策略版本，并独立比较。Service 经验的动态验收与 Designer 探索诊断不会混成同一“更新成功率”。

### 10.3 每代 Controller 的实际顺序

    加载本代实际选中 SystemSnapshot
      → Designer 读取允许的训练记忆
      → 提交 ScenarioSpec
      → Builder 生成并冻结世界
      → Designer 提交 TaskSpec
      → 独立业务 + Customer 交互认证
      → Customer–Service 执行本代挑战
      → Oracle + Replay + Decision Analyzer
      → Designer Reflection + 静态选择
      → Service Learner + 静态检查
      → 独立机制/回归验证
      → 原子保存候选、验收和本代选中版本
      → 下一代

自然业务任务也可以作为登记的训练输入，双方均可读取其允许证据。成功、失败、被恢复的错误和无法评估的情况全部保留。

本代正常执行证据必须进入双方的 Reflection 证据索引。不得只保存额外研究比较，却忘记把真实探索错误提供给 Service。

训练循环不默认执行四组交叉，不在本代用新 Designer 再出一套题来比较新旧版本。新 Designer 在下一代自然实践。

### 10.4 独立评估

训练后加载任意保存的 Designer / Service / Memory 组合，运行独立评估。该入口不能调用 Reflection、发布经验或修改选中版本。

固定 Customer 与进化 Designer 的训练条件、世界分布、模型、Prompt、Runtime、总预算要一致。节省的调用不能只转给某一个比较组。

旧实验使用旧协议；重构后必须创建新运行，不重新解释过去的结果。

## 11. 训练、验证与最终测试怎么隔离

| 集合 | 可供谁读取 | 是否影响更新 | 来源要求 |
|---|---|---|---|
| 训练探索集 | Designer、Learner、分析器 | 是 | 自主挑战与登记自然业务任务 |
| 局部机制开发验证 | Validator；模型只见本题正常输入 | 是 | 与训练不同的具体世界和订单 |
| 常规开发回归 | Validator；模型只见本题正常输入 | 是 | 正常完成、正确拒绝和负迁移实例 |
| 最终 Frozen Held-out | 训练结束后的评估入口 | 否 | 独立种子、来源族与预登记业务分布 |

不仅排除相同 world_hash，还要保存 ScenarioSpec 来源、生成谱系和结构签名。ID 重命名不能绕过重复检查。

正常分布与主动挑战分别报告，不能用全是攻击题的样本代表综合业务能力。

验证结果反复用于选代会产生自适应过拟合。每次候选消耗哪些验证实例必须登记；更新评估池时切换版本，最终测试不能补进案例记忆。

## 12. 实验怎么分层推进，避免再次烧预算却测不清楚

### 12.1 L0：纯工程验证

费用为零，不调用模型：

- 一条多商品链路，至少两个合法方案；
- 动态报价失效、取消、重复确认和退款边界；
- Customer 事实与确认兼容检查；
- Oracle 能识别错误夹具；
- 完整 Replay 与篡改检测；
- 候选版本的发布、回滚与跨代继承。

### 12.2 L1：无学习真实基线

先少量独立任务，不运行 Reflection。

建议首个诊断批次为 8 个冻结实例：不同实例覆盖规格/预算/期限权衡、多目标、报价变化和应正确拒绝的情形。这个数量只用于检查错误分布，不用于显著性结论，也不是新建固定题型池的要求。

先用确定性 Customer 隔离 Service，再用同一协议的 LLM Customer 检查自然交互。两种结果不混算。

如果主要失败仍来自格式、Customer Fidelity 或可达性缺口，停在工程层修复，不自动进入经验生成。

### 12.3 L2：一轮局部学习与独立配对

使用 L1 中可学习的真实训练证据，生成至多一个候选更新；在预冻结的新实例中对父版本与候选版本配对。

先回答三个问题：目标机制有没有减少，正常业务有没有退化，成本和新问题有没有增加。没有可靠改善就保留负向结果，不能继续生成多个 Skill 后挑最好的一次。

### 12.4 L3：两代最小递归

只有前面链路通过工程验收后，才运行两代。每代必须能追踪：

> 发现什么 → 学什么 → 注入哪里 → 哪个独立验证支持 → 下一代用了哪个版本。

是否扩大到更多代、更多模型和最终 Held-out，由真实诊断结果和预先预算决定，不在本次计划里承诺跑出正向曲线。

### 12.5 消融顺序

不是第一轮就跑六组大矩阵。先建立无记忆基线和固定 Working Memory 条件，然后分批比较：

1. 原始 Service 与固定人工检查表。
2. Skill-only 与相同运行时的无 Skill。
3. Episodic-only 与 Skill-only。
4. 固定/关闭 Working Memory 的配对。
5. 完整系统与固定 Designer。
6. 状态检索与全程固定注入。

每次只改变登记的机制。公平比较使用相同模型、相同初态/顾客、同一工具及上限预算，同时如实报告经验注入本身增加的 Token。

### 12.6 调用、超时与成本

默认并发上限先设为 2；运行前写入每个角色、每个阶段与整个 Run 的预算。增加并发或规模需要独立的运行配置。

不再默认给每个请求套 4096 输出上限。输出配置显式记录，优先沿用用户要求的不额外截断；总预算、调用次数和超时仍受控。

超时请求的真实用量可能未知，必须记 unknown，不能记成零。恢复以 operation_id、原始日志和副作用状态为依据；任何再次发送都形成单独尝试，不静默覆盖。

Customer、Service、Designer、Reflection、Gate、反事实分别统计调用和输入/输出 Token。预算不止主 Service Episode；Reference 搜索、反事实分叉和额外验证也有独立计算成本。

## 13. 指标、报告与证据目录

### 13.1 分开报告的指标

| 维度 | 必报指标 |
|---|---|
| 任务有效性 | 世界有效、业务获证、交互获证、UNKNOWN/UNSAT、真实执行完成率 |
| 业务结果 | 完整任务成功、逐目标完成、硬约束、部分数量正确性 |
| 安全合规 | 成功违规、被拦截尝试、未经同意承诺、越域访问、污染状态 |
| 决策机制 | 选择、参数、遗漏、错误拒绝、前置条件、已验证重复、机会未到达 |
| 经验效果 | 目标机制配对差异、合法回归、负迁移、候选接受与原因 |
| 运行可靠性 | 格式失败、Customer Fidelity、传输失败、超时、未知用量 |
| 资源成本 | 分角色 Token/调用、业务工具、搜索节点、反事实分叉、墙钟时间 |

样本少时报告每个配对结果和不确定性。不能把错误码种类叫作根因数，也不能把不同任务的 Task 2/Task 3 分数差叫作学习收益。

### 13.2 运行产物

    outputs/usami-v2/<run-id>/
      manifest.json
      source-pins.json
      partitions.json
      policies/
      worlds/<world-hash>.json
      scenarios/
      tasks/
      certificates/
      generations/g000/
        selected-before.json
        episodes/<episode-id>/
          customer-scenario.json
          model-requests.jsonl
          model-responses.jsonl
          conversation.jsonl
          business-events.jsonl
          observation-index.json
          oracle.json
          replay.json
          decisions.jsonl
          counterfactuals/
          cost.json
        designer-reflection/
        service-learning/
        validation/
        selected-after.json
      snapshots/
      evaluation/
      report.zh.md
      integrity-manifest.json

原始数据默认写 outputs，不自动加入 Git。Git 保存代码、配置、摘要、哈希和归档索引；大证据包单独归档并验证恢复后可 Replay。

不需要每条 Episode 重复复制整份源码或同一个世界。用内容哈希引用，归档时附完整恢复清单。

## 14. 分 PR 的实际执行安排

| 顺序 | PR / 工作包 | 主要文件 | 前置条件 | 必须交付的验收证据 |
|---|---|---|---|---|
| P0 | 契约、版本与兼容基线 | 本计划、2.0 Schema、Manifest、兼容测试清单 | 无 | 旧接口清单、新协议明确、无默认替换 |
| P1 | 电商核心与独立规则 | commerce/models、operations、transitions、reference、invariants | P0 | 多 SKU/多仓/金额数量边界、正常与错误夹具 |
| P2 | 冻结 Builder 与新目标认证 | scenarios/schema、builder、certification、events | P1 | 两合法方案、无解/未知区分、证书 Replay |
| P3 | 自然委托与顾客运行时 | runtime/session、delegation、consent、customer | P1–P2 | 不用精确 grant 出题、真实报价绑定、交互获证 |
| P4 | 独立任务入口与无学习基线 | runtime/runner、cli、evaluation/outcomes | P3 | 零费用完整链路；显式启用才允许在线请求 |
| P5 | 两阶段真实 Designer | scenarios/designer、signatures | P2–P4 | 非模板约束组合、世界冻结、失败可修正可审计 |
| P6 | 局部诊断与分叉证明 | analysis/*、观察日志 | P4 | 选择/遗漏/错误拒绝证据、局部替代与因果边界 |
| P7 | Working State 与案例经验 | runtime/working_state、learning/episodes、retrieval | P4、P6 | 无 Oracle 泄漏、多目标追踪、检索注入可核验 |
| P8 | Learner 与组合验收 | learning/learner、snapshots、evolution/validation | P6–P7 | 单候选、静态/动态分开、正常回归、原子选代 |
| P9 | 递归 Controller 与独立评估 | evolution/controller、evaluation/pairing | P5、P8 | 跨代继承、训练证据消费、无默认四组交叉 |
| P10 | 小规模真实研究验证 | 预注册配置、报告与归档索引 | P9 + 模型运行预算 | 两代轨迹、独立配对、失败/负迁移和成本全保留 |

P1 的工作量和正确性风险最高；P6 的因果结论风险最高；P3 最容易把协议复杂度重新加回来。它们分别设置独立验收，不合成一个巨大 PR。

P5 与 P6 在 P4 后可以分别实现，但最终通过同一套版本化 Episode 数据连接；不会要求同时重写全部旧 Controller。

### 14.1 我会先实际完成的前三个 PR

P0 是本计划与契约准备；下面三个代码 PR 对应 P1–P4 的首条完整切片。

**第一 PR：契约 + 电商核心。** 先把 SKU、仓库、行级账务、数量和报价对象做实，完成确定性业务与独立规则。先不接模型。

**第二 PR：可组合世界 + 联合目标。** 让约束 Builder 构建前述多选项世界，再由独立认证给出任何合法方案都能通过的任务。

**第三 PR：自然顾客 + 单任务 Runner。** 取消新协议中无必要的逐操作 grant；通过真实报价确认执行交易；把第一条完整链路跑通并形成可恢复证据。

这三个 PR 完成后，已经有一个可以单独使用的业务 Benchmark 纵向切片。后续进化工作建立在它之上。

## 15. 测试与验收怎么做

### 15.1 核心测试矩阵

| 测试组 | 必测情况 |
|---|---|
| 世界与规则 | 同 Seed 重现、约束冲突、边界金额、部分数量、库存竞争、幂等、对象归属 |
| 商品决策 | 错规格、超预算、超时限、两个合法替代、确实无解、预算不足不能证伪 |
| 顾客交互 | 缺少事实、未展示报价、歧义接受、拒绝、偏好变更、确认后 finish、结束后不新增承诺 |
| 报价时效 | 过期、库存变化、金额变化、版本变化、重复确认与重复成交 |
| 结果评估 | 终局成功但过程违规、被拦截尝试、真实违规、部分完成、错误拒绝与正确拒绝 |
| 局部分析 | 可见信息重建、同前状态替代、污染链路、多个错误同一依赖、因果未证明标注 |
| 经验与选代 | 非法 Patch、NOOP、范围越界、候选负迁移、无目标机会、未获证不接受 |
| 递归 | 新版本实际注入、父版本保留、下一代继承、证据无遗漏、评估不能更新 |
| 数据完整性 | 对世界、报价、同意、工具参数、Oracle、Snapshot 和事件游标逐项篡改可检测 |
| 历史兼容 | 旧 v3 任务序列化、历史哈希、原运行入口和源码快照 Replay |

### 15.2 属性测试重点

使用新增的开发依赖运行属性与状态机测试，覆盖：

- 库存预留、释放、发货的数量守恒；
- 多次部分退款累加不超过行级可退余额；
- 拒绝或失效报价不产生有效成交同意；
- 未成交交易不会无故改变资金与履约；
- 外部事件幂等且不得重复应用；
- 随机操作序列执行后，独立 Reference 与真实状态的差异能被识别。

属性测试生成的是边界状态与操作序列，不替代合法业务场景的端到端样例。

### 15.3 回归范围

每个 PR 先跑本模块和直接调用方测试。触及共享 Engine、Schema、Snapshot 或注册表时，再跑相应共享回归。

合并完整纵向切片、切换新入口或发版本时执行可运行的全量回归。不会为只改文档重复跑全部业务测试，也不会为获得绿色结果删除旧断言。

旧源码绑定的实验用它自己的源快照验证；不能要求旧归档在新源码上仍产生相同源码哈希。

## 16. 拟提供的操作入口

命令是接口设计目标，目前尚未实现：

    # 纯离线构建与认证
    python -m usami_v2.cli build --scenario scenario.json --seed 1 --output <new-dir>
    python -m usami_v2.cli certify --task task.json --world world.json

    # 零费用工程链路
    python -m usami_v2.cli smoke --offline --output <new-dir>

    # 显式开启真实业务诊断；不学习
    python -m usami_v2.cli run --manifest run.json --execute-live --learn disabled

    # 训练结束后独立配对
    python -m usami_v2.cli evaluate --manifest evaluation.json --parent <hash> --candidate <hash>

    # 明确的递归训练
    python -m usami_v2.cli evolve --manifest evolution.json --execute-live

    # 无模型 Replay
    python -m usami_v2.cli replay --run <dir> --verify-all

默认命令不会查询凭据或调用模型。在线命令使用现有 OpenAI-compatible 客户端与本机凭据，Model / Base URL 不写死；发送和返回原文脱离 Key 归档。

## 17. 兼容策略、风险与不在首版做的事

### 17.1 旧路径怎么处理

- 不删除 usami_aftersales、旧 DialogueSession 和旧 Designer。
- 不把旧 After-sales 世界强制转换后继续沿用原哈希。
- 新旧世界之间若需要转换，保存显式 MigrationRecord 和新的世界哈希。
- 旧实验报告继续按原协议解释；2.0 的结论只来自 2.0 的真实记录。
- 主工作区存在尚未提交内容时，在干净 checkout 实施；不覆盖用户改动。

### 17.2 主要风险与处理

| 风险 | 具体处理 |
|---|---|
| 世界复杂了，但 Agent 仍只做固定流程 | 验收要求真实候选权衡、两个合法方案和多目标；不以字段数/世界数验收 |
| Builder 变成暗中提供答案的脚本 | Builder 只满足场景约束；任务认证与 Service 观察分开，参考路径不进 Prompt |
| 自然授权变成自动放权 | 可信 Request 必须有独立委托或报价同意来源；逐项测试范围与失效 |
| 全部失败又被归为业务能力 | Customer Fidelity、交互获证、格式/网络错误分栏，并在学习资格检查排除 |
| 反事实分析夸大因果结论 | 区分单步替代、固定续跑和真实独立修复，保留不确定性 |
| Memory 和记忆实例答案混淆 | 去固定标识、来源族分区、案例引用边界、最终测试不可入库 |
| 多组件一起变，无法归因 | 组合 Snapshot + 分批消融；首版 Working Memory 实现固定 |
| 新 Gate 只奖励拒绝 | 合法任务完成与负迁移是接受前提，目标机会未到达单独报告 |
| 规模拖慢开发 | 先单领域完整切片；不预建几百题，不并行重写八领域 |
| 档案再次撑大仓库 | 默认 outputs、哈希引用、源码去重、归档恢复验证 |

### 17.3 首版不做

不新增其他业务领域，不重写网页，不训练模型权重，不让 Agent 生成并执行任意代码，不把所有历史系统迁移到一个新 Controller，不引入分布式数据库、在线向量服务或额外摘要 Agent。

τ²-bench 外部实验放在内部链路与经验接口稳定以后。届时单独核对其实际任务、工具和评估协议，用 Adapter 接入同一学习流程；不把“在 Usami 写了一条经验”直接当成已经外部泛化。

## 18. 完成后应该怎样判断这次重构成功

工程验收看六件事：

1. Service 面对多个可执行方案，自主选择，且有多个合法解。
2. Customer 可以自然表达、比较并确认；机械协议不再支配正常业务。
3. Designer 可以提出新场景关系，再在冻结世界中组合任务。
4. 局部错误与终局结果分开，错误机制有对应真实状态与证据。
5. 一次经验更新能被追踪到独立验证、真实注入和下一代继承。
6. 任意关键结论都能回到原始请求、真实执行、独立 Oracle 与 Replay。

研究验收另看：相同条件下，候选是否在未见实例修复了目标决策，正常业务是否保留，负迁移和成本是否可接受，多代是否积累了可迁移收益。

我的具体实施选择是：**先做出一个任何 Agent 都能接入、需要真实业务判断的电商 Benchmark；随后把局部诊断、经验学习和递归进化逐层接上。每一层都用独立证据验收，保证最终看到的提升能够解释、恢复和比较。**

---

## 附录：原方案到实施工作包的对应

| 原方案主题 | 本计划实施位置 |
|---|---|
| Business World 2.0 | 第 4、7 节；P1 |
| 自然交互与授权 | 第 5 节；P3 |
| 两阶段 Designer | 第 6 节；P2、P5 |
| Outcome / Decision Analyzer | 第 8 节；P4、P6 |
| Skill / Episodic / Working Memory | 第 9 节；P7、P8 |
| 独立验证与递归进化 | 第 10–12 节；P8–P10 |
| 证据与复现 | 第 3、13、15、17 节；所有 PR |
| 外部实验与研究结论 | 第 12、17、18 节；内部链路稳定后的独立阶段 |
