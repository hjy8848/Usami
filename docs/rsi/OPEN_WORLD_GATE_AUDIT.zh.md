# Usami 开放式 RSI 真实运行链路 Gate 审计

**审计基线：** b0bdf8b7c734f34e06f70b111f9a88cde279ef98（2026-10-24）
**审计入口：** integrations/rsi_usami/open_world.py::run_open_period()，并追踪 World Population、Native Designer、Grounder、Compiler、Reference、Host、Usami Runtime、Oracle/Replay、P/K 选择、M 自修改和 Period 编排。
**交付边界：** 本轮提交 Gate 清单和最小修改方案。未改运行时代码、业务规则、Oracle、Replay 或评价阈值；未调用在线模型、未运行正式实验。

## 结论

目前有两条不能混为一谈的链路：

1. run_open_period() 是正式 RSI/GRPO 数据采集入口。它生成训练 World，然后调用现有 run_period() 和 collect_service_improvement_group()；每个 Service round 先收集 roots，再做独立 selection/reward，最后收集 M self-edit roots。任一正式采样组为 UNUSABLE 就终止 Period。
2. propose_open_challenge() 是单次真实模型提案诊断入口。它能复用冻结 World、真实 Designer Provider、Grounder、Compiler 和 Reference，但不运行 Service、P/K 修改、独立评价或 M 修改。因此它不能充当真实端到端诊断。

所以当前代码有开放 World/Challenge 接入，也有真实模型单阶段诊断，但没有一个不采集 GRPO、又能继续观察失败阶段的真实端到端 DIAGNOSTIC 编排模式。正式入口把“训练数据组不可用”直接当作“研究 Period 不能继续”；挑战编译/证明的不同失败也会被压成 REFERENCE_UNPROVEN。这解释了为什么一次失败或无提升会让后续阶段看起来像没有发生。

自然语言门槛不是一处正则，而是至少四处重复承担同一职责：TaskDraft 请求引用与意图词检查、compile_task() 的公开边界、TaskSpec 的 public-line 匹配、Customer delegation span 校验，以及末端 communication claim 抽取。目标合法性与授权规则需要保留；“必须使用某个内部词、原文子串或唯一文本匹配”不是业务规则本身，应从结构化目标绑定中拆开。

## 分类和证据口径

| 类别 | 含义 | DIAGNOSTIC 中的处理 |
|---|---|---|
| A | 低价值工程约束，或以词面/子串/唯一识别替代结构化语义。 | 简化/替换为来源绑定、结构化字段或明确澄清；保留其背后的 C 类业务不变量。 |
| B | 判断合理，但一次失败不应终止全部诊断。 | 记录原失败，允许有界、计费、可审计的新尝试/检查点恢复；不得把失败转成成功。 |
| C | 业务、权限、证据、数据隔离、安全或研究评价正确性。 | 不放宽、不自动纠错、不根据模型自述通过。失败时阻断依赖该证据的下游阶段，归档为 DIAGNOSTIC_BLOCKED。 |

主表按“语义 Gate 家族”归并同一规则在多个模块里的重复实现。行号对应审计基线；同一区间可能含多条同类判断。完整源码分支、异常/状态节点和数据模型字段索引见审计附录。可恢复指保留失败后另开独立尝试，不代表把失败改写为成功。

## A. 正式运行 Gate 清单

### 0. CLI、工厂与入口状态

| ID | Gate：文件:行 / 条件 | 阻断结果 | 恢复与类别 | 存在原因；业务正确性是否需要 |
|---|---|---|---|---|
| E0 | experiments/rsi/examples/open_world_usami.py:17-30；命令必须是 period 或 validate-designer，--factory module:function 必填，World/Period 数量为正，工厂可导入并返回上下文。 | 参数错误在模型调用前退出；工厂导入/配置异常不形成 RSI Period。 | B：修正本地配置后重开；诊断 CLI 可逐字段检查，不自动替换 Provider 或测试集。 | 需要可信运行依赖；不是业务门槛。当前没有默认端到端 Factory，实际能否运行取决于外部 Factory。 |
| E1 | 同文件 :31-44,63-65；正式命令只接受 Period 为 READY_FOR_TRAINING/COMPLETED 才继续下一 Period；其他最终状态令 CLI exit 1。 | 状态是非零退出；之前生成的 Summary 文件仍存在。 | B：诊断应以“阶段是否已如实记录”为命令健康标准；退出时保留 NO_GAIN/NOOP/BLOCKED 状态。 | CLI 把正式采集状态当作命令健康状态；与业务正确性无关。 |

### 1. World：来源、生成、冻结与复现

