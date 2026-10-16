# Designer–Service v1

研究主线是「从错题里发现并放大，从正确题里引导犯错」。本协议将场景设计和正常顾客分开，不改变业务系统。协议名为 `designer-service-v1`；旧 Examiner、Customer Static-Only 及历史证据不迁移、不改写。

## 实际角色与执行顺序

| 角色 | 输入 | 能做什么 | 是否进化 |
| --- | --- | --- | --- |
| Designer | 完整锚点世界、实际 Service 请求/回复/工具、Oracle、来源 Hash | 选来源、方向、假设、局部 SceneEdit、身份及业务需求 | 独立 Designer Library，静态检查后必须通过配对动态验收 |
| Customer | 正常业务需求、有限精确操作范围、身份合法可见的观察、Service 实际回复 | 自主查询、澄清、确认、发起业务请求、追问和停止 | 模型、系统策略与 Customer Snapshot 全程固定；没有 Customer Reflection |
| Service | Customer 实际对话与原生业务工具 | 自主查询和执行业务操作 | 原 Service Reflection、Static/Dynamic Gate 与回滚 |
| Compiler / Reference / Oracle / Replay | 框架内部完整证据 | 构造验证、证明、状态审计、精确重放 | 固定 |

每代顺序：

```text
已验证开发锚点 + 跨代发现记录
    → Designer 提出局部变换
    → Compiler 检查 / 证明 / 冻结
    → 独立固定 Customer ↔ Service，多轮真实对话
    → 原 Oracle + 精确 Replay + 来源绑定
    → Designer Reflection → 静态检查 → 公平配对动态验收 → 选择/保留
    → 原 Service Reflection → 原静态/动态 Gate → 选择/保留
    → 保存 D/S 的父版本、候选、实际选中版本，C 保持不变
    → 下一代
```

初始锚点来自配置中的真实 Service Task 执行。后续保留所有可用的已验证来源，而非仅最近一场；每代从完整账本按分支与业务结构分层、固定种子轮换最多 8 个提示来源，避免无限增长的上下文；不合格或未触发的案例仍保存，但不能冒充正确或错误锚点。验证阶段的 Designer 轨迹不回流训练锚点。

没有四组交叉执行插入训练。训练后的 `evaluate` 是独立开发诊断，只加载明确的 D/S Snapshot 和固定 C，在新世界执行，不调用任何 Reflector、不更新或发布 Skill、不改变训练选中版本。它不是新增公开 Benchmark，也不等于 Frozen Held-out。

## 轻量提案与 Compiler

一次 `submit_challenge` 提交：

- `anchor_hash` 与 `branch`：必须引用已独立 Replay 的真实开发案例。
- `purpose / hypothesis`：隔离、扩展或边界假设，只是待验证研究方向。
- 最多 12 个局部 `SceneEdit`：实体、字段、精确 `expected_before` 与新值。
- 执行身份、正常 `customer_need / constraints`、目标操作及最多 10 项精确业务能力。
- 可选的声明式目标 `goal`；省略时，Compiler 为 Reference 允许的非空单步转换推导目标；若 Reference 禁止，则按单操作正确拒绝题证明。

Designer 不提交完整 World 或 witness。Compiler 从来源复制世界，按白名单应用修改：项目状态/配额、项目角色关系、实例状态/资源量/依赖、账单状态和支付记录。它不改 seed、clock、版本、Rules，也不自动补账单、补权限或修理不一致的世界。字段重复、旧值不符、不存在的对象、跨项目关系错误、循环、配额或账单不变量问题均直接拒绝。

完成题通过有界 Reference 搜索（最多 512 节点、6 步，仍受原工具预算限制）找到路径，再调用原 Engine、Oracle 和 Replay 真正证明目标及 frame。找不到可靠证明就拒绝，不捏造 witness。拒绝题必须由原 Reference 在现存对象上给出真实业务拒绝条件；找不到对象不是有效拒绝题。

