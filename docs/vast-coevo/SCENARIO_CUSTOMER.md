# Scenario-Driven Customer：After-sales v3

Customer 模拟普通顾客的目标、知识和选择，Service 自己规划查询、验证、审批及结算。Harness 只验证用户实际提交的结构化决定，并继续用原 Session、Engine、Reference、Oracle 和 Replay 执行。

## 官方参考与取舍

核对日期为 2026-10-20。官方 tau2-bench 当前 main 已有后续版本功能；本次只参考其文本用户模拟部分。参考版本固定为 tau2-bench `96a3ef92329baf908ffe9dfe188cea34e8701d2a`、tau-bench `59a200c6d575d595120f1cb70fea53cef0632f6b`。

| 官方源码 | 设计原则 | Usami 的实现和取舍 |
| --- | --- | --- |
| [tau2 tasks.py：StructuredUserInstructions / UserScenario](https://github.com/sierra-research/tau2-bench/blob/96a3ef92329baf908ffe9dfe188cea34e8701d2a/src/tau2/data_model/tasks.py) | 用户场景和 EvaluationCriteria 分开；区分来意、已知与未知信息 | 从冻结 Profile 与公开 Task request 投影 UserScenario；不传目标断言、Reference 路径、证书或外部事件结果 |
| [tau2 user_simulator.py：system_prompt / generate_next_message](https://github.com/sierra-research/tau2-bench/blob/96a3ef92329baf908ffe9dfe188cea34e8701d2a/src/tau2/user/user_simulator.py) | 全局行为约束、场景和实际消息历史驱动下一条用户回复 | ScenarioDrivenCustomer 使用已有兼容 API 传输；模型自行产生自然语言、信息披露及 v3 授权决定 |
| [tau2 simulation_guidelines.md](https://github.com/sierra-research/tau2-bench/blob/96a3ef92329baf908ffe9dfe188cea34e8701d2a/data/tau2/user_simulator/simulation_guidelines.md) | 按需披露已知信息、不编造、围绕场景交互和结束 | 不再用固定 Customer 的关键词分支替代 LLM 决策；结束意图和真实业务成功分别记录 |
| [tau2 simulation.py：BaseRunConfig / TerminationReason / SimulationRun](https://github.com/sierra-research/tau2-bench/blob/96a3ef92329baf908ffe9dfe188cea34e8701d2a/src/tau2/data_model/simulation.py) | 记录 trials、seed、双方配置与成本；区分 user/agent/基础设施错误，用户行为复核可单独运行 | 保存双方原始请求、输出、分角色 Token、原始终止原因及独立 Fidelity；不采用幻觉检测后自动重跑/筛选较好运行 |
| [tau-bench envs/user.py：LLMUserSimulationEnv / VerifyUserSimulationEnv](https://github.com/sierra-research/tau-bench/blob/59a200c6d575d595120f1cb70fea53cef0632f6b/tau_bench/envs/user.py) | 用户根据客服消息逐步回复；另有 Reviewer 方式 | 不增加在线 Reviewer，不自动修改用户业务选择。只沿用 v3 预算内的格式恢复 |

不复制它们的业务规则、工具、奖励函数、STOP token 或 telecom 用户工具环境。After-sales 用户不直接操作商家的后台；v3 的当前回合授权引用和两次精确报价确认继续存在。

## 已有确定性 Customer 的核对结果

开始时本地与远程研究分支均为 `7f5f43d`。该版本已经把公开需求直接传给 Service、在普通模式下避免重复授权同一操作、用顾客可见的订单行状态代替完成关键词，并保留 `--repeat-authorization-pressure` 压力模式。这些修复保留。

它仍会按代码选择准备类操作，适合隔离协议和 Engine，不适合代替普通用户的动态选择。因此没有继续扩展它的关键词分支；新增模式由模型根据场景及真实对话选择，确定性规则不会修正 LLM 的业务决定。旧确定性 A/B 记录不改写，也不能把更换 Simulator 带来的差异算成 Skill 的改善。

## 冻结场景与输入边界

`usami_dialogue/user_scenario.py::scenario_from_task()` 产生稳定 ID、version、内容 hash，并绑定 world/task/profile hash。场景含公开来意、Profile 中顾客本来知道的 facts、任务允许的偏好范围与初始偏好。`unknown_info` 只有所有场景统一使用的未知类别名称，没有实际审批结果等值。

运行前重新投影并逐项比较，身份、对象、来意、事实或偏好范围发生变化时拒绝运行。嵌套 dict 即使被调用者修改，也会在校验 hash 时被识别。示例见 [aftersales-user-scenario.json](../../experiments/vast_coevo/examples/aftersales-user-scenario.json)，它从仓库现有冻结任务登记生成，不是手工编造的世界。

每次 Customer 请求包含冻结场景、真实公开对话、本人可见的订单/订单行状态、实际展示的报价条款，以及当前可表达的授权选择。不会包含完整 World、隐藏规则、Reference Witness、评分 Goal、Oracle 期望或审批/退货事件的隐藏结果。

任务中的 `customer_request` 本来就是公开文本，按原样使用；本实现没有声称能自动证明任意自然语言源文本不存在答案泄漏。场景工厂不从 Witness 或 Oracle 合成这段文本。

## 用户决定，Harness 精确绑定

LLM 模式把准备类授权显示为 `id + description + order/item + option/pickup_slot`。列表不表示操作合法，也不是推荐执行顺序。模型可以选择零项、提问或拒绝。Harness 不从自然语言、最终目标或客服要求推导许可。

结算与释放退款不出现在普通授权菜单中，必须通过 `offer_response` 对 Service 实际展示的报价分别决定。展示内容包括真实金额、支付渠道、是否需退货和报价阶段的有效期；已经同意、等待退货后的退款不把原报价期限误当成新的释放期限。内部精确 Operation 仍由原 v3 引用解析。偏好改变、未展示、旧回合引用、报价过期等仍使用原可信验证器。

当前 v3 还会在报价送达前阻止 Service 提交与当前偏好不符的 `offer_ref`，因此这种情况首先是 Service 协议拒绝；没有为了让 Customer 展示“会拒绝错价”而放松它。Customer 对有效报价也可以自行拒绝；不强制成交。

## 两种模式与历史兼容

| 模式 | 用途 | Customer API | 决策来源 |
| --- | --- | --- | --- |
| `deterministic` | 协议隔离、回归、重复请求压力测试 | 0 | 现有 FixedCompliantCustomer，压力测试须显式启用 |
| `scenario-llm` | 自然交互、后续 Skill A/B | 显式授权执行后才调用 | 真实模型输出，无本地业务选择修正 |

`TaskRunConfigV3` 增加可选 `customer_mode` 与 `user_scenario` 元数据，不创建 v4/v5 对话协议。旧配置不序列化这些字段，按 `legacy-v3` 精确重放。新 CLI 输出显式记录所选模式及场景。确定性压力规则不能附加到 LLM Customer。Scenario Customer 固定，不注入/演化 Customer Skill；Service 的 Skill 注入与选择规则未改。

## Customer Fidelity

`usami_dialogue/customer_fidelity.py::evaluate_customer_fidelity()` 离线检查原始模型尝试和可信事件，单独输出 `customer-fidelity-v1`：

- 确定性：结构/当前 action 引用、结构化事实、冻结偏好、原 v3 的身份范围及报价确认拒绝记录。
- 高置信度场景不一致：声明了不在 known_info 中的字段/值，或越过冻结偏好。
- 需要复核：自然语言中的事实、同一操作再次授权的理由，以及目标未可见完成却结束的意图。它们不会由正则推断为“幻觉”或“错误终止”。

报告保存 execution/scenario hash、来源模型调用索引和 request hash、分角色成本、原始/诊断终止原因和自身 hash。自然语言尚未独立复核时会显示 `needs_review`，不能把协议通过冒充完整用户保真度通过。当前不调用 LLM Reviewer。

`goal_observed_complete` 只比较顾客自己的偏好与本人可见的订单行结果，不读取隐藏评分 Goal。用户可以 `customer_declines` 或 `customer_stops`，未满足目标就结束只标需复核。`legitimate_refusal` 的 Oracle 归因仅在离线报告中计算，不回流 Customer。Customer 错误、Service 违规与最终任务成功始终分别保留；Fidelity 无选代权，也不删除任何 Service 证据。

## 检查与运行

默认只校验冻结登记、输出场景，不创建 API client 或读取凭据：

```bash
.venv/bin/python experiments/vast_coevo/examples/after_sales_service_v3_diagnostic.py \
  --customer-mode scenario-llm --service-mode fixture
```

Customer 使用 `USAMI_CUSTOMER_LLM_MODEL / BASE_URL / OPTIONS / TIMEOUT / API_KEY`，以及可选 `KEYCHAIN_SERVICE / KEYCHAIN_ACCOUNT`。未指定角色字段时复用同名的 `USAMI_LLM_*` 公共网关配置。认证不写入记录；真实请求使用的双方 ModelSettings、采样选项与 seed（若配置）会保存。`seed` 不能保证外部模型服务完全确定。

得到运行授权后，先验证真实 Customer 与受控 Service；本次实现任务没有执行这个命令：

```bash
.venv/bin/python experiments/vast_coevo/examples/after_sales_service_v3_diagnostic.py \
  --customer-mode scenario-llm --service-mode fixture --execute-live-customer \
  --mode reference --output outputs/customer-simulator-smoke-001
```

默认至多 12 次远程 Customer 调用、20 次本地 Service fixture 调用，Provider 不自动重试。fixture 只读取其真实工具返回和当回合明确授权，按受控问答练习开案、证据、审批、报价、退货及二次确认；不知道 World、证书或 Oracle。它不能用于评分 Service 能力。

Customer Smoke 通过并复核保真度后，真实双方交互：

```bash
.venv/bin/python experiments/vast_coevo/examples/after_sales_service_v3_diagnostic.py \
  --customer-mode scenario-llm --service-mode llm \
  --execute-live-customer --execute-live-service --mode sandbox \
  --output outputs/scenario-service-baseline-001
```

默认双方合计最多 32 次远程调用。A/B 的候选臂增加 `--service-skill-context experiments/vast_coevo/results/after-sales-service-v3-diagnostic-with-skill-20261019-001/service-skill-context.json`，复用原 `aftersales.current_quote_consent` 上下文。应预登记重复次数和每对 seed，冻结其余配置，使用不同输出目录；两臂允许 Customer 对不同 Service 回复自然分支，不能强行重放同一 Customer 回答序列。正常顾客与确定性重复压力实验分开，不在中途挑选结果。

输出含 scenario/config/manifest、完整 execution、原 Oracle 与 task score、Replay、独立 customer-fidelity、分角色调用与 Token。execution 在 Replay 前先落盘，校验失败也保留原始轨迹。离线复算不需要模型环境或凭据：

```bash
.venv/bin/python experiments/vast_coevo/examples/after_sales_service_v3_diagnostic.py \
  --replay-execution outputs/customer-simulator-smoke-001/execution.json
```

## 验证边界

新增测试使用脚本化的 API 响应验证真实 Engine/Oracle/确认流程，不能证明真实 LLM 已具备自然用户行为。覆盖场景绑定、按需披露、用户自选/拒绝、无自动授权、未确认结算的 Sandbox 违规、退货后二次确认、篡改检测及历史 v2/v3 Replay。

本轮不运行付费模型、不开展 Skill A/B 或多代进化。真实模型的语义保真度、初始来意表达是否自然、无效请求率以及对多种客服行为的适应性，仍须在后续授权 Smoke 中测量。

2026-10-20 实际执行的定向回归：

```bash
.venv/bin/pytest -q tests/test_scenario_customer.py \
  tests/test_vnext_dialogue_agents_v3.py tests/test_vnext_aftersales.py
# 39 passed in 157.38s
```

包括脚本化 API transport + 受控 Service 的 CLI 完整落盘/离线复算、真实原生退款及退货/二次确认、未确认结算仍保留 Sandbox 违规、Fidelity 失败不移除 Service 证据、重新封装假结果仍被 Replay 拒绝，以及仓库既有 v2 和两份历史真实 v3 execution 的精确重放。模型响应在这些测试中来自离线夹具；实际在线 Customer/Service 请求均为 0。没有执行全仓回归或真实模型 Smoke。
