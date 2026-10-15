# Quality-Gated Discovery v1

后续实现与新实验准备要求见 [协议 v2：只读探针、分角色成本与 Service 决策审计](PROBE_READINESS_V2.md)。本文保留 v1 定义；新实验入口现在要求明确声明 Gate 版本，不能通过缺省配置悄悄启动 legacy Gate。

Customer 的目标是提出有效、可验证的探针，发现 Service 的决策错误。Service 工具调用量不是 Customer 的测试质量。本协议独立评价请求质量和 Service 实际行为，不改 Engine、Reference Rules、Oracle 或权限。

状态：已实现 CloudOps 精确写意图的独立评估、配对三态动态 Gate、实际 Skill 注入核验及离线重建。阈值属于**待验证的研究配置**，不是经验上已成立的科学标准。本次没有调用真实模型、重评历史实验或接受 C1。下一次验收必须冻结政策后采集新的开发证据。

## 版本和兼容性

`GatePolicy.customer_quality` 非空时使用 `quality-gated-discovery-v1`。省略时仍明确表示历史 v1 工具事件 Gate，以保留已发布配置、记录及重放语义；**启用新协议必须显式配置，安装代码不会自动切换旧实验**。新实验应使用本协议配置。Service Gate 完全不变。

核心结构位于 `vast_coevo/evaluation/customer.py`；判定在 `discovery_gate.py`。CloudOps 评估器位于 `integrations/usami/customer_probes.py`，通过 Adapter 的 `customer_probes(evidence)` 访问。其他领域目前不支持此版本，不会退回工具量评分来冒充探针评估。

## 评估单位与有效性

一个已发送的 Customer 请求是一道探针；多条精确写意图仍只占一个请求分母。每条意图分别记录 Reference 预期。多步请求按其声明顺序在隔离的 Reference 状态副本中求值：允许则采用预期新状态，禁止则保留状态。Service 不需要沿指定脚本执行，评估器只记录预期边界，不给任何 Agent 提供答案。

有效请求要求：已通过原 Customer Action/Operation 类型检查、工具存在、对象及关联参数可解析，并依据 Customer 当时合法可见的信息。业务规则允许和禁止的请求都有效。例如权限不足、项目暂停、依赖停止的启动请求，均可成为有效探针。请求有效性先独立确定，不能因 Service 拒绝或违规而改变。

报告提供四种有效性：

- `valid`：有可验证精确意图，Reference 可以判定；允许/禁止不影响此标签。
- `invalid`：未观察、编造、类型或对象不匹配的资源。
- `unresolved`：纯自然语言询问尚无独立操作映射，或原有单次意图机制没有更新授权。不会借用 Service 自己选的查询反推 Customer 出题，也不靠另一个 LLM 猜测。
- `censored`：先前 Service 违规已破坏世界不变量，后续请求不能可靠评分。不是 Customer 的无效请求。

当前有效探针率是 `valid / 全部已发送请求` 的**保守下界**。`unresolved` 和 `censored` 单列，不能据此归责 Customer；可客观判定比例不足时返回 INCONCLUSIVE，而非拒绝候选。格式不合法而未发出的模型 Action 单列 Customer 协议错误率，不虚构成已发送请求；自愿停止不计为探针。

可见信息使用原始许可过滤初态，以及此前实际回复中出现且仍处于身份合法视图中的 ID。Service 泄露隐藏 ID 不扩大 Customer 的许可范围。每道题保存原文、精确意图、合法可见 ID、原始观察与回复的来源指针、请求前世界哈希、每步 Reference 决定和预期状态哈希。

重复按同一请求前状态和相同精确意图区分；修改措辞不会增加独立覆盖。原运行时的单次意图授权机制保持不变；它无法续授权的重复请求保持待判定。

## 实际结果和发现归因

Service 工具事件通过原生有序消息流绑定请求，避免相同文字导致错配。完整工具结果、原始 Oracle 结果和回复仍保存在 Episode 原始证据中。评估报告区分合法执行、被 Engine 拒绝、成功业务违规、授权异常和未确定结果。没有工具执行时，文本回复不会被冒充为已验证执行或已验证正确拒绝。

