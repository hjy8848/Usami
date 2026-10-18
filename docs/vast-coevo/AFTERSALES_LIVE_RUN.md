# After-sales 真实模型共同进化小闭环

`aftersales_coevo_smoke.py` 是离线、脚本化的工程回归；它验证接口、业务执行、证据和 Replay 能连通。它不能证明 Agent 会自主出题或从交互中学习。

v2 允许明确登记的 Designer 提案修正，不自动重试传输失败。DashScope Qwen 的强制提交与思考模式不兼容：Designer 可显式设置 `enable_thinking=true` 保留探索思考，协议在正式提交请求中改为 `false`，每次实际选项均记录在请求中。若省略该选项，网关的默认思考模式可能导致 400。Service Reflector 也使用强制工具调用，应配置为 `false`。限制见 [Qwen 官方 Function Calling 文档](https://docs.modelstudio.console.alibabacloud.com/en/model-studio/qwen-function-calling)。例如：

```sh
export USAMI_DESIGNER_OPTIONS='{"max_tokens":8192,"temperature":0,"enable_thinking":true}'
export USAMI_REFLECTOR_OPTIONS='{"max_tokens":4096,"temperature":0,"enable_thinking":false}'
```

`aftersales_coevo_live.py` 是独立的真实模型运行入口。没有固定题目、预设 Customer 对话、Service 工具序列或模型生成的 SkillPatch。Designer 阅读冻结世界并自行提交任务；只有原生编译器证明任务后，Customer 和 Service 才会在独立世界副本中真实交互。完成两项挑战后，Designer 与 Service 分别基于已 Replay 的证据进行至多一次反思；通过静态安全门的 Patch 才会成为后续所用快照。模型也可以给出无效提案、NOOP 或被 Gate 拒绝，这些结果都会保留，不会脚本补答案或自动重试。

## 运行

先配置 OpenAI-compatible 端点。API Key 可以使用环境变量，也可以沿用现有 Keychain 读取机制；不要把密钥写入命令历史或结果目录。

```sh
export USAMI_LLM_MODEL='provider/model-name'
export USAMI_LLM_BASE_URL='https://your-openai-compatible-endpoint/v1'
export USAMI_LLM_KEYCHAIN_SERVICE='your-keychain-service'
export USAMI_LLM_KEYCHAIN_ACCOUNT='your-keychain-account'

PYTHONPATH=. .venv/bin/python -m experiments.vast_coevo.examples.aftersales_coevo_live \
  --output experiments/vast_coevo/results/aftersales-coevo-live-001 \
  --seed 1 --max-model-calls 65 --customer-turns 4
```

可以为角色分别设置 `USAMI_DESIGNER_MODEL`、`USAMI_CUSTOMER_MODEL`、`USAMI_SERVICE_MODEL`、`USAMI_REFLECTOR_MODEL`，以及对应的 `USAMI_<ROLE>_BASE_URL` 和 `USAMI_<ROLE>_OPTIONS`。未单独指定时使用 `USAMI_LLM_*` 通用配置。默认请求选项为 `max_tokens=2048, temperature=0`。每次实际请求都会在发送前登记；全局模型调用预算耗尽后不会再发请求。

一次运行最多包含三条 Service 执行任务、三次 Designer 出题会话和两次 Reflection，默认全局上限 65 次模型调用。每条 Service 任务最多 4 次 Customer 模型调用、8 次 Service 模型调用和 12 次业务工具调用。任务构造有节点与深度预算。所有模型输出、失败、业务轨迹、Oracle、静态 Gate 结果、快照和 Replay 写入新的运行目录；已有目录不会覆盖。

Designer 的请求还明确说明原生组合契约：完成目标必须指向冻结世界中已经存在的对象；v2 的修改范围和 `selector_field` 等字段由编译器依据原生契约生成；信息要求只能使用顾客实际拥有的事实；确认要求必须是精确操作。`native_field_enums` 自动提取原生 Pydantic 模型的字段枚举，避免模型猜测并不存在的状态值。这些是静态业务字段词表，不指定具体顾客、订单、题目或答案，也不会代替编译器判断提案是否合法。

## Designer 探索协议 v2

本入口默认使用 `frozen-world-designer-exploration-v2`，运行协议为 `aftersales-real-model-coevolution-v2`。初始请求只含冻结登记、身份和集合数量，不包含完整世界。Designer 通过 `inspect_frozen_world` 分页列出顾客画像、读取某个画像和相关对象、读取具体集合或业务规则，自主决定调查对象。查询不执行业务写入、不调用 Reference，也不返回执行见证。

每次出题会话最多 5 次探索模型调用、20 次只读查询、1 次初次提交加 3 次修改。真实入口在首次提交前最多使用 4 次探索，为纠错保留剩余预算。模型调用 `ready_to_submit` 后，或达到阶段预算时，切换到正式提交阶段；该阶段强制 `submit_frozen_world_task`。失败会返回真实编译错误、剩余预算及重复提案提示；若还有探索预算，Designer 可以补充查询再提交。传输失败不自动重试。全部请求、工具返回、回复、编译反馈和失败保存在 `designer/task-N-journal.json` 与 `model-calls/`。

画像查询除原生可修改对象外，还返回有界的关联只读记录，包括订单日期、产品条款和证据。引用遍历限制为两条边、最多 24 个关联记录；初始目录包含世界时间。它不计算可执行性，不标记哪一题正确，不扩大最终任务的顾客权限。

高层提案只提交顾客画像、自然语言挑战、目标、拒绝操作和可选交互要求。编译器先确认全部画像属于同一身份，再合并各自的原生 frame；不修复、替换或代选目标。Reference 搜索、Engine、Oracle 和证书仍使用原来的代码。搜索预算内未找到路径只报告 `search_unproven`，不声称任务不可能。

对话领域的 `designer_view()` 和 `design_and_compile()` 现在默认采用 v2；工具领域保留原协议。历史 v1 的请求形状和提示保持兼容，旧离线夹具显式选择 v1，可以用 CLI `--designer-protocol frozen-world-task-designer-v1` 启用旧入口。`verify_designer_execution` 按记录中的协议分派：v2 会重新执行确定性的查询、反馈与任务编译，比对整个对话，而不只是验证哈希。失败的 v2 日志使用 `verify_failed_journal(frozen, journal)` 离线重放。为历史 v2 记录保留的配置缺省值不会隐式改变旧请求。

Manifest 的 `designer_diagnostics` 分别记录提交合法率、目标结构签名数量、Reference 证明路径业务步数、真实执行数、自然结束比例、最终目标达成和严格成功数。证明路径长度不是最短路径难度，少量题目也不足以证明探索多样性。这些统计不参与 Skill 版本选择。

第二轮的“创建新对象”目标谓词未实现；v2 当前仍使用现存对象目标与独立的正确拒绝目标。这是有意保留的边界。

## 如何解释结果

- `EXECUTED` 表示三条计划内 Service 任务确实运行，证书与离线 Replay 完成。它不代表一定产生 Skill 更新。
- `designer_skill_updated` 与 `service_skill_updated` 直接报告是否有 Patch 通过静态 Gate 并被选中。NOOP、无效输出或拒绝会保留父快照。
- `verification/task-3-skill-consumption.json` 记录第三项挑战实际注入的 Designer / Service Skill 内容和命中情况。若模型提出的新 Service Skill 未被 Retriever 选中，会明确记为未消费。
- 每条任务都独立记录目标达成、过程错误、严格任务评分和 Oracle 结果。Service 的业务决策是否正确不由 Designer 自己判定。
- 本入口只关闭这次三任务集成验证中的动态性能 Gate。静态接受不能解释成能力提升；一个小闭环也不能支持跨场景泛化或自我改进有效性的研究结论。

运行前可分别设置角色模型；实际端点、模型与采样选项会写入 Manifest。认证信息不会写入结果。模型请求和回复包含合成业务世界与对话内容，运行前应确认配置的端点适合接收这些数据。