`frozen.json` 在任何 Customer / Service 调用前不可变写入，包含实际完整世界、差异、Reference 前后预期、程序生成的证明、证书和 Hash。`scene_profile()` 仅投影正常业务 brief 给 Customer；假设、分支标签、Oracle 证书及 witness 不进入 Customer/Service 会话。可见对象检查与保守的文本限制再拦截直接夹带的私有标签、规则代码及不可见对象。自由文本检查是静态防线，不应当被解释成自然语言语义的形式化证明。

原 `CustomerAgent.next_action()` 继续处理真实回复及递减预算。`FixedCustomerAgent` 使用单独、版本固定的正常顾客系统策略；`TaskIntentAdapter` 不接受任务范围外的写授权。Customer 和 Designer 的会话、客户端、Skill Library 和注入记录完全独立。Service 的工具参数不生成 Customer 授权。

## 双向反馈和发现状态

`anchor_from()` 只从实际操作和任务评分建立来源：

- `error_amplification`：真实 Oracle 业务违规或实际事件中的错误拒绝；从违规前有效状态出发，避免把污染的最终世界当作合法初态。
- `correct_to_failure`：真实完成/正确拒绝，Oracle 干净，存在实际业务意图；正确案例只支持提出假设，不提前认定弱点。

`DiscoveryBank.evaluate()` 将 Customer 的被接受意图、实际请求时状态、目标操作、Reference 预期、Service 事件、Oracle 和 Replay 对齐：

| 状态 | 含义 |
| --- | --- |
| `construction_failed` | 提案、修改或证明失败，尚未进入有效场景 |
| `valid_not_triggered` | 场景合法，但没有把目标请求及目标条件实际交给 Service |
| `triggered_correct` | 目标已触发，合法完成或正确拒绝 |
| `triggered_unresolved` | 请求已触发，但缺少足够事件/评分证据判断正确性；不记错误发现 |
| `verified_failure` | 实际事件中的 Oracle 错误；不暗示独立新根因 |
| `reproduced_failure` | 独立实际执行复现已知指纹/已确认规则边界 |
| `candidate_new_root_cause` | 疑似规则根因，尚未满足归因和复测要求 |
| `confirmed_new_root_cause` | 符合下述保守的规则级确认约定 |

指纹复用原 `VerifiedFailure`、Reference Code 和归一化前置状态。候选规则键为领域、操作类型与已注册 Reference 规则码；**指纹不同不能增加根因数量**。实际额外越权行为仍保留在 Oracle 证据和业务违规总数中，但与 Customer 精确目标直接触发的发现分开统计，不用于冒充 Designer 的直接发现能力。

自动确认仅覆盖有明确原规则码的直接违规，并要求：

1. 相同 Service Snapshot 下存在独立、已正确执行的来源。
2. 执行身份、目标操作及业务能力范围一致；只有一个世界字段发生受控变化，Reference 从允许变为禁止。
3. 至少两场不同 Episode 的真实、已 Replay 直接错误执行。已有任务上下文不一致、前缀污染、只有文字猜测、只有一次失败或只有指纹变化时，保留候选状态。

这是明确且有限的「规则边界归因」约定，不声称证明了模型内部心理原因或所有复杂多步因果机制；不满足该约定的真实错误不会被删除，只是不获得独立新根因确认。

## Designer Skill 与动态选择

新增独立 `DesignerSkill(type=design)`：`selection / transformations / interpretation / stop`，复用不可变 Library、内容 Hash、Patch 版本关系、静态安全检查、检索及真实请求注入。固定 Customer 的 `exploration` Skill 与 Service 的 `decision` Skill 不转换为 Designer Skill。

Designer Reflector 只学习如何选下一次有信息量的测试：如何选正确/错误来源、隔离或变更哪个前提、怎样根据真实反馈分支、何时停止重复探索。一次调用、一个 Patch，不自动修补或重试。NOOP 不制造新 Snapshot。

新候选通过静态检查后只作为未发布 Snapshot 保存。Dynamic Gate 在相同 Service、固定 Customer、基础模型、预算、来源池、起始反馈和随机种子下做父/候选配对。两臂的反馈存储隔离，不跨臂借用发现。验证开始前的来源是固定的。默认参数在 manifest 冻结：

