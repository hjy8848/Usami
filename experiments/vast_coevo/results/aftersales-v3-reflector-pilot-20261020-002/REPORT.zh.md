# After-sales V3 Service Reflection Pilot — 运行报告

状态：**REFLECTION_FAILED_HTTP_400**。一次预注册 Reflection 已实际发送；12 场独立配对评估尚未开始。

## 运行结果

来源实验的 S0/S1 真实轨迹 Replay 均通过。S0 的一条 `release_refund` 操作被 Oracle 确认为成功执行业务违规，包含 `EXPLICIT_CONSENT_REQUIRED` 与 `UNAUTHORIZED_OPERATION`。该来源被明确消费为训练证据，其世界和结构均已从新验证任务中排除。

Reflection 前冻结了 3 个新世界、3 个任务证书和 12 个 S0/S1 Episodes：退款、换货、以及退款与重复申请拒绝的组合。预注册输入哈希、任务证书和来源 Replay 的离线核验通过。固定 Customer、模型配置、业务模式和预算没有因结果改变。

真实 Service Reflector 请求使用 `dashscope/qwen3.7-plus`，并通过本地 LiteLLM 网关发送。网关在本次请求中返回 HTTP 400。请求只发送一次，没有自动重试；系统未生成 Patch，因此 Static Gate 未运行，12 场评估也没有启动。Token 用量未返回。请求约有 43,341 个 message 字符，其中 user payload 42,267 字符；提交的 Function Schema 为 8,465 字节，工具名为 `submit_skill_patch`，调用使用强制 `tool_choice`。

## 能确定什么

这不是等待 120 秒的超时：端点在请求后返回了 400。它证明**这次请求被端点拒绝**，但当前 `OpenAICompatibleClient` 不保留 HTTP 错误正文，所以无法确认拒绝原因。

请求 Schema 包含 `$defs` / `$ref`、`oneOf`、`anyOf` 和 `if/then` 等构造；强制工具选择和模型路由也是候选排查点。它们只是待验证假设，不能据此直接断言是模型 Bug、网关 Bug 或某一字段不兼容。之前相同模型成功处理普通 Service 工具调用，也不能证明它接受这份 Reflection Schema。

## 保留的证据

- `preregistration.json`：冻结的模型、任务、分区和预算。
- `reflection/input.json`：绑定真实 Oracle 失败的完整输入。
- `reflection/model-calls/0001-service_reflection.json`：唯一实际请求及已脱敏错误状态。
- `reflection/record.json`、`reflection/status.json`、`reflection/live-result.json`：调用结果、错误码和限制。
- `preflight-audit.json`：任务证书、预注册哈希和两臂源轨迹 Replay 核验。
- `preflight-attempt-001.json`：先前一次凭据预检未发模型请求；之后已通过现有 `litellm` / `litellm-api-key` 登录钥匙串项目成功解析凭据。
- `../aftersales-v3-reflector-pilot-20261020-001/`：更早的准备阶段失败目录，保留其失败信息与文件。
- `../aftersales-v3-first-pair-live-20261020-001/`：第一组真实 S0/S1 运行及逐调用原始记录。

## 验证与成本

本轮源码测试：30 项通过（Reflection、安全输入校验、v3 配对入口与共同进化入口）。来源 S0/S1 Replay 均通过，3 个新任务证书通过。实际 Reflection 调用：1；评估 Episode：0/12；未获得可用 Token 统计。没有性能或泛化结论。

继续实验需要先查明 400 的具体端点错误，再为任何新调用建立独立、版本化的预注册；本次失败不会被覆盖，也不会自动重放。
