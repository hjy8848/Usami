# Usami 2.0 实施状态

更新日期：2026-10-21。依据实施计划 v0.2 和 P0 研究契约推进，整体目标尚未完成。

## 当前已经实际实现

### P0：可执行契约与独立校验

- 不可变、内容寻址的来源、事实、公开信息请求、沟通义务和实际消息模型。
- 核对实际送达文本的金额、日期和状态；正确 fact_ref 不覆盖错误正文。
- 漏答、错误事实、错误完成声明、语义未判定分别记录。问句、条件和历史陈述不直接当作肯定事实。
- 提前结束不能绕过已经触发的必要信息义务。纯信息任务不要求伪造交易状态变化。
- Service / Customer / Learner 等角色的来源投影和 Working Memory 的公开来源限制。
- 带来源的合成业务参考分布、固定采样计划、拒绝和 UNKNOWN 生成记录、拒绝重复样本替换。
- 挑战质量诊断按后果等价类计数；仅改 ID 或统一平移价格/时间、不改变约束结构，不计为新的结构。
- 局部检查点比较要求相同状态、历史、授权、时钟、事件游标和预算，并调用独立执行验证器。
- 就绪政策缺字段不能冻结；脚本不能替代真实 S0 基线；Smoke 不能冒充正式采样；相关世界不能当独立样本。
- 就绪统计使用分层权重和 Clopper–Pearson 区间，并对声明的维度与分层作 Bonferroni 调整。契约测试模式即使模拟得到 PASS，也不允许正式学习。
- 原生 Schema 导出、不可覆盖发布和离线内容校验命令。

这些是接口与校验代码。P4 Runner 现在可以为单 Episode 记录真实执行证据并离线 Replay；检查点比较和就绪检查的正式证据验证器仍未接入批量冻结实验，本阶段没有正式 R2 通过记录。

沟通的默认抽取器目前只支持明确的中英文金额、日期、数量和业务状态表述。复杂自由文本保留 UNRESOLVED；不宣称覆盖任意自然语言，也不让辅助引用自动证明整段文字正确。

### P1：原生电商执行核心

新增 commerce-2.0.0 Adapter，使用既有 usami_harness.Engine、原生独立 Oracle 和 Replay，未修改旧八领域规则。

已经实际执行并测试：

- 多 SKU、两个仓库、库存预留/释放/出库和冻结的路线估计。
- 两个不同目标 SKU 均可真实完成换货。
- 按原始实付分摊到购买单位；部分退款的总和保留优惠和舍入后的每一分。
- 工单、真实证据验证、审批申请、报价、成交、退货、退款释放和换货履约。
- 报价绑定目标、数量、渠道、金额、版本和库存/配送状态；旧报价变化后需要新的有效同意。
- 没有独立业务委托，不能因为模型想调工具就获准准备业务；没有真实报价同意，Reference 阻止成交。
- 研究 Sandbox 能产生真实未经同意的成交，由独立规则确认违规；它仍不能读写其他顾客对象。
- 退货收货后，退款释放需要独立的第二次同意。
- 真实外部审批、收货、库存和路线事件；实际事件处理与独立预期投影分别实现。
- 重复成交不会重复记账；取消未结算承诺会释放预留库存。
- 独立 Oracle 能检测故意损坏的实际查询结果和实际扣款变更。

实际 transitions 不导入 Reference；Reference 不调用实际 transitions 或实际查询输出。两者共享 Schema、稳定标识及基础整数分摊函数，状态变化分别实现。

P1/P2 历史证明中的 Customer 授权由明确标注的离线夹具独立建立。当前 P3 新交易 Episode 已增加请求原文和目标对象绑定；这仍不等于真实 Customer LLM 保真度已验证。

### P2：冻结世界构建与多目标认证（部分实现）