| ID | Gate：文件:行 / 条件 | 阻断结果 | 恢复与类别 | 存在原因；业务正确性是否需要 |
|---|---|---|---|---|
| W1 | integrations/rsi_usami/open_world.py:49-69,71-91；resume 的分布、seed、BuildBudget、尝试数、Period 链和 schedule 必须与归档完全一致。 | ValueError，World Population 不能继续。 | C：不可在原状态引用下改变分布或历史；另开新运行/分布版本。 | 防止悄然换分布、删失败 slot 或重写历史；训练/评价溯源必需。 |
| W2 | usami_v2/scenarios/distribution.py:35-111；分布声明、split、权重、slot schedule 和分层统计必须合法；open_world.py:325-326 只接受 train。 | 配置无效直接失败；非 train 分布不能开启正式 RSI。 | C：保持 train/validation/heldout 隔离。修正需新注册的分布/运行。 | 训练-测试隔离与可复现采样必需。 |
| W3 | open_world.py:107-115；count * max_attempts 不得超过注册的生成尝试预算。 | ValueError，不开始/不完成当前 World period。 | B：保留已消费次数；用新预算版本、较小 slot 数或新 Period 继续。 | 资源上限是工程策略；额度不是业务真值。 |
| W4 | usami_v2/scenarios/designer.py:812-872；slot 必须属于声明分布；尝试数限 1–3；World Designer 输出需通过结构 Schema/ScenarioSpec。Provider 失败会将 slot 标成 ERROR 并停止该 slot 重试。 | UNSAT/UNKNOWN/ERROR slot；Provider 错误不继续该 slot。 | 格式错误/可修复约束 B：有界新模型调用并保存原请求/响应；鉴权、端点错误 B：修配置后继续新 slot；不把 ERROR/UNKNOWN 改写为 SAT。 | SAT 与合法世界必需；次数是工程预算，可调。 |
| W5 | usami_v2/scenarios/schema.py、distribution.py、builder.py:124-162、solver.py；字段类型/引用/域约束、约束矛盾、原生不变量；受限搜索结束时区分 SAT、穷举 UNSAT、未穷尽 UNKNOWN。 | schema/约束错误；SAT / UNSAT / UNKNOWN 各有明确状态。 | 身份/不变量 C；节点预算导致 UNKNOWN 为 B，可提高真实 BuildBudget 或换合法提案。不能把 UNKNOWN 当 UNSAT/SAT。 | 禁止非法世界和错误宣称可解；有界搜索是工程预算。 |
| W6 | open_world.py:116-119；本 Period 或历史中出现相同 frozen world_hash 即抛错；world_structure():24-40 用关系结构签名区别仅改 ID/名称/seed 的伪多样性。 | 重复世界使 next_period() 整体抛 ValueError；其他 slot 可能已付费但未登记。 | B：保存重复 slot 结果，按新 schedule 补 slot；不能改哈希或静默换 seed。仍按真实结构签名报告多样性。 | 跨周期探索要求新世界；去重不是商业规则。 |
| W7 | open_world.py:94-105 + builder.py:165-171 verify_build()；仅 SAT World 会供 Grounder 使用，World 构建必须可原生重建且不变量复核通过。 | 非 SAT World 被跳过；build 验证不一致则中止。 | 非 SAT 为 B，可继续其他有效 slot；build 不一致为 C，依赖该 World 的路径阻断。 | 合法世界与归档完整性必需。 |

### 2. Challenge → Grounder → Compiler → Reference

