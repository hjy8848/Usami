# Customer Examiner v1

Customer 不再只是在预设世界中提问的顾客。显式启用 `usami-examiner-v1` 后，它是出题考官：读取完整模板世界及经过 Replay 的开发轨迹，一次提交新的业务世界、执行身份、请求、精确授权和可判定目标。Service 通过原来的业务工具执行，不接收考官的全量配置、分析或证明路径。

## 数据流

初始 Service Task → 原始执行与 Oracle → Customer 构造场景 → 原生不变量 / 任务证明校验 → 冻结实例 → Service 执行 → Oracle / Replay → 双方 Reflection 与原版本选择 → 下一代。

四个领域均接通：SaaS、CloudOps、FulfillmentOps、StayOps。没有改动 World Engine、Reference Rules、Oracle 或它们的业务权限。

## 考官能改什么

- 全局查看模板世界，在原生模型内新增、删除和配置实体，选择执行身份。
- 组合实体关系、业务状态、精确写操作能力与目标。
- 根据成功和失败的真实 Service 轨迹设计下一题。
- 不能改 seed、clock、领域 / 版本、SaaS rules、生成器来源等非实体字段。
- 不能改写旧模型回复、事件或 Oracle。构造阶段的权限不是执行阶段的业务权限。

构造接口为一次 Function Calling：`submit_exam`。工具 Schema 内嵌当前领域的 World、Operation 和逐操作参数模型，不让模型猜字段。最多一次 Customer 调用，不自动修补或重试；最多 512 个实体、64 个能力与 64 步证明，证明还受工具预算限制。

提交 `world / identity / message / kind / capabilities / goal / witness / refusal_operation / rationale`：

- `completion`：要求非空目标、允许变化的范围及一条合法 witness。通过原生 Reference Engine 真正执行 witness，由原有 Oracle 与 Replay 核验；初态已满足目标、证明不达标或超出授权都会拒绝。Service 得到目标和可用的精确授权，**看不到 witness**，可以选择另一条合法路径。
- `policy_refusal`：只有一项精确操作，Reference 必须确认存在业务拒绝条件。不存在对象或无效世界不当成有价值的拒绝题。拒绝码由程序计算，不接受模型自报答案。

全量模板只进入 Customer 请求。Service 仅收到自然语言题面、明确目标 / 允许变化范围、执行身份及精确写能力；通过原查询工具获取其身份可见的事实。考官的 rationale、证明路径、旧轨迹与 Oracle 证书不进入 Service 请求。

## 复用原有进化入口

在标准实验 plan 的探索 profile 中增加：

```json
{
  "config_id": "author-cloudops",
  "domain": "cloudops",
  "seed": 731,
  "identity": "u0",
  "mode": "sandbox",
  "split": "dev",
  "examiner_protocol": "usami-examiner-v1"
}
```

其余 plan、Library、基础模型和预算沿用现有 `integrations.usami` CLI。探索预算至少预留一次 Customer 调用。已有 profile 不增加这个字段，仍是原先的局部观察与自主请求协议。

```bash
.venv/bin/python -m integrations.usami --root artifacts/examiner-training \
  --plan experiments/vast_coevo/examples/examiner-plan.json run --id examiner-training-001
```

随附 plan 和两份初始 Library 可直接使用。`customer_selection: customer-static-only-v1` 控制 Customer 版本选择；为兼容现有 CLI 保留的 `customer_gate_version: legacy-v1` 只命名诊断配置，不恢复性能验收。训练命令会调用模型及 Reflection，按 plan 预算计费；小闭环命令不运行 Reflection。

要求：

1. 使用递归 v3 Controller。每个考官领域至少有一项已配置的开发 Service Task，作为初始执行材料；没有时在调用模型前报错。
2. 第 0 代先在原 Service 上执行这些任务，计入原 Journal 预算；考官与双方 Reflection 均可消费这些证据。
3. 后续代从上一代 `current_evidence` 加载经 Replay 的同领域执行，最多保留最近 8 项。模型输入只投影实际 Service 世界、请求 / 回复、工具与 Oracle，不递归复制旧考官的请求历史或私有 reasoning 字段。
4. 生成失败会保存原始请求、回复、原因与实际成本，以 `construction_error` 终止该 Episode；不会调用 Service，也不会伪装成测试有效性下降或发布新版本。
5. Customer 仍是 Static-Only Selection。Service Reflection、静态 / 动态 Gate 和回滚逻辑保留。
6. **Service 动态 Gate 的验证 profile 必须是固定世界，不能启用考官。** 已知错误回归直接加载原考官冻结的实例、身份与请求，不再调用 Customer 出另一道题。
7. seed 任务仍可能在原 Service Reflector 的固定 preflight 中执行一次，这是原验收机制；两处调用都记录预算，不把它们算成同一场。

构造不在 Held-out 中运行。Held-out 世界与任务须在评价前单独冻结，不能把最终考试轨迹送回考官或 Reflector。

## 一次真实小闭环（不运行 Reflection）

使用原有环境配置和钥匙串机制；不把 Key 写进计划或结果。可用 `VAST_CUSTOMER_*` 与 `VAST_SERVICE_*` 分别配置模型，未设置时沿用 `USAMI_LLM_*`。

```bash
export USAMI_LLM_MODEL='<OpenAI-compatible model>'
export USAMI_LLM_BASE_URL='<API base ending in /v1>'
export USAMI_LLM_OPTIONS='{"temperature":0,"max_tokens":8192}'
export USAMI_LLM_KEYCHAIN_SERVICE=litellm
export USAMI_LLM_KEYCHAIN_ACCOUNT=litellm-api-key

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python experiments/vast_coevo/examples/examiner.py run \
  --domain cloudops --seed 731 --output artifacts/examiner-smoke-001

# 不读取凭据、不调用模型：
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python experiments/vast_coevo/examples/examiner.py replay \
  --output artifacts/examiner-smoke-001
```

默认每次只跑两场：一场原生初始 Service Task，一场模型自主构造的挑战。总上限 17 次 LLM 调用（Customer 1、Service 16）、32 次工具调用，Reflection 0。输出目录必须不存在；不覆盖旧证据，不重试失败。`--domain` 支持四领域，`--seed-task` 可指定已有原生任务族作为 T0，后续挑战仍由模型决定。

## 证据与版本边界

- Profile 中的 `examiner_protocol` 和 Native ExamConfig 明确标记新协议。
- `EpisodeConfig.initial_world_hash / identity` 绑定**构造前的模板**；`EpisodeEvidence.execution_initial_world_hash / execution_identity` 另行绑定实际执行的冻结世界和身份，不把模板冒充最终考场。
- Native ExamTrace 保存完整考官请求 / 原始输出、提案、校验证书、冻结世界与 Service Execution。失败也保存原始提交。
- 原 RuntimeClient 保存实际 Skill 注入、原始 wire 请求 / 回复、预算与快照哈希。Token 来自 provider usage，缺失不记为 0。
- Replay 重建原始构造请求、Skill 注入、校验与 Service 工具过程，重新计算证书、状态与评分，不联系 LLM。历史证据逐项核对来源和开发分区。
- 新增字段缺省不序列化，旧配置与已有内容 Hash 不迁移；旧原生 Replay 仍使用各自的 source snapshot，不能用新源码冒充原版本。
- SaaS 通过独立适配层装载已认证的冻结世界，复用原 GoalServiceSession 的执行与精确能力语义，不修改历史 Service 协议，也不要求执行 witness 中的某条标准路径。

浏览器工作台是这一协议的交互说明；后端实际调用、证据与 Replay 通过上述 Python 入口完成。
