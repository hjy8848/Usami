# Customer / Service 实验准备协议 v2

> 当前选择机制已更新为 [Customer Static-Only Selection](CUSTOMER_STATIC_ONLY.md)。下文中的 Customer 性能 Gate 是历史机制或显式诊断，不能决定当前 Customer 版本。Service 动态验收保持原样；历史结果不改判。


本轮只补评价、归因和启动检查；不调用在线模型，不生成新 Skill，不正式接受 C1/S1。新的评价语义不能用于事后追认旧实验。Engine、Reference Rules、Oracle 和 Sandbox 执行语义均不修改。

## 1. 独立只读意图

CloudOps Profile 新字段：

```json
{"read_probe_protocol": "cloudops-read-probes-v1"}
```

新 Customer Action 显式包含 `read_probes`，与写意图 `requested_operations` 分离，例如：

```json
{
  "type": "send_message",
  "message": "请查询这个项目的状态和权限。",
  "read_probes": [
    {"name": "get_project", "project_id": "p0", "resource_id": "p0", "purpose": "state"},
    {"name": "get_project_members", "project_id": "p0", "resource_id": "p0", "purpose": "permissions"}
  ],
  "requested_operations": []
}
```

支持六种原有读接口：get_customer_context、get_project、get_project_members、list_instances、get_instance、get_invoice。目的分别为 catalog / state / permissions / quota / dependencies / billing，并由运行时和公开 JSON Schema 同时限制名称、目的及对象参数的组合。不能用 read_probes 声明任何写操作。纯读、纯写、混合请求都支持；每个请求仍只占一道题。新协议不再接受没有任何结构化意图的 send_message。stop 的两个列表均须为空。

评估器先读取 Customer 独立声明，再用其合法可见 ID、对象类型、固定工具集合和独立规则判定查询。初态项目中已经出现的 invoice_id 可用于测试“已知账单 ID，但无读取权限”的拒绝边界；这不增加写授权。读对象存在但权限不允许，同样可构成有效探针。猜测隐藏对象、类型错误、未配置读工具不能算有效。

Service 仍自主选择要调用的工具与顺序。实际读调用与原声明分别记录，不能从 Service 选了哪种工具反推 Customer 原意。即使 Service 不查询而直接回复，Customer 原请求也可以有效，但回复事实正确性保持未验证，不冒充已证明正确或错误。

信息价值单列：`tests_known_fact` 表示测试初始可见事实；`potential_new_fact` 只表示可能获得新信息；`denial_boundary` 表示读取权限边界。相同对象、目的、Reference 结果及预期事实的重复查询不增加覆盖，改写措辞和无关世界变化不能刷分。返回给 Service 的工具数据不自动视为 Customer 已学到的事实。当前不自动判断自由文本回复是否准确转述；这仍是报告中的明确未知项。

旧 Profile 缺省此字段时，仍使用旧 Action、旧 Prompt 和旧授权过程。新类位于 `integrations/usami/customer_protocol_v2.py`，复用原交互循环；原 CloudOps 包不修改，原冻结任务来源 Hash 不变。旧世界、旧轨迹和旧库不迁移；历史完整算法 Replay 仍使用归档源码。

## 2. 新实验必须声明 Gate

新 `integrations.usami run` 在读取凭据、构造模型客户端或调用模型之前，要求 Plan 明确设置：

```json
{
  "customer_gate_version": "quality-gated-discovery-v2",
  "policy": {"customer_quality": {"protocol": "quality-gated-discovery-v2"}}
}
```

完整研究参数见 `experiments/vast_coevo/configs/customer-quality-v2-policy.json`。exploration / validation 中的 CloudOps Profile 都必须配置新只读协议。声明 QGD 却没有相符配置、声明 legacy 却带 QGD、或配置与续跑的冻结版本冲突，都直接报错。

历史 v1 QGD 和 `legacy-v1` 仍可显式选择。没有新字段的旧 Plan 仍可读取用于离线 Replay；已经登记的旧运行可按原冻结配置恢复。**新建运行不能依靠省略字段默默选中旧 Gate。** 已归档的独立实验驱动脚本保持不变，不能把用旧脚本运行等同于已启用 v2。

v2 仍沿用质量门槛、配对发现/覆盖收益、三态结果和事前 Manifest，不重用旧测试集选择候选。三十条请求、二十个业务结构、允许五个百分点退化等参数仍为待验证研究参数。