| ID | Gate：文件:行 / 条件 | 阻断结果 | 恢复与类别 | 存在原因；业务正确性是否需要 |
|---|---|---|---|---|
| C1 | open_world.py:181-192；同批所有 World 的 task_design_capabilities 必须完全一致，否则 public_view() 抛错；空 World batch 的 capability 为 None。 | 一份 World capability 不同便无法发布挑战视图。 | B：按 capability profile 分批，或给每个 World 单独列能力并由 Grounder 选择；空 batch 记录为空并采新 World。 | 批次组织限制，不是业务真值；不能暗示未配置能力。 |
| C2 | designer.py:116-165,325-350,420-480；TaskDraft 字段、拒绝额外字段、Provider 按模型/请求设置 tool_choice，模型输出必须是恰好一个规定 function call、完整 JSON、Pydantic Schema 通过；{} 是 EMPTY_TOOL_ARGUMENTS。 | INVALID 或模型调用失败；单次坏输出不认证。 | Function-call 完整性和字段类型 C；模型不支持当前 tool_choice 的端点兼容失败与单次格式错误为 B，允许有界、显式记录的 endpoint-specific 请求和格式纠错调用；可派生机器 ID/标签为 A，由 Host 派生而非要求模型猜。 | 结构有效是执行前提；重试策略是工程选择；不能自动改写目标或补答案。 |
| C3 | grounding.py:47-81；抽象变量、selector、target alias、关系、域/实体 ID Schema；扫描整份 JSON 中类似 8 位内部 ID 的文本是信息隔离代理。 | Schema 错误或 INVALID；合法公开句子中的 ID 也可能误拒。 | 关系/身份 C；ID 词法代理 A，只验证结构化 Grounder binding 和禁用字段，避免无关字符串误判。 | 挑战不能夹带 World 真值；“任意字符串含 8 位 hex”不是信息隔离的必要/充分条件。 |
| C4 | grounding.py:21-69；line selector 数量/年龄/数量/退货属性范围、变量唯一性、目标与 selector 对应、关系类型；候选数量有限。 | Schema 无效、Grounding 预算耗尽或无匹配。 | 业务关系和 Customer 范围 C；数量上限 B，诊断可提高登记预算并报告截断；不能把未搜索到叫作不合法。 | 限定执行搜索；限额是工程成本约束。 |
| C5 | grounding.py:95-163；只匹配 SAT 冻结 World 中真实 SKU family/issue/属性、顾客所有权、订单/行和关系；受限 world/binding 扫描；确定排序。 | NO_MATCH 或 BUDGET_EXHAUSTED；二者都不是 Reference UNSAT。 | 对象/所有权/关系 C；预算耗尽 B；catalogue 缺少同顾客多行共现等匿名关系摘要为 A 的表示缺口；max_matches 截断后排序导致的偏序为 B。 | 防止绑定不存在或越权对象；必须区分搜索预算和无匹配。 |
| C6 | open_world.py:194-224 + grounding.py:166-171 compile_grounded()；Challenge Schema → 候选 → 原生 compile_task() → certify_task()；仅 CERTIFIED 才注册 NativeTask。 | Schema INVALID；无候选时返回 Grounder 状态；有候选但编译/证明失败统一成 UNVERIFIED/REFERENCE_UNPROVEN。 | 可修复 Schema B；真实业务/权限 C；把所有候选失败压成 REFERENCE_UNPROVEN 是 A（可观测性），应分别汇总 COMPILE_REJECTED、UNSAT、UNKNOWN、能力缺失、预算耗尽。 | 任务须绑定真实世界且由 Reference 证明；不同失败不能混为模型错误。 |
| C7 | designer.py:116-165,522-618；scenarios/tasks.py:94-265,366-432；remedy/information goal 由 public_request_span/subject_mention 支持；要求 span 含 remedy/fact/date/charge/quantity 词并唯一命中冻结商品行；TaskSpecV2 再绑定 Customer、line alias 和 source span。 | Pydantic/compile_task() 拒绝；自然表述不能匹配时不是 Reference 搜索失败。 | A（匹配机制）/C（语义）：原文子串、关键词、要求自然语言唯一编码内部 issue/family 改为结构化 RequestBundle 与 Host 来源绑定；最终 goal 必须来自已登记顾客 intent、同一顾客和合法对象，C 保留。 | 目前把“目标是否合法”“公开需求是否授权”“文本是否被正则解释”混在一起，且在 Designer、Task、Customer profile、communication 评分重复。 |
| C8 | designer.py:484-519,522-618；task_design_capabilities 列表；compile_task() 要求任务 Schema 与验证器配置一致；scope、line alias、Customer、数量、target stage、退货/退款/审批/证据事件和 remedies 必须真实合法。 | COMPILE_REJECTED；缺失外部事件阻止/无法证明目标；delivery-confirmation 未实现时 delivered 不能认证。 | 权限/所有权/可用动作/真实前置条件 C；配置不支持的事件/目标 B，明确 CAPABILITY_UNSUPPORTED 并尝试其他合法题/World；不得伪造事件、库存或实际送达。 | 业务和证书范围必须一致；未实现能力不是模型违规，也不能伪造证书。 |
| C9 | task_certification.py:24-127,170-249,253-347；Task scope、对象、预注册事件、pristine pre-state、ProofBudget 和候选操作；缺外部/审批/配送事件产生 blocker；unsupported information target 为 UNKNOWN。 | CERTIFIED、UNSAT、UNKNOWN、blocked 分开；搜索预算用尽是 UNKNOWN。 | Reference 和证据可重算 C；ProofBudget/支持能力不足 B，换支持的任务或合法增加证明预算；不能把 UNKNOWN 当成功。 | 证书证明具体任务在原生执行规则下存在路径，不证明 LLM Service 能理解。 |
| C10 | task_certification.py:443-640；certify_task() 需达到要求的独立 witness；路径经真实 Engine/Oracle/Replay 验证。 | 无路径且穷尽才 UNSAT；预算/未穷尽为 UNKNOWN；witness 不足不 certified。 | C，不放宽；按注册 ProofBudget 重新证明或换 Task。 | Designer 不能自行宣布题目可完成。 |
| C11 | open_world.py:217-245,254-313 + task_certification.py:648-662 + integrations/rsi_usami/packages.py:12-74；认证后复验、锁 World/task/profile/events/runtime binding，Task ref 同时登记 Adapter 和 verifier。 | hash/binding/registry 不一致中止。 | C：完整性错误不能恢复为可执行任务；归档故障后重开新绑定。 | 防止证书与真实执行环境不是同一个任务。 |
| C12 | open_world.py:246-248；无 Grounder 候选返回 Grounder status；候选编译/Reference 均失败则统一 REFERENCE_UNPROVEN。 | Host 只收到通用 reason_code，具体原因仅在尝试记录中。 | A（可观测性）：向 M 传已记录的安全失败类型及公开 Compiler contract 错误；Reference 私有 blocker、对象 ID、witness、Oracle 私有结论不传。 | 修复可观察性，不改变证书标准。 |
| C13 | open_world.py:166-167,203-205,254-269；只能 train population；parent evidence hash 必须在 allowed_training_hashes 白名单。 | INVALID/UNAUTHORIZED_TRAINING_EVIDENCE。 | C，不放宽；修正来源注册后以新提案重跑。 | held-out、私有或未授权证据不得进入训练/提示。 |
| C14 | open_world.py:316-345；新 World hash 不能与独立 Task source 重叠；Period 结束验证每个 Challenge receipt；外层 Period record 只在 run_period() 正常返回后写入。 | overlap/split 抛错；Replay 错误阻断；异常退出可能只留下内层阶段记录。 | 隔离/Replay C；异常时写外层诊断终态和 checkpoint 为 B。 | 隔离和追溯必需，失败也应有清楚终态。 |

### 3. Host、Customer/Service 与原生业务执行

