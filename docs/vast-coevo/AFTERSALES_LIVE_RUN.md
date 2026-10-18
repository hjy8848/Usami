# After-sales 真实模型共同进化小闭环

`aftersales_coevo_smoke.py` 是离线、脚本化的工程回归；它验证接口、业务执行、证据和 Replay 能连通。它不能证明 Agent 会自主出题或从交互中学习。

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
  --seed 1 --max-model-calls 41 --customer-turns 4
```

可以为角色分别设置 `USAMI_DESIGNER_MODEL`、`USAMI_CUSTOMER_MODEL`、`USAMI_SERVICE_MODEL`、`USAMI_REFLECTOR_MODEL`，以及对应的 `USAMI_<ROLE>_BASE_URL` 和 `USAMI_<ROLE>_OPTIONS`。未单独指定时使用 `USAMI_LLM_*` 通用配置。默认请求选项为 `max_tokens=2048, temperature=0`。每次实际请求都会在发送前登记；全局模型调用预算耗尽后不会再发请求。

一次运行最多包含三条 Service 执行任务、三次 Designer 任务提案和两次 Reflection，默认全局上限 41 次模型调用。每条 Service 任务最多 4 次 Customer 模型调用、8 次 Service 模型调用和 12 次业务工具调用。任务构造有节点与深度预算。所有模型输出、失败、业务轨迹、Oracle、静态 Gate 结果、快照和 Replay 写入新的运行目录；已有目录不会覆盖。

Designer 的请求还明确说明原生组合契约：完成目标必须指向冻结世界中已经存在的对象；修改范围须保留原生 `selector_field` 等字段；信息要求只能使用顾客实际拥有的事实；确认要求必须是精确操作。`native_field_enums` 自动提取原生 Pydantic 模型的字段枚举，避免模型猜测并不存在的状态值。这些是静态业务字段词表，不指定具体顾客、订单、题目或答案，也不会代替编译器判断提案是否合法。

## 如何解释结果

- `EXECUTED` 表示三条计划内 Service 任务确实运行，证书与离线 Replay 完成。它不代表一定产生 Skill 更新。
- `designer_skill_updated` 与 `service_skill_updated` 直接报告是否有 Patch 通过静态 Gate 并被选中。NOOP、无效输出或拒绝会保留父快照。
- `verification/task-3-skill-consumption.json` 记录第三项挑战实际注入的 Designer / Service Skill 内容和命中情况。若模型提出的新 Service Skill 未被 Retriever 选中，会明确记为未消费。
- 每条任务都独立记录目标达成、过程错误、严格任务评分和 Oracle 结果。Service 的业务决策是否正确不由 Designer 自己判定。
- 本入口只关闭这次三任务集成验证中的动态性能 Gate。静态接受不能解释成能力提升；一个小闭环也不能支持跨场景泛化或自我改进有效性的研究结论。

运行前可分别设置角色模型；实际端点、模型与采样选项会写入 Manifest。认证信息不会写入结果。模型请求和回复包含合成业务世界与对话内容，运行前应确认配置的端点适合接收这些数据。