## 3. 污染状态优先

已发送请求的前态违反世界不变量时，主分类固定为 `censored`。未观察 ID、错误类型等请求问题保留为次级原因，不再覆盖成 `invalid`。污染请求不产生有效覆盖或直接发现分；不把由 Service 破坏世界引起的后续无法评分归责 Customer。

模型未能生成合法 Action 时仍属于协议层错误，独立于已发送探针的有效性分类。

## 4. 成本分角色、分时点

v2 ProbeEpisode 保存：

- Customer 和 Service 各自的调用、prompt/completion/total Token、缺失用量字段数；工具调用属于 Service。
- 到首次“有效请求直接触发的真实违规”为止的分角色成本。
- 首次任意成功业务违规之后的分角色成本，观察后续连锁消耗。
- 首次发现的调用 ID、首次任意业务违规的调用 ID及终止原因。

两条时间轴可能有不同锚点，不能强行相加。当一次模型完成输出多个工具时，无法拆分其中每个工具的 Token；整次完成计入含发现的调用，后续同批工具仍有各自工具计数。时序在后不等于因果上由 Customer 或违规导致。

v2 Gate 分别约束 `customer_token_ratio`、`service_token_ratio`、`service_tool_ratio`，不再把合计 Token 下降等同于 Customer 效率提升。仅 Service 变便宜不能取得 Customer 效率收益。成本收益还要求逐对请求暴露不减少，且没有业务违规、污染请求、协议失败或异常预算提前终止。发现收益与成本收益分开，不能通过提前失败刷低成本。

缺失用量不能补零或估算成已知成本。旧 v1 总成本语义保持供归档复现。

## 5. Service 逐写决策审计

新读协议下，每个 CloudOps Episode 自动保存 `service-decision-audit.json`；也可以通过 `adapter.service_decision_audit(evidence)` 对已核验当前证据重建。审计不会改变 Service Prompt、工具结果、状态转移或拒绝策略。

每次写入保存：实际决策调用及请求哈希、实际注入的 Skill 版本/内容、原 Customer 消息、精确写授权、Reference 预期、原 Oracle 结果、执行前状态和所需事实投影。

“模型可见事实”只来自该次决策请求中真实存在的工具消息；每条事实有来源调用和工具。原 Customer/Service 自述不自动成为事实。同一次完成同时发出查询和写操作时，查询结果尚未进入该次模型输入，不能伪装成已经查询并理解。成功写操作自身返回的状态也属于可见事实；可以从先前已知的 usage/资源尺寸和成功启动/停止结果推导更新后的 usage，不要求模型无意义地重复查询。

审计把事实缺失、事实快照与当前状态不符、已观察到阻断事实仍成功违规、无精确授权写入、未注入 Skill 等分别列出。事实投影对部分操作只提供部分前置条件，须读取 `fact_projection_scope`。未出现查询证据不等于模型一定不知道；正确事实在输入中也不能证明其私有推理过程。报告只支持观察层面的决策归因。

原 116 场证据可运行：

```sh
.venv/bin/python experiments/vast_coevo/examples/audit_service_decisions.py \
  --bundle experiments/vast_coevo/results/service-repair-bundle.tar.gz \
  --output outputs/vast-coevo/service-decision-audit-NEW/AUDIT.json
```

先在隔离子进程中导入归档原算法，完整重放 116 场、原 Gate 和原统计；再由新审计器读取哈希绑定的请求、工具和原始 Oracle 结果。输出目录不可覆盖。这个离线诊断不创建新 Episode、不重新判旧 Gate，也不是新泛化实验。

## 6. 领域适用范围

已发布 S1 保持原 Snapshot 和 Hash。它显式提到 CloudOps 的 start_instance，却声明四域，因此审计记录另外三个领域没有语义等价验证。

v2 正式实验入口阻止直接使用这种未隔离的 Service 指导；ServiceEvolver 的 v2 候选发布路径也增加同样的范围检查。检查是保守的显式操作名审查，不声称能自动证明任意自然语言策略的跨领域等价性。

后续应保留通用授权原则，另用 ADD 建立 CloudOps 专属经验；或另开明确范围变更实验。UPDATE 必须继承父 scope 的既有规则保持不变，不能手改历史 S1 的 domains 或 hash，冒充模型已经生成并通过的新经验。没有新候选，因此本轮不声称已修复 Service。