| ID | Gate：文件:行 / 条件 | 阻断结果 | 恢复与类别 | 存在原因；业务正确性是否需要 |
|---|---|---|---|---|
| R1 | rsi_core/runtime.py:32-88；M/target/mode 类型匹配；固定 B/φ、Host capabilities、probe handles 不能被 public view 覆盖；IMPROVE_SERVICE 要 certifier 和 baseline runner。 | ValueError，root 不创建或模式阻断。 | mode/target/私有句柄 C；配置缺失 B，记 DIAGNOSTIC_BLOCKED；不得自动换模型/任务集。 | 固定实验干预和信息边界必需。 |
| R2 | runtime.py:93-128；MODEL action 字段精确，request/schema 为对象且 JSON Schema 有效；model 配置和 call/token budget 可用；输出过其声明 Schema。 | 错误输出 CandidateError/FAILED；未配置或预算耗尽为 Infrastructure/Candidate failure。 | 安全 Schema/角色 C；单次响应格式 B，保存原响应并单独 correction call；不能自动补业务目标。预算耗尽 B，成本不重置。 | Host 限制 M 的可执行协议；一次格式错误不应终止全诊断。 |
| R3 | runtime.py:130-158；只可 Stage 规定 kind/current parent；最多 2 candidates；第一次 PROBE 后 freeze candidates；P/K 静态检查。 | 越权角色/parent 为 forbidden；坏 P/K feedback=INVALID；超过候选数/冻结后再加候选失败。 | 角色/parent C；候选数/freeze B，formal 保留，DIAGNOSTIC 以新 revision/root 继续并完整记录；静态修复限次重提。 | 不让 M 改业务能力；候选限额是正式采样协议。 |
| R3a | rsi_core/programs.py:10-49,52-79,90-109；P/M 必须是非空、受字节预算的同步 Python AST；唯一 entrypoint 且签名恰好为 (view,state)；K 是 finite canonical JSON object；ServiceSnapshot 固定 P/K/B。 | 语法/API 约定错则 CandidateError/ValueError；不合法快照不能发布。 | entrypoint/版本/lineage C；源码大小预算 B；可依 Host error 新提案修复。重要：ProgramArtifact.check() 明确是 contract check、不是 sandbox；真正隔离在 rsi_core/isolation.py:14+ 的 DockerWorker，任何诊断和训练都必须保留。 | 程序接口和执行隔离必需；绝不能把 AST 检查当安全沙箱。 |
| R4 | runtime.py:159-187；PROPOSE_CHALLENGE 仅 IMPROVE_SERVICE；receipt 只可为登记状态；CERTIFIED 必须绑定 task/certificate/frozen；task ref 每 root 只注册一次。 | 结构/重用引用失败；INVALID/UNVERIFIED 会作为 observation 回给 M。 | receipt 和 binding C；挑战未通过 B，给安全反馈并尝试新 challenge，而不是终止诊断。 | 真实 challenge 是任务入口；证书不可伪造/跨 root 复用。 |
| R5 | runtime.py:188-209；RUN_BASELINE 必须在候选前，只能跑本 root certified task 一次；结果要匹配真实 parent/task、Replay true 和登记 status。 | 顺序/重复执行 CandidateError；伪 runner 结果 InfrastructureError。 | C（因果基线/任务绑定）；不合法 Task 重新出题。 | 保证候选与父版本基线来自同一题。 |
| R6 | runtime.py:210-225；PROBE 只接受当前 parent/注册候选及公开 probe；open challenge 需先 parent baseline。 | 私有/未认证 probe 为 CapabilityViolation；缺基线为 CandidateError。 | C，不放宽；动作格式/顺序错误 B 可有界修复。 | 防止测试泄漏与无基线因果比较。 |
| R7 | runtime.py:226-268；SUBMIT 只能注册版本；相同 P/K 被记 NOOP；max steps/output token/call budget 到期则失败。 | NOOP、FAILED 或 infrastructure failure；Host 记录事件与成本。 | NOOP 是有效结果 B：保留父版本继续诊断；预算 B：只能新预算版本继续；能力/证据完整性 C。 | 不允许 Agent 直接报告新版本；NOOP 不应等同运行失败。 |
| R8 | rsi_core/worker.py、runtime.py MODEL、usami/service/client.py:37-52,126-150；HTTP timeout/response、Host/P adapter/client 各自 token ceiling；当前失败不自动重试。 | PROVIDER_TIMEOUT/HTTP_ERROR 成为失败；超时的真实 token 消耗可能未知。 | B：区分 auth/schema 400 与 timeout/429；无副作用生成可有界新调用并单独存原失败；写工具绝不盲重试，先 Replay 核对状态。统一预算来自 manifest，未知成本标 UNKNOWN_COST。 | 连接/长度是工程约束；真实模型、费用身份须记录。 |
| R9 | integrations/rsi_usami/adapter.py:37-122；P 每个 service action 最多 8 内部步；模型身份固定 B、tools 完全匹配、parallel calls=false；Action 是注册 operation/reply。 | P/action 错误 CandidateError；API 错误 InfraError；缺 usage 被视为未知/失败成本。 | 工具/模型固定 C；步数/调用预算 B；usage 不足可继续 DIAGNOSTIC 但不进训练样本。 | 工具权限必需；八步是 Host 限额。 |
| R10 | adapter.py:99-100 调 ServiceAction.from_tool_message；agents.py:115-133 要恰好一个完整 function call 且 finish_reason=tool_calls；native OpenAIServiceAgent agents.py:342-357 接受普通 assistant text reply。 | RSI ProgramServiceAgent 拒绝 native Service 可接受的纯文字澄清回复。 | A/B：复用 native 的“工具操作或非空纯文本 reply”解析；纯文本无副作用，业务操作仍须恰好一个完整 call。多 call/截断/坏 JSON 保持拒绝，可有界格式修复。 | RSI 与原生 Service 协议不一致，造成无关协议错误。 |
| R11 | usami_v2/runtime/runner.py:424-468；Task/Profile checked、mode、task scope、Customer identity/delegation exact set、协议版本、external event 唯一性和初始业务 invariant。 | Episode 前异常。 | C：重认证合法 task/profile/event；不跳过。 | 冻结 World、顾客身份与授权的基础。 |
| R12 | runner.py:480-535,545-618,649-712；service decisions/tool/model/customer turns budget；model request/response 必须可记录；仅观察过的对象/quote 可引用；reply 非空；Customer transition 合法。 | 预算结束保存未完成 episode；模型/Schema/Engine 错误成为 agent/protocol/runner error；非法业务 operation 由 Engine 原样拒绝并可继续。 | 工程预算/Provider B；越权、未观察对象/quote、错误记录 C。可开独立新 Episode，但真实写操作状态不明时先查 Replay。 | 权限可见性与完整轨迹必需；预算是工程配置。 |
| R13 | usami_v2/runtime/customer.py:100-223,226-390；CustomerDecision action、profile delegation 必须绑定 public request；quote 需来自当前真实 Customer/金额/数量/费用/期限/退货条款；consent 精确绑定展示报价。 | profile/报价/授权不匹配则不授权或要求澄清。 | 委托、报价、授权 C；窄关键词推断自然语言肯定/否定的 _explicit_consent_intent() 为 A 的表达代理：诊断记录原话，歧义要求澄清；不可由 LLM 自己给交易授权。 | 交易授权是安全边界，词面判定不是授权本身。 |
| R14 | usami_harness/engine.py:42-135；usami_v2/commerce/adapter.py:1-11；commerce/reference.py:121-328；transitions.py:11-202；invariants.py:8-130；external.py:4-70；Actor/scope/resource/operation/params、权限、状态转移、业务不变量；actual state 必须与 Reference projection 一致。 | 实际错误码/拒绝/转移失败/runner error，不能由 Service 自述覆盖。 | C，绝不放宽。被拒绝操作可继续但不记为已执行。相邻校验可共用纯函数，但 Engine 与独立 Reference/Transition/Oracle 的真值判定不能整体删。 | Benchmark 业务真值。 |
| R15 | runner.py:623-644,703-712；customer.py:177-223,299-390；quote 实际重渲染并 hash-match；authority proof 绑定 actor/target/operation/value；有待执行 consent 时 finish 被阻止，让 Service 收到授权。 | 条款不一致不得成交；finish 延后。 | C：准确报价和有效授权必须保留。可信结构化 consent 可渲染成自然语言；不能反向从随意语言猜交易许可。 | 防止金额、SKU、时间或条款被换后成交。 |
| R16 | rsi_core/programs.py:154-240；save/load 必须哈希一致；publish_service 要求父版本、固定 B 和 P/K lineage；publish_designer 只能从父 M 继承且模型 ID/sampling 固定；evaluation-only Service copy 不能进 main chain。period.py:62-69,170-186 使用所选 Service/M 建子快照。 | 不匹配版本 lineage、被篡改 artifact 或 evaluation-only publication 拒绝。 | C，不放宽；出错后从最后一个有效 parent 另开候选。 | 防止被测临时副本污染训练主版本，且保证跨代可追溯。 |