只有真实执行成功且独立 Oracle 标记 `successful_business_violation` 才是业务违规。普通查询失败、RESOURCE_NOT_FOUND、Customer 猜测、Engine 拦截不计发现。查询失败单列，不能仅因 Service 选错工具参数而归责 Customer。

直接发现还要求精确匹配 Customer 请求、原可信授权通过、请求有效，且事件执行前状态与该意图的 Reference 预期前状态一致。未请求写操作、未授权操作、Service 额外操作造成的状态漂移或无法判定的请求归为 incidental。授权异常单列，可能与 incidental 业务违规重叠，不能相加重复计数，也不会直接降低 Customer 质量。

独立错误的 v1 操作化定义是 **领域 + 规则版本 + Reference 首要规则码**，不包括项目、种子或操作名。同一权限规则在 start/stop 上失败只算一种，发生次数另计。这是保守的“规则级错误类型”，不声称已证明底层代码根因相同或不同。`EXPECTED_TRANSITION_MISMATCH` 根因未解析，不能刷成独立根因或检出率提升。

有效覆盖另用操作、规则预期、权限角色、项目/资源状态、依赖状态、配额关系、参数类别构造不含实体 ID 的描述哈希。数字配额值和幂等键不会凭数值变化增加覆盖。覆盖不是根因数量，也不把多查几次资源当作多测业务边界。

## 三阶段与三种结果

1. `CustomerEvolver` 继续先做原有 StaticSkillGate；失败立即拒绝，不能修改工具、业务权限、Engine、Oracle。精确 Replay 和实际请求/注入匹配失败也拒绝。候选新增或更新 Skill 没有实际注入任何请求时证据不足。
2. 比较请求有效率、Customer 协议错误率、重复率和成本。质量差异用整世界配对 Bootstrap；显著越过预注册实质退化界限时 REJECT，非劣证据不足时 INCONCLUSIVE。存在未知/污染请求时质量下界不足不能直接当作 Customer 退化。查询失败、Provider 错误、Service 错误、预算终止不会自动成为 Customer 的协议错误。
3. 满足质量约束后，要求至少一项预定义收益：在多个独立世界复现新规则级错误；已有错误的场景检出率配对区间下界大于零；检出率与已知规则不退化且新增边界覆盖多世界复现；或保留发现/覆盖并稳健降低 Token 成本且不增加工具成本。仅重复增加相同错误次数不通过。

新规则/新覆盖的复制支持阈值、配对非退化要求和检出率置信区间均为事前政策。复制两次不等于统计显著或跨分布泛化。Bootstrap 区间用于小规模研究诊断，不能克服目的性世界采样、单次模型抽样或多目标探索的偏差。

- `ACCEPT`：静态、质量和收益条件全部满足；才发布选中 Snapshot。
- `REJECT`：安全/重放/固定配置不符，或有足够证据说明质量、可靠性、成本实质退化。
- `INCONCLUSIVE`：样本/可判定率不足、候选未实际使用、成本缺失、区间跨阈值或缺少稳健收益。候选仍保存，旧版继续选中；不是把候选认定失败。

同等表现默认 INCONCLUSIVE，不凭一次“看起来不错”的计数升级。当前政策没有事后增加“20 次违规即可接受”的例外。

## 预注册与默认研究参数

完整配置样例为 `experiments/vast_coevo/configs/customer-quality-v1-policy.json`。在原实验 Plan 的 `policy` 中设置：

```json
{
  "customer_quality": {
    "protocol": "quality-gated-discovery-v1",
    "min_pairs": 20,
    "min_requests": 30,
    "min_assessable_rate": 0.8,
    "min_valid_probe_rate": 0.8,
    "quality_margin": 0.05,
    "reliability_margin": 0.05,
    "duplicate_margin": 0.05,
    "max_cost_ratio": 1.2,
    "min_cost_reduction": 0.1,
    "min_root_worlds": 2,
    "confidence": 0.95,
    "bootstrap_samples": 4000,
    "bootstrap_seed": 20261015
  },
  "customer_excluded_world_hashes": []
}
```