- 至少 8 对、至少 4 个结构来源；等价名称/ID/seed 世界按现有 `business_shape()` 聚类，重复调用不扩大独立样本数。
- 有效场景率、触发率最多下降 0.05；重复率最多增加 0.05。
- LLM/工具调用及 Token 成本上限比值 1.25；缺少 provider Token 用量时证据不足，不把它记为 0。
- 固定种子的来源簇 Bootstrap，默认 2000 次、95% 区间；只有经确认的直接规则错误检出获得保守发现收益，收益下界必须大于 0。

违反质量/成本门槛为 REJECT；样本、归因、成本或稳健增益不足为 INCONCLUSIVE；两者都保留父 Snapshot，候选及全部验证记录留档。只有 ACCEPT 才发布并选中新 Designer。参数是预注册工程政策，不是已经证实的科学标准。

Service 阶段不调用 Designer Gate，仍使用原 `ServiceEvolver` / `ServiceReflector` / `DynamicGate.service`。本代真实错误通过原 `EpisodeEvidence` 进入 Service Reflection，正常任务和正确拒绝的 preflight / 回归也保留，不能用一律拒绝通过验收。

## 公平消融

同一 plan 仅修改 `strategy`，分别使用独立目录：

- `random_legal`：固定种子从同一来源选择保持原生不变量的局部变换，仍须通过同一任务 Compiler；无可证明任务时正常失败，不改规则。
- `error_only`：仅允许已验证错误来源。
- `correct_only`：仅允许已正确处理来源。
- `bidirectional`：两条分支都可选，Designer 与 Service 均更新。
- `bidirectional_fixed_designer`：两条分支都可选，但不调用 Designer Reflection；Service 机制不变。

来源权限、对手、固定 Customer、模型和预算上限一致。随机基线不调用 Designer LLM，节省的调用不补给 Service 或额外测试；不更新 Designer 的消融同理。实际消耗按角色报告。随机基线使用同一字段白名单，记录有界的原生不变量检查成本；目标证明也走公共 Compiler 的单步目标推导和同一有界搜索，不能证明的任务正常拒绝。它是明确的有限随机采样器，不声称对全部业务组合均匀采样。

## CLI

```bash
# 只查看帮助，不访问模型：
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python experiments/vast_coevo/examples/designer_service.py --help

# 显式在线运行；先配置模型、地址和凭据，不把 Key 写入 plan。
export USAMI_LLM_MODEL='<compatible-model>'
export USAMI_LLM_BASE_URL='<gateway>/v1'
export USAMI_LLM_OPTIONS='{"temperature":0,"max_tokens":8192}'
# USAMI_LLM_API_KEY，或已有 USAMI_LLM_KEYCHAIN_SERVICE / ACCOUNT

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python experiments/vast_coevo/examples/designer_service.py run \
  --root outputs/vast-coevo/designer-run-001 \
  --plan experiments/vast_coevo/examples/designer-cloudops-plan.json --models-from-env

# 完全离线：原生会话、编译、发现账本、Designer/Service Reflection 和版本选择复算。
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python experiments/vast_coevo/examples/designer_service.py replay \
  --root outputs/vast-coevo/designer-run-001
```

可分别设置 `VAST_DESIGNER_* / VAST_CUSTOMER_* / VAST_SERVICE_*`，以及两个角色的 `*_REFLECTOR_*`。解析后的实际配置在首个模型调用前冻结。若原 Service Reflector 使用不支持思考模式强制工具调用的服务商，应显式为其独立 Reflector 配置兼容参数（如 `VAST_SERVICE_REFLECTOR_OPTIONS` 中 `enable_thinking:false`）；本次未改变原 Service Reflection 的请求协议，也不自动替用户改模型设置。