### 4. Oracle、Replay、P/K 与 M 修改和 Period 完成

| ID | Gate：文件:行 / 条件 | 阻断结果 | 恢复与类别 | 存在原因；业务正确性是否需要 |
|---|---|---|---|---|
| O1 | usami_harness/oracle.py:5-94 + usami_v2/evaluation/outcomes.py:45-236；Oracle 从真实轨迹判定；Outcome 分开 goal/process/safety/reliability；Adapter adapter.py:151-217 只有 VERIFIED 且 strict_task_success 才计正式 score 1。 | CANDIDATE_FAILED/UNKNOWN/VERIFIED；goal 达成不抹掉过程错。 | C：不改 strict score、不把被拦截非法操作算成功。DIAGNOSTIC 展示分量，不能因 0 分阻止阶段继续。 | 正式评价定义不可为调试改动。 |
| O1a | usami_v2/evaluation/communication.py:96-156,174-250；从 Service 消息以文本提取数字/日期/对象/承诺，再和 Facts/obligations 匹配；未识别表达可成为 UNKNOWN/UNRESOLVED，并影响 strict score，但不应中断 Engine。 | communication UNKNOWN/FAIL 会影响最终 score/strict success，而非认证或运行安全。 | A（表达抽取机制）/C（声明必须真实）：本轮不改评分；诊断保留文本、抽取证据和 unresolved。后续需针对真实表达做独立评估后再改版本化标准。 | 关键词/正则抽取可能错判自然语言，但不能默认为事实为真或把无法解析当成功。 |
| O2 | usami_v2/runtime/runner.py:394-421,747-780；integrations/rsi_usami/adapter.py:176-217；rsi_core/evaluation.py:85-90,189-204；状态重建、工具/模型调用、authority、Oracle、Outcome、Replay 全过才可作正式证据。 | Replay false 会令 dependent result 无效/Infra failure。 | C；保留坏原件并标 BLOCKED，不得继续用它训练/评选。 | 可审计性与真值。 |
| O3 | integrations/rsi_usami/adapter.py:151-158 + rsi_core/evaluation.py:11-30；M 只获版本化、绑定 run_ref/status/score 的公开反馈，不直接取得 Oracle 私有结果。 | feedback protocol 不一致时报 InfrastructureError。 | C：现有聚合反馈符合明示契约，不应凭名称认定 Oracle 泄漏。 | 隐私裁判与训练反馈分界。 |
| O4 | rsi_core/collection.py:163-191 与 self-edit collector；正式 Service/M group 至少 2 个不同整数 seeds；预注册 root/selection/reward 三套任务包与预算、purpose/partition。 | config 错误直接拒绝；collection 在开跑前 reserve 所有阶段预算。 | B（仅诊断）：正式要求不变；DIAGNOSTIC 用独立 single/multi-root manifest、逐步计费，不造 GRPO group、advantages 或 training input。 | 完整 on-policy GRPO 数据合同，不是单次真实流程所需。 |
| O5 | collection.py:95-159,163-205,256-315；冻结模型身份；root/selection/reward 分配；任一 API/Replay/UNKNOWN 超有效性阈值可令 group UNUSABLE、reward_refs 为空；单 root FAILED=-1/NOOP=0 本身不必然废组。 | 正式采集组不能导出；Period 直接中断。 | formal group完整性 C（formal-only）；DIAGNOSTIC 记录已完成的 root，保留失败并用父版本继续可独立运行的 stage；不伪装正式训练样本。 | 部分组不能用于 GRPO；诊断没有 GRPO 要求。 |
| O6 | rsi_core/evaluation.py:78-177,180-250；paired evaluation 固定模型/任务/seed/budget/purpose，Replay 通过；UNKNOWN 保留分母；unsafe candidate 不可被选。 | comparison unusable/unsafe/UNRESOLVED。 | C：不改 isolation、配对、UNKNOWN 或安全条件；Diagnostic 可以报告 unavailable/UNRESOLVED，不能计 pass。 | 公平比较与评价可信度。 |
| O7 | evaluation.py:252-310 + collection selection；重算 summary/pair binding/safe/usable；mean_delta<=margin、regression、unsafe、unresolved → KEEP_PARENT。 | candidate 不发布，parent 保留。这是正常结果，不要求 Period 停止。 | 评价标准 C；NO_GAIN 应让 DIAGNOSTIC 继续到 M，并记录保留父版本。 | 不可降低门槛；分清“候选未发布”和“研究流程没有完成”。 |
| O8 | evaluation.py:119-156,215-249；Adapt/F 的 probe/query 分离、parent copy、purpose/partition；candidate 跑独立 query package；service set 只接受已注册集合。 | bad package、Replay fail、UNKNOWN 或无 candidate result 导致无法宣称评价。 | 隔离与评价 C；没配置 package 为 B，记录 EVALUATION_NOT_CONFIGURED；不能说“无提升”或“有提升”。 | 独立评价不能用训练 Task 冒充。 |
| O8a | rsi_core/packages.py:16-42,60-115,166-198,200-324；TaskProof 需真实 origin/certificate；package proof 必须精确覆盖 probe/query；来源不可跨 partition/purpose/support/probe/query；validation/test bank 除 audit 外不得提供训练 reward/selection；PackageProvider 逐条调用可信 verifier 并验证 sampling draw/task set。 | Bank 配置、来源复用、证书或 draw 不匹配时拒绝；package pool 不足可能抛 PackagePoolExhausted。 | 来源/证书/split/用途 C；pool exhaustion B，增加合法、独立、预注册 packages 或把 evaluation 记为未运行；不得改目的标签。 | 任务来源隔离和每条独立评价都必须由真实证书支持。 |
| O9 | experiments/rsi/seeds/M0.py:4-38；拒绝挑战时回 MODEL，但 attempt 不递增；attempt>=3 只在初始 challenge_model 分支检查，拒绝后仍在 challenge_submit，因此实际上可能一直调用到 Host step/cost budget。 | 多次无上限（由 M0 逻辑看）提案/格式修正，最终 Host 超步数或费尽预算。 | A/B：修状态机计数，提供配置化有界修正；每次真实请求和拒绝入账，不增加总预算。 | 已确认程序状态机 bug；非业务规则。 |
| O10 | rsi_core/period.py:11-39,46-78；输入 snapshots/Host/round 必须一致且完整；任一 service group != USABLE 就写 ABORTED_SERVICE_GROUP 并跳过 M self-edit。 | 即便 root 已归档，也不运行后续 M。 | snapshot/模型完整性 C；“不能继续不训练诊断”为 B，新增独立编排；formal Period 原样保留。 | formal collection 不能消费部分 GRPO group；观察流水线可以独立。 |
| O11 | period.py:80-111；所有 self-edit package P0 必须是最终 selected S；self-edit group 不可用即 ABORTED_SELF_EDIT_GROUP，M 不发布。 | M 阶段可能未发生；Service selected version 可保留。 | lineage C；诊断中记录 M failure/NOOP，保留父 M；若其他配置阶段已到真实终态仍可 DIAGNOSTIC_COMPLETED，否则 BLOCKED。 | 保证 M 面向最终 Service；不强迫发布坏 M。 |
| O12 | period.py:120-168；只有显式 phi_update 才训练；training input 必须含 r_service/r_self 两种 GRPO groups，model refs 对齐，返回不可变 ModelSnapshot 且只改 φ weights。 | trainer failure 另存 TRAINING_FAILED；无 hook 时状态是 READY_FOR_TRAINING。 | C（formal contract）；DIAGNOSTIC 不调用 phi_update/group_advantages，另记 DIAGNOSTIC_COMPLETED，不复用 READY_FOR_TRAINING。 | formal训练约束不变；Diagnostic 是独立运行目标。 |
| O13 | experiments/rsi/examples/open_world_usami.py:31-65；正式多 Period 只在 READY_FOR_TRAINING/COMPLETED 后加载 output snapshots；validate-designer 仅验证一次 challenge。 | 任一正式组失败即停；单次 Designer CLI 不进 Service/P/K/M。 | B：加独立 status machine/checkpoint；下一 Period 只加载实际 selected snapshots，勿把单次测试称为端到端。 | 保持训练状态语义。 |

