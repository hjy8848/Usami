# VAST-CoEvo 递归训练 v3 实现与验收

**C2C：EXECUTED。** 修改与离线验证完成，953 项全量测试通过；没有新在线训练或正式 Held-out。

## 1. 修改前的真实顺序

Cn×Sn 正常探索 → Oracle/current → Customer Reflection/Static → 选中 Cn+1 → Cn+1×Sn 再探索/selected → Service Reflection（current+selected+合法/拒绝任务）→ Service Static/Dynamic Gate → 四组 cross → 保存 Snapshot/代际。
parent_parent / selected_parent / parent_selected / selected_selected 是训练主循环的末尾执行，不属于 Service Gate。发现的错误发生在 Reflection 之后，未进入该代反思。

## 2. 修改后的真实顺序

Cn×Sn 自主挑战 → 原 Engine/Oracle/完整 En → Customer Reflection/Static 选择 → Service Reflection（同一 En + 原合法/拒绝任务）→ 原 Service Static/Dynamic Gate → 保存实际选中版本 → 下一代使用 Cn+1/Sn+1。
每个 exploration_case 每代只运行 1 次正常自主交互。新 Customer 在下一代实践，不在本代额外出一道比较题。固定 Customer 的 A 组不进行 Customer Reflection，其余训练链和预算规则相同。初始配置提供种子/环境，后续由 Customer 决定挑战；没有逐代人工题目或新 Agent。

## 3. 从默认训练移除了什么

- 更新后 selected_customer 比较探索。
- parent_parent、selected_parent、parent_selected、selected_selected 四组末尾研究比较。
- 没有将这些比较提前到 Reflection，也没有添加跨代错误队列。
原 Service Gate 内部 baseline/candidate 开发验收、真实失败回归、合法完成、正确拒绝、违规和授权检查保留，不能与研究交叉测试混同。

## 4. 学习证据与版本选择

正常 En 的完整 EpisodeEvidence 同时传给双方 Reflection。新测试用实际 CloudOps Sandbox Engine/Oracle 产生真实业务违规，核对 Service 模型请求中的失败/Oracle 事件，以及 ReflectionRecord.input 中相同 evidence_hash，并独立 Replay 通过。模型回复是明确标注的离线 fixture，不是新模型实验。
Customer 仍只按 Static Gate 选择，不恢复 Performance Gate；NOOP/静态拒绝保留旧 Snapshot。Service 原 Evolver、Reflection 和 Gate 未改动；候选仍须动态通过才会被选中。
GenerationRecord v2 保存 current_evidence，selected_customer_evidence/crossings 强制为空；原 EvolutionRecord/Archive/native journal 保留候选与选中版本、Oracle、Reflection/Gate、原始请求/返回/实际调用成本。下一代按实际选中 Snapshot 加载。
Service Gate 使用当前已选中的 Customer 验收候选，Reflection 来源仍是此前 Cn×Sn 的 En；合法/拒绝 preflight 为原有 Service-only 学习补充。没有额外 Customer 比较探索。

## 5. 训练后如何独立交叉评估

新增 evaluate-cross 入口只读已有 Snapshot hash，可通过 history 获取任意代 parent/selected hash，再指定 C0×S0、C3×S0、C0×S3、C3×S3 等组合。
评估使用独立 profile/world、同一基础模型、独立预算、Manifest/日志/Archive；CLI 要求训练已完成且初态 hash 不重叠，开发诊断与 frozen-heldout 分区必须匹配。世界业务结构独立性仍须通过原世界生成/构造流程保证，不能用改名声称多样性。
评估函数没有 Reflector、Evolver 或可写 LibraryStore 参数，不发布 Skill/修改选中版本；失败保存实际成本或未知预留，不自动重试。测试比较训练目录全部文件内容，证实评估前后 Snapshot/报告/Archive 均不变；另用真实原生 Session 验证 CLI 独立入口。
任意 C/S 的自主交互评估属于 Discovery Track；Service 固定任务 Held-out 主正确率仍沿用 multigen_heldout.py 原 finish_evaluation/scored/analyze，不以发现数替换正确率。

## 6. 预算与兼容性

每世界/每代/每臂去除 5 次 Episode 机会。旧已完成实验对应 20 场额外步骤共 148 次调用、940,975 Token（输入 870,014，输出 70,961），140 次工具调用。该数仅为历史组成成本，不是新协议实测节省。
新协议没有在线运行；实际成本和效果尚未知。A/B 使用相同的新循环和原上限，不将节省预算转为某组额外代数、挑战或单场预算。
RunConfig v3 / recursive-training-v1 明确封存新执行语义。旧 v1/v2 配置与 v1 代际记录不新增字段、不改 hash；额外只读校验旧实验 10 份真实记录均通过。Core 的显式 v2 分支仅用于历史语义，默认新运行是 v3；生产 CLI 拒绝静默用新入口续跑旧协议。原精确 Replay 继续使用各自归档源码。
旧实验、Manifest、Held-out 全部未修改；没有用已查看测试结果选 Skill 或训练。

## 7. 是否还有未被消费的训练证据

有效完成的本代正常 En 没有被留到 Reflection 之后：双方均接收同一 En。A 固定 Customer 例外是实验定义，不进行 Customer 学习。
合法/拒绝 preflight 是 Service 学习补充；候选 Gate 产生的验证证据只用于验收，训练后独立交叉结果只用于研究比较，不回流已经结束的训练。它们不是遗漏的正常挑战。预算或错误使 Reflection 未执行时仍保留明确错误和证据，不能声称已学习。

## 修改文件

|文件|原因|
|---|---|
|vast_coevo/evolution/controller.py|v3 单次探索共享 En、跳过 selected/cross、验证代际协议|
|vast_coevo/evolution/models.py|RunConfig v3 与显式 training_protocol，旧序列化稳定|
|vast_coevo/storage/runs.py|GenerationRecord v2 禁止混入比较证据|
|vast_coevo/evaluation/cross.py|训练后独立只读评估、证据/成本/预算/失败记录|
|integrations/usami/cli.py|v3 注册与 evaluate-cross、历史/分区/世界/模型保护|
|experiments/vast_coevo/examples/multigen_heldout.py|新 Manifest 选择 v3；原主 Held-out 评分保留|
|experiments/vast_coevo/configs/ 的四份现行计划|显式声明 recursive-training-v1|
|tests/test_recursive_training.py|7 项新协议、原生 Oracle、跨代继承与独立评估检查|
|现有 controller/static-selection/resilience 测试|新默认断言及明确历史 v2 fixture|
|README 与 docs/vast-coevo/RECURSIVE_TRAINING.md 等|顺序图、证据流、CLI、预算和兼容性说明|

## 验证

- 全量：953 passed in 253.86s。
- 新协议：7 passed。CLI/配置相关：43 passed。
- Git Diff 未修改 Service Evolver/Gate、Reflection、Skill Schema/静态安全或任一业务 Engine/Rules/Oracle。
- 初期全量开发日志保留：当时有计划字段尚未声明的问题，以及修改源码期间触发的 source-pin 拒绝；修复并冻结源码后重新运行，全量通过。
- 未启动在线进化或正式 Held-out，没有新的性能/泛化收益结论。

详细执行图与命令见 docs/vast-coevo/RECURSIVE_TRAINING.md；历史组成成本与 hash 校验见本目录 JSON。