- `ScenarioSpec` 支持多个顾客、订单、订单行、SKU、仓库、库存区间、属性及有界线性关系约束；模型不能提交任意 Python、完整 `World`、Engine、Reference 或 Oracle 实现。
- Builder 将设计别名转换成种子绑定的业务 ID，保留每次候选的约束拒绝原因，并区分 SAT、完整枚举 UNSAT、预算耗尽 UNKNOWN。SAT 会由独立证书器读取实际生成世界，重新核对数量、实付、属性、库存、路线、事件和未初始化交易状态。
- `TaskSpec` 支持一项任务中的多个订单行目标、兼容规格、补款上限、承诺送达日期及只读信息请求。目标计分允许多个满足同一硬约束的 SKU；额外或未请求的结算不会算作完成。新 Designer 交易任务使用 `TaskSpecV2`，要求目标绑定公开请求原文、明确提出的处置方式和唯一冻结订单行；历史 v1 Task 保留 Replay 兼容。
- 信息目标必须绑定到实际公开顾客原话中的请求片段。计分使用独立事实来源和 Service 实际送达文本；只读任务无需交易状态变化，擅自产生任务范围外结算会失败。
- CLI 已能导出/校验现行 Schema，以及构建、密封和离线重建验证冻结世界包；输出只记录构建证据，明确不声称任务可达或交互可达。
- 新增有界 `certify_task`：以只读冻结世界、`TaskSpec`、私有 `CustomerScenario` 和固定 `ProofBudget` 搜索退款/换货/补发方案。候选业务操作逐步调用原生 Engine 的 Reference 模式；每步保存 Oracle 结果与原生 Replay。候选路径会保留为可审计的私有 witness。
- `CustomerScenario` 单独密封测试用业务委托、报价接受范围、补款/到达限制，以及审批与退货事件计划。证明器只在派生副本中建立测试委托和绑定精确报价条款的同意，原始冻结世界不变。审批、退货和退款二次同意逐步记录；事件实际投影必须与独立 Reference 投影相同。
- 结果区分 `CERTIFIED`、`UNSAT`、`UNKNOWN`。仅在有限候选计划完整枚举且无不支持条件时报告 `UNSAT`；预算耗尽或遇到尚未实现的交互/送达事件则报告 `UNKNOWN`。已证明一条路径即可证明业务可达，但不会冒充满足 `minimum_witnesses` 的多解要求。
- 新增 `certify-task` / `verify-task-certificate` 离线 CLI，证书封存任务、私有 CustomerScenario、操作轨迹和 witness；复核会重建冻结世界、重跑有界搜索并复算全部轨迹。更改证书内容会被哈希或重建校验发现。
- 新工程夹具实际走过不变的 Engine、Oracle 与 Replay：两条订单行联合处理；D/E 两个符合规格、价格和时限的替代品均通过；错误规格、超期、超预算的替代品失败；完整枚举无解与预算不足分别判为 UNSAT 和 UNKNOWN。

边界：这是受限的 Reference 业务计划搜索，不是任意操作规划器。`CustomerScenario` 是确定性私有证明夹具，委托/同意由它在证明分支生成，不会注入 Service；因此不等于自然 Customer、自然语言授权或交互可达证明。审批与退货事件计划在搜索前密封，不读取模型正确性或 Oracle 标签。当前没有配送完成事件；要求 `target_stage=delivered` 的任务会是 `UNKNOWN`，不会假装可达或宣称无解。

P2 本身仍未完成：更一般的 Reference 搜索、完整对话可达性证书以及配送完成事件。P3 的自然 Customer / AuthorityProof 已作为单 Episode Runtime 独立接入，但没有把自然交互折叠进 P2 业务证明。已实现证书只证明受限业务动作在冻结世界和登记的顾客行为/事件下满足状态目标；不代表 Designer 自主出题能力或正式题库已通过认证。

## 前序阶段验证记录（非本次回归）

| 检查 | 实际结果 |
|---|---|
| 前序阶段 `tests/test_usami_v2_*.py` | 68 passed |
| 新增 Task Certification 定向测试 | 6 passed；覆盖双替代 SKU witness、证书复核、UNSAT/UNKNOWN、审批/退货事件、二次同意与篡改检测 |
| P0/P1 新增测试 | 45 passed |
| P2 Builder / TaskSpec / Schema 定向检查 | 18 项前序检查与 6 项任务认证检查通过 |
| 相关综合回归 | 178 passed；其中旧测试 144 项，包含旧 Oracle、售后、对话过程、Skill、v3 Agent、开放组合、A/B 和 Live 入口 |
| 属性测试 | Hypothesis 的分摊守恒、随机部分退款和库存承诺状态机实际通过 |
| Python 兼容 | 在现有 Python 3.9.6 环境实际运行 |
| Schema CLI | P2 阶段核验 27 份；P3–P5 初次核验 54 份；本轮新增 V2 合同后重新导出并复核 58 份，`verified=true`、`model_calls=0` |
| 在线模型调用 | 0 |
| 真实业务错误就绪 Gate | 未运行 |
| Designer / Service 学习收益 | 未测量 |
| 前序全仓回归尝试 | 用户要求停止；中断前累计 287 passed（309.79 秒），不构成完整回归结果 |

### P3–P5 定向实现状态（本次更新）

| 工作包 | 已实现的最小纵向切片 | 边界 / 尚未声称 |
|---|---|---|
| P3 Customer Runtime | 固定身份和私有 CustomerProfile；新交易任务用 V2 请求片段绑定、唯一订单行委托、顾客侧委托/撤销/披露与精确报价同意；结构化确认须与顾客文本中的明确表达一致 | 文本匹配是有限词法规则，不是通用自然语言理解；历史 v1 Profile / Episode 保留 Replay 兼容；未做真实 Customer LLM 保真度验证 |
| P4 Episode Runner | Customer / Service Adapter 接口；每个业务操作走原生 Engine、Reference 或 Sandbox、Oracle 与 trace Replay；OutcomeV2 分开评分业务目标、过程错误、安全违规及交互可靠性；事件级重建和篡改检测；原子私有 Episode 归档及 `verify-episode` | 运行入口是 Python API `run_episode()`；CLI 提供离线校验，没有通用的在线运行 CLI；未接真实 LLM 运行 |
| P5 Designer | 两阶段 Designer：先提受限世界，再在冻结世界上提任务；最多三次确定性编译反馈；来源分布/预登记采样槽绑定；训练证据哈希白名单；Reference 证书与可选自然交互 Episode Replay；交易目标绑定公开原文并唯一映射到冻结订单行 | Designer 的动态质量向量是诊断，不是 Skill 接受 Gate；有限词法规则会保守拒绝未覆盖表达；未证明真实模型能稳定生成高质量题目 |