## B. 重复校验的审查结论

| 规则家族 | 重复实现 | 处理判断 |
|---|---|---|
| Task Schema / 请求-目标来源 | TaskDraft（designer.py:116-165）→ compile_task()（:522-618）→ TaskSpecV2/check_task_scope（tasks.py、runner.py:435）→ Customer delegation（runner.py:440-453、customer.py）→ communication evaluator。 | 目前混合结构、目标来源和 NL 理解。结构与目标来源保留；NL span/keyword/unique line lookup 收敛到一个版本化 RequestBundle 的 goal_id→clause_id→rendered text provenance。 |
| 对象/所有权/权限 | Grounder、Compiler、TaskSpec scope、Runner、Engine、Reference、Transition、Oracle。 | Grounder 防错绑，Compiler/Certificate 认证，Runner/Engine 拦越权，Oracle 独立复核；不是重复实现同一事实。可共享纯校验代码，但不能删除独立运行时/裁判边界。 |
| 任务可达性 | compile_task() 静态约束→certify_task() 有界 Reference 搜索→verify_task_certificate() 重算→Package verifier→Episode Replay。 | 每步验证对象不同；分离 COMPILE_REJECTED/UNSAT/UNKNOWN/unsupported 是可观测性改进，不是放宽认证。 |
| Model protocol | Designer function parser、ResearchHost Schema validator、ProgramServiceAgent task parser、native Service parser。 | 发现 native Service 接受而 RSI adapter 拒绝的纯文本 reply；需要共享语义的 Parser，而不是更多正则或自动构造 tool call。 |
| Cost/attempt limits | World slots、Grounder、proof、Host model/token/step/candidate、P action、Episode、collection reserve。 | 不是业务真值，但正式实验要预注册并计量。诊断可另设明确预算，不能清零历史成本。 |
| Customer consent/quote | Service reply→render_offer→Customer decision→CustomerRuntime→authority proof→Engine→Oracle/Replay。 | 不能因多层校验而删掉。报价与结构化授权必要；应改进的是从自由文本关键词猜意图。 |