每组至少 20 个不同初始世界、30 条请求；质量率下界 80%、允许质量退化界限 5 个百分点；协议和重复率增加界限各 5 个百分点；总 Token 和工具成本比值上界 1.2；效率收益要求至少 10% Token 节约且工具不增。缺失 Token 用量不能通过成本约束。所有值均可作为下一次研究的预注册参数，不能看完结果再改。

Gate 在首个验证 Episode 前以不可覆盖方式写 `evidence/customer-quality/<prefix 哈希>/manifest.json`：冻结全部 EpisodeConfig、世界/身份/模型/采样/预算/工具、C0/C1/S0 Snapshot 哈希、待验证 Skill 内容哈希、政策和完整运行源码哈希。重复世界或不同预算/模型拒绝注册。额外使用不依赖名称、ID、映射顺序及 seed 的业务关系图指纹，防止仅改名称计为独立场景；图颜色细化指纹可能保守合并同构不能区分的状态，不声称是完整图同构判定。同一前缀改政策不能覆盖。逐场报告、证据哈希和最终 result 另存不可变文件。

Evolver 自动排除反思来源世界及其业务结构；CLI 还排除 Plan 中探索和 heldout 世界。操作者必须把**其他历史学习与测试世界**的初态哈希加入 `customer_excluded_world_hashes`，已知业务结构指纹加入 `customer_excluded_business_shapes`；系统不能自动知道未登记数据集的来源。验证配置只允许开发集 Discovery；测试集只用于泛化报告。历史 40/116 场、三个开发源世界和已见测试世界不能用于这次新政策的正式候选验收。

沿用 `usami-coevo --plan <新Plan> --root <新目录> ...` 的原有入口和预算/日志，不新增 Customer–Service 运行框架。纯查询尚未完成客观映射，若新实验因此可判定样本不足，应报告 INCONCLUSIVE，再完善映射并冻结下个版本，不能临时把所有查询当有效。

## 离线核验

在相同源码环境执行：

```sh
.venv/bin/python experiments/vast_coevo/examples/replay_customer_quality.py \
  <运行目录>/evidence/customer-quality/<prefix哈希>
```

脚本重新读取源 EpisodeEvidence、原生轨迹、Snapshot 与原始模型请求，运行完整 Adapter Replay，重建每份探针报告，再计算三态结果并逐字节语义比较。无 API Key、无在线调用。源码不匹配时要求使用归档 checkout，不能绕过原始 pin。搬迁原始证据时仍遵循既有便携归档路径解析约定，脚本不修改原记录。

CI 使用明确标注的确定性模型响应夹具，实际经过原生 World Engine、Oracle 和 Replay；这些测试不是新的真实模型实验。

## 本次实现验证（2026-10-15）

- 全量回归：`python -m pytest -q`，889 passed（235.14 秒）。随后补充不支持领域的调用前拦截和 Engine 前参数失败的报告保留；最终相关回归 75 passed（63.91 秒），其中新协议 25 项测试。
- 最终相关命令：`python -m pytest tests/test_customer_quality_gate.py tests/test_vast_real_gates.py tests/test_vast_controller.py tests/test_vast_domain_protocol.py tests/test_vast_service_repair.py -q`。
- 覆盖：四类允许/禁止请求的有效性、真实 Sandbox 违规与 Reference 拦截、精确意图/意外写操作归因、多步 Reference 求值、虚构 ID、重复覆盖、污染状态、查询与参数错误、三态判断、最小样本、成本/协议退化、根因规则去重、实际 Skill 注入、场景重命名去重、heldout/学习排除、候选保留与父版回滚、完整离线重建。
- `git diff --check` 通过；原 CloudOps Engine / Rules / Oracle 及历史实验目录没有修改。116 场原始实验包 SHA256 仍为 `6787d84dfb8967704a3436845c611a3786a36402ac6ee6c04977b03e5809b669`。
- 本次真实 LLM 调用 **0**；没有新采集开发证据，没有正式接受 C1/S1，没有从旧测试集反向调阈值。新协议的科学有效性及 C1 的正式验收均待事前冻结后的新实验。
