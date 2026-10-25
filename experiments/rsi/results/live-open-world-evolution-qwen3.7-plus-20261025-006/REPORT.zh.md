# 开放世界单题进化诊断

- 状态：`FAILED`
- 模型：`dashscope/qwen3.7-plus`
- World：1 个，hash `8c3a18f2b241c269149ef4bc9cb6eba45c437319ae0c81c0e5eccbcb46133fd2`（复用并冻结）
- Challenge：由 RSI M 提出；最多提交 1 次。
- Service：基线与 M0 提出的 P/K 候选各执行一次同一冻结任务。
- 真实模型请求：29 次。
- 参数训练：`NOT_RUN`。
- 独立选代：未运行；本诊断不宣称候选有效或已晋升。

## 结果

- Service root：`SUBMITTED`。
- P/K 候选：`a515a84b01c0047decc1b7cfef5a460371ee613670537041bc9af7282426903a`。
- 基线 Episode：业务目标 `True`，过程错误 `FAIL`，Replay `True`。
- 候选 Episode：业务目标 `True`，过程错误 `PASS`，Replay `True`。
- 调用量：基线 13 次 / 71391 Token；候选 12 次 / 70062 Token。
- 基线被 Oracle 记录的无效尝试：`[{'error_code': 'ALREADY_SETTLED', 'operation': 'release_accepted_refund'}]`；候选体验是否实际注入 Service 请求：`True`；其中包含防止重复释放退款规则：`True`。
- 严格任务评价：基线 `UNKNOWN` / 候选 `UNKNOWN`；两者严格评价均未解析（`UNKNOWN`、score 0），Customer 通信有未解析消息。
- M 自修改 root：`FAILED_PROVIDER_TIMEOUT`（请求已发送：`True`）。
- M 候选：[]。
- 阻塞阶段：`m_self_edit_proposal`；错误：`LLM request timed out; no retry performed`。
- 超时调用：请求体 41526 bytes，Provider 阶段 `ReadTimeout`；无法据此区分模型推理慢与网关/服务端延迟。
- 记录到的模型 Token：162226；超时请求的 Provider 用量未知。

## 证据

- `summary.json`：World、认证、Host 根轨迹、执行结果、Replay 与模型调用计数。
- `model-calls.jsonl`：真实请求和响应；不会保存认证头或 API Key。
- `native-episodes/`：基线和候选版本的 Engine、Oracle、Customer 与 Replay 记录。
- `research-archive/`、`programs/`、`task-records/`：研究动作、程序与证书快照。

这是单世界、单挑战的工程诊断。基线和候选在同一题上的比较不是独立选代，不能据此声称 RSI 能力提升。

## M 自修改续跑

首次 M 请求超时后，按 300 秒超时仅重试 M 阶段一次，复用相同公开上下文。模型成功生成 M 候选并通过静态接口检查；由于没有独立 M Probe，Host 保留父版本，候选未执行或选中。详见 [`m-self-edit-retry-300s/REPORT.zh.md`](m-self-edit-retry-300s/REPORT.zh.md)。