## C. 结构化 Challenge 与 Customer Request 的替代方案

不再让 Designer 同时发明自然语言并要求正则证明文字里编码了全部内部目标。业务 Goal 是权威数据；对顾客展示的句子是有来源、可重算的呈现。

1. 新增版本化 RequestBundle/CustomerIntentSpec：symbolic customer、公开商品描述选择条件、目标 remedy/数量/期限/费用上限/交互要求、goal_id。只引用公开 catalogue 中的类型和关系，不含 World ID、Reference 路径、Oracle 私有标签或测试答案。
2. Grounder 继续绑定到多个训练 World；Host 将真实 Customer/line binding 加入私有端，然后用版本化 renderer 生成初始 Customer Request 和 goal clauses。每个 goal_id 对应稳定 clause_id，不要求模型复制原句或写出内部 family/issue。
3. 复用 compile_task()、Customer delegation、原生 TaskSpec、certify_task()：由同一 RequestBundle 派生任务目标及来源绑定，验证 ownership、许可 remedy、数量、期限、费用、退货/外部事件和 Reference 可达性。
4. 多解时先按完整 candidate hash 排序或按公开、无泄漏字段做记录抽样，再截断 Grounder budget。NO_MATCH、BUDGET_EXHAUSTED、COMPILE_REJECTED、UNSAT、UNKNOWN、CAPABILITY_UNSUPPORTED 必须分开。
5. Service 的自然语言理解仍由真实 Service 执行、Oracle/Outcome、通信诊断和独立评价观察。未来若 Customer LLM 改写请求，必须用独立机制确认改写仍表达同一结构目标；歧义就澄清/拒绝认证，不能仅靠第二个 LLM 说“语义相同”。
6. 旧 TaskSpec/证书/Replay/Manifest 保持版本和 hash 不变。新协议单独版本化，不全局放宽旧 public_request_span validator。

三层判断必须区分：

- **业务目标合法性（C）**：冻结 World、真实权限、前置事件、数值约束合法，并由独立 Reference 认证。
- **公开请求一致性（C）**：每个用于评分的 goal 都获已登记 Customer Intent 授权，不允许 Designer 私加；依赖结构化来源绑定，不依赖关键词或连续子串。
- **Service 自然语言理解**：Service 是否理解实际展示的请求仍由运行结果评价。Compiler 不能替 Service 判断语言，也不能因为 Service 失败就改写评分标准。

## D. 不训练的真实模型端到端 DIAGNOSTIC 方案

不能只给 run_open_period() 设 phi_update=None：它仍要求正式完整 root/selection/reward groups 和 reserve budgets，USABLE 失败会提前跳过 M。也不能把 propose_open_challenge() 扩名为“端到端”，因为它没有 Service/P/K/evaluation/M。

新增薄的 Diagnostic orchestrator（建议 integrations/rsi_usami/diagnostic.py；CLI 给 open_world_usami.py 增 diagnostic 子命令），复用原有组件，不复制 Engine/Oracle/Reference：

1. **Manifest 与隔离**：mode=DIAGNOSTIC、training_eligible=false、源 hash、Factory/Provider/model 身份、seed、train split、预算/尝试上限、UNKNOWN_COST。拒绝 validation/heldout 与独立 Task overlap；任何 candidate/diagnostic artifact 永不进入 collector。
2. **World**：复用 WorldPopulation、design_world_slot、native builder、verify_build。SAT/UNSAT/UNKNOWN/ERROR/duplicate slot 都真实记录；在同一个声明预算内尝试新 slot。结构多样性只按 world_structure 衡量。
3. **真实 Designer**：复用真实 OpenAIDesignerProvider 和抽象 Challenge Schema；Catalogue 增匿名关系摘要。记录 request/raw response/schema/Grounder/Compiler/Reference。格式错、编译拒绝可有限重试；向模型只返回允许的 rejection，不返回 hidden binding/witness/Oracle private details。修 M0 拒绝时 attempt 不增长的状态机 bug。
4. **认证**：复用 OpenChallengeBridge.certify()；逐个记录候选 World/binding/compiler/proof。只有 CERTIFIED 注册 NativeTask；如果一个挑战无解/不支持/预算不足，可继续另一个挑战；最后无认证 Task 就标 NO_CERTIFIED_CHALLENGE，不启动 Service。
5. **Service baseline**：对认证题使用真实父 Service、现有 P0/Native Runtime、Customer runtime、Engine、Oracle、Outcome、Replay。每次模型请求、回复、工具拒绝、成本和状态真实存档。episode失败可新开 episode；写操作结果未知时先 Replay，不重发。
6. **P/K**：一个诊断 root 足以观察 baseline→P/K patch→probe→independent selection。候选格式错/静态拒绝/NOOP/无提升均保留；候选冻结后用独立预注册 task package，沿用模型/seed/budget/purpose/partition/Replay/select_service 与 safe rules。无提升选 parent，继续 M。
7. **M**：针对实际选中 Service（candidate 或 parent）构造 support/probe package，调用 ResearchHost SELF_EDIT；M 候选仍经独立 selection。无效、NOOP、UNKNOWN、无提升都可真实记录，保留父 M。
8. **明确不采集训练**：不调用 collect_*_group、reserve_group、training_records、group_advantages、phi_update；不要求 2 roots、完整 formal reward export 或 logprobs 对齐。仍按一个 manifest ledger 记录所有 model call、episode、token、step、墙钟成本。
9. **终态**：DIAGNOSTIC_COMPLETED 表示每个配置阶段有真实终态，允许 REJECTED/NOOP/NO_GAIN/UNSAT/UNKNOWN；DIAGNOSTIC_BLOCKED 表示安全、隔离、Replay或不可恢复配置/provider问题阻断依赖阶段；DIAGNOSTIC_BUDGET_STOPPED 表示总预算耗尽。每个 stage 独立标状态。Summary 写 training_updates=0、training_eligible=false、formal_experiment=false；端到端完成不代表 RSI 有效。
10. **检查点**：World Period、Designer call、Challenge receipt、closed Episode、P/K stage、paired evaluation、M stage、final selection 均原子存档。只从完整边界恢复；不重放状态未知的 write。恢复时复核上游 hash、模型、partition、package purpose、预算和选中快照。预算延长是新额度，不能清零已消费成本。