本轮一致性修正只运行 `tests/test_usami_v2_runtime.py` 与 `tests/test_usami_v2_designer.py` 两个定向模块，21 passed。断言覆盖隐藏/歧义目标、未请求处置选项、错绑委托、结构化同意文本不一致、拦截错误与实际安全违规的区别、未完成目标的过程遗漏、Service 协议错误分类，以及 Episode Replay。未运行全量回归。

本次没有调用真实模型。新增聚焦测试之外的既有测试、不同 Engine Adapter 的交互、真实模型请求格式与运行成本均未在本次验证。当前 58 份 Schema 导出并离线复核通过，`model_calls=0`。

此前的相关综合回归检查有 178 项通过；综合回归完成后新增了离线 CLI 和工具面覆盖，并加强类型/时间边界，最终对全部 P0/P1 新增测试重新运行，结果为 45 passed。P2 Builder、任务与 Schema 变更在本轮另行运行了 18 项定向检查。本次 287 项通过后按用户要求中断全仓回归，不将中断结果表述为完整回归。

开发依赖新增 Hypothesis，生产依赖未扩大。本机测试把新增依赖安装到独立临时目录，没有改动原工作树的虚拟环境。

通用复现命令：

    python -m pip install -e '.[dev]'
    python -m pytest -q tests/test_usami_v2_contracts.py \
      tests/test_usami_v2_commerce.py tests/test_usami_v2_properties.py

目前实际可用的 CLI：

    python -m usami_v2.cli schema --output /tmp/usami-v2-new-schemas
    python -m usami_v2.cli verify-schemas --directory /tmp/usami-v2-new-schemas
    python -m usami_v2.cli build --scenario scenario.json --seed 1 \
      --output /tmp/usami-v2-world-001
    python -m usami_v2.cli verify-build --directory /tmp/usami-v2-world-001
    python -m usami_v2.cli certify-task --world-directory /tmp/usami-v2-world-001 \
      --task task.json --customer-scenario customer-scenario.private.json \
      --max-plan-candidates 256 --max-operation-steps 64 --max-witnesses 2 \
      --minimum-witnesses 2 --output /tmp/usami-v2-task-cert-001
    python -m usami_v2.cli verify-task-certificate \
      --world-directory /tmp/usami-v2-world-001 --directory /tmp/usami-v2-task-cert-001

所有输出目录必须不存在。上述构建、证明和复核命令不查凭据、不发模型请求。`verify-build` 只证明世界约束；`certify-task` 证明有限业务计划下的状态目标可达。CustomerScenario 与 witness 是私有验证档案，不能注入 Service。当前 `interaction_certified=false`，所以不能把业务可达说成完整自然交互可达，也不产生进化成功声明。

## 仍未完成的整体范围

| 工作包 | 当前状态与下一步 |
|---|---|
| P0 的运行级接线 | 契约、Customer/Service 来源投影、离线 Episode Replay 与私有归档已有最小接线；正式 R2 验证器尚无通过记录 |
| P1 完整业务契约 | 原生核心已实现；持续由 P2/P3 场景与交互认证补足完整业务链路 |
| P2 Builder / 联合目标 | 部分实现；受限 Builder、独立世界约束证书、联合终态评分、有界 Reference 计划搜索、多合法 witness、Oracle/Replay 复核及冻结审批/退货事件计划已有。通用搜索、自然交互与配送完成事件仍待补 |
| P3 自然 Customer Runtime | 最小离线运行时已实现；固定身份、Customer 侧委托/撤销/披露、精确报价确认与 AuthorityProof 已接入。真实 Customer LLM 保真度仍未测 |
| P4 独立业务 Runner | 最小 Python Episode Runner 已实现；原生 Engine、Oracle、沟通与状态评分、精确 Replay、私有归档可运行。没有通用在线 CLI；未做全量回归 |
| P5 两阶段 Designer | 最小入口已实现；世界/任务分阶段提案、受限编译、来源和训练证据绑定、有界 Reference 证书及可选交互 Replay、结构签名和诊断向量已接入。真实模型生成质量未验证 |
| R2 业务错误就绪 | 尚无真实 S0 数据；具体模型/采样/预算需在正式运行前冻结 |
| P6 局部诊断与双重对照 | 比较契约已实现，真实检查点恢复、替代搜索和完整任务配对仍未接通 |
| P7 三种记忆 | 公开 Working State 契约已有，运行中更新、案例存储和检索未接通 |
| P8 Learner / 验收 | 未接通，尚无候选经验或动态接受结果 |
| P9 递归 Controller | 未实现 |
| P10 真实实验 | 未启动，不使用旧实验代替 2.0 结果 |

后续继续沿既定目标实现，不把当前阶段改称为完整重构。