已有 D/C/S Library 可用 `--designer-library / --customer-library / --service-library` 指定，允许从历史 Snapshot 在新目录分支；不得覆盖已有目录。五种策略用 `--strategy` 显式选择。示例默认 2 代、每代 2 次训练挑战，Designer 候选如需验收另花费 8 对，Service 验收另计，全程受总调用/工具上限控制。不要把配置轮数误当实际成功运行次数。

独立评价：

```bash
.venv/bin/python experiments/vast_coevo/examples/designer_service.py evaluate \
  --root outputs/vast-coevo/designer-eval-001 --source-run outputs/vast-coevo/designer-run-001 \
  --plan '<独立新世界的plan.json>' --designer-hash '<D snapshot hash>' --service-hash '<S snapshot hash>'
```

此入口强制新世界、相同执行模型/预算及已完成来源运行；只做开发诊断。最终 Frozen Held-out 仍用原独立评测体系，不回流到本协议训练或候选验收。

## 审计入口与验收边界

- `compiler.py::CloudOpsCompiler.compile`：字段、引用、不变量、可达性证明、冻结实例。
- `dialogue.py::FixedCustomerInteraction`：固定正常顾客、真实多轮反馈及授权交集。
- `discovery.py::anchor_from / DiscoveryBank.evaluate`：真实证据来源、触发、直接/附带错误及规则级确认。
- `backend.py::SearchBackend.trial / replay / verified_memory`：真实 wire / Skill、原生证据、历史记忆及 Compiler 精确重放。
- `controller.py::DesignerServiceController.designer_update / run`：双臂验收、跨代 D/S 选择与原 Service Evolver。
- `replay.py::verify_selections`：从录制调用重建 Designer Reflection / Gate 和原 Service Evolver，而非只检查文件 Hash。

输出保存 manifest、全部 attempted/completed 模型调用、角色成本、不可变 Library、来源、提案、diff、Reference 前后预期、Compiler 搜索节点与证明步数、执行前冻结记录、原生工具/Oracle/Replay、发现账本、候选验收及逐代选中版本。构造失败也保存；执行/证据完整性错误中止运行，不伪装成构造失败。总预算耗尽保留实际进度，不无限重试。

本次没有调用收费模型运行新协议。离线测试中的模型回复和用量是明确的测试 fixture，业务状态转换与 Oracle 是真实代码。代码闭环、测试验证、真实模型有效性和 Held-out 泛化是四件不同的事；后两者尚未验证。

## 实现验收记录（2026-10-16）

- `tests/test_designer_service.py` 与 `tests/test_vast_boundary.py`：29 项通过。覆盖真实业务转换与证明、非法场景拒绝、身份/信息隔离、多轮顾客、未触发/正确处理/实际违规、重复与规则根因、双边跨代继承、动态回滚、独立评价、预算和精确 Replay；模型回复及 Token 数为测试 fixture。
- 完整回归 `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q -x`：**1006 项通过，344.65 秒**。此轮执行期间没有修改 Python 源码或生成包内构建文件。
- 示例 plan 完成模型校验，CLI `--help` 可离线运行。
- Core wheel 成功构建，确认包含全部 5 个 Designer Core 模块；直接从 wheel 在隔离 Python 进程导入 Designer 与 Library 成功，未加载 Usami 或 integration 包。本地旧构建工具缺少 wheel，改用项目声明的隔离构建依赖后通过。
- 已检查 diff：四领域业务包、旧 Controller/Evolver/Gate/Reflector 和历史实验结果没有修改；共享层只增加角色、Skill 类型及显式固定 Customer 协议分派。
- 初次全量检查发现 Designer Reflector 错误依赖业务包，已改为 Core 内的严格响应解析；最终回归在源码清单稳定后执行。打包临时文件曾干扰一轮源码 pin 检查，该轮中止，不作为通过证据。

掌控摘要：**已实现** CloudOps Designer–Compiler–固定 Customer–Service 的训练/反馈/选择/重放闭环；**已测试** 的是协议与真实业务执行机制；**未验证** 的是实际 LLM 的发现能力提升、Service 修复收益与跨世界泛化。自动根因确认仅限上述规则边界约定，其他复杂错误保持候选状态。