预算从一个 Manifest 派生，覆盖 World slot/attempt、Designer/correction call、总 token、Grounder binding、Reference node/step、Service decision/tool call/episode、P/M Host step/candidate、pair 数与墙钟时间。实际 endpoint/ModelSettings/timeout 记录；未知成本标 UNKNOWN_COST。格式修复只修输出结构，业务动作每次由原 Engine 验证。

## E. 最小修改顺序（本轮审阅稿）

| 顺序 | 修改 | 关键文件 | 可核验结果 |
|---|---|---|---|
| 1 | 提交审计和修改方案，不动正式代码。 | docs/rsi/ | Gate 家族、原始 AST 索引与 source hash。 |
| 2 | 对齐结构化 Intent 和请求文本来源，保留旧 TaskSpec。 | designer.py、grounding.py、tasks.py、runtime/customer.py、open_world.py；新协议/renderer。 | 一个 abstract challenge 对多个真实合法 binding；文本不需含内部 family/issue；旧证书/Replay 原样有效。 |
| 3 | 修真实模型 parser 差异和有界 retry。 | adapter.py、runtime/agents.py、M0.py、client.py。 | plain-text reply 在 RSI/native 语义一致；工具操作仍需一个完整 call；每次修复请求单独入账；M0 拒绝次数上限真实有效。 |
| 4 | 加独立不训练编排和 checkpoint。 | 新 diagnostic.py；open_world_usami.py 子命令；复用 Host/Adapter/evaluator。 | 一次有限真实调用实际走到 World、Challenge/Reference、Service baseline、P/K probe/evaluation、M self-edit/evaluation；所有阶段和 Replay 可见；0 训练更新；即使无提升也有完整 DIAGNOSTIC 终态。 |
| 5 | 形式上隔离诊断 artifact。 | collection.py、period.py、archive/package schema。 | Collector 明确拒绝 training_eligible=false；正式 seeds/budget/task purpose/data split/score/safety 不变。 |
| 6 | 新协议离线测试，之后一次预算明确的真实诊断。 | 对应 tests 与运行报告。 | 证明无假证书、无重复写操作、状态分离；真实调用额度/成本开跑前声明并按实报告。 |

本轮只完成第 1 项。第 2–6 项未实施。按用户要求，先审阅完整清单和修改方案；审阅前不启动在线模型、正式训练或 held-out。

## F. 当前真实模型路径能否开箱即跑

正式路径接受用户 Factory（CLI 的 --factory 必填）来装配 Provider、Host、model snapshots、task registries 和 evaluators；真实模型诊断 CLI 可单独完成一次 proposal/certification。当前仓库没有默认完整 live Factory；validate-designer 也只运行到 challenge certification。因而不能据此声称现成的真实模型 RSI 全链路已经跑通。诊断方案必须包含一个明确可复现的 Factory 配置与模型协议记录。

## 审计附录与穷尽性边界

静态扫描 48 个运行边界模块：11,580 行源码、1,402 个 if 分支、1,033 个潜在阻断/状态/异常位置、1,025 个 class field。它们不是 1,033 个独立业务 Gate：同一规则多次实现，普通状态分支和模型字段也计入。主表是归并后的语义 Gate；原始索引用于回查。

- GATE_REGISTER.csv：AST 扫出的 raise/assert、异常或失败状态写入、break/continue、选择结果等潜在阻断点，共 1,033 个 syntactic sites。
- SOURCE_BRANCHES.csv：上述模块全部 1,402 个 if 条件，包含普通业务分支；用于定位，不表示每条都阻断链路。
- SCHEMA_REGISTER.csv：1,025 个 class field 声明；字段只有被 Pydantic/runtime consumer 检查时才构成 Gate。
- generate_gate_inventory.py：只读 AST 索引生成器；在审计基线 checkout 后运行 python3 docs/rsi/generate_gate_inventory.py 可重现附录索引。
- GATE_AUDIT_SOURCE_MANIFEST.json：审计基线、文件数、行数及源 SHA-256；覆盖入口、Designer/World/Task、native runtime/business/oracle/replay、RSI Host/collection/evaluation/period/provider、seed programs 和 model client。

CSV 中 A/B/C 是由源码文本规则产生的初筛标签，不能代替主表的人工语义判断；单独字段、if 或日志行未必是主动 Gate。依赖库内部、OS/TLS、外部 API 服务端、用户 Factory、运行环境和生产模型的隐式限制无法由源码静态穷尽，需在真实诊断记录中观察。
