# Designer 精确上下文离线诊断

## 结论

失败的 API 运行使用的是 `frozen-world-designer-exploration-v2`，不是后续 v3 协议。最终提交工具把 `refusal_operations` 和 `confirmation_requirements` 都描述成任意 JSON 对象数组，没有把业务操作的参数 Schema 交给模型。模型把 `case_id`、`line_id` 放错层级或添加了不属于该操作的字段，编译器才在提交后拒绝。

同一最终请求的 30 条消息、工具定义和模型参数已保存于 `designer-context.json`。离线 Codex 子智能体看到了这份原始请求和其历史只读查询/编译反馈，没有读取 World、Reference 或 Oracle，也没有调用外部 API。它从已观察到的 `u1_order1_line0` 提交了一道换货目标，现有 v2 编译器成功生成证明，离线 Replay 与 Oracle 均通过。

## 修正

当前 v3 提案 Schema 已经为 `refusal_operations` 提供按原生写操作区分的严格参数结构。本次补齐同一类结构到可选的 `confirmation_requirements`：字段仍可省略；一旦提供，就必须符合原生操作的完整参数形状，阻止多余或放错层级的 `case_id` / `line_id` 在工具 Schema 处漏过。Customer 授权、对象范围和业务规则验证没有放宽。

另一个失败来自任务选择：API 连续把 2025-12-01 送达、30 天售后期、世界时钟 2026-01-15 的订单设为退款完成任务。超额审批通过不会重置售后期限。这是模型对已给事实的判断错误，不是 Reference 不可证明；最终回合的历史反馈里没有能让模型回到正确拒绝挑战的有效机会。精确上下文离线复跑识别了这个日期边界并提交了另一道可证明任务。

## 验证范围

- 真实 API 调用：0（复用的是已存档请求，不重新发送）。
- Customer / Service 执行：0。
- Service Reflection / Skill 更新：0。
- 离线 Designer 提案：1，Schema 与当前源 v2 提案模型兼容。
- 原生任务编译及任务记录验证：通过。
- 独立 Oracle 与精确 Replay：通过；任务包含 5 个合法业务步骤。
- 相关自动测试：`tests/test_designer_exploration.py` 与 `tests/test_vnext_open_compositions.py`，39 项通过。

这证明当前冻结世界里存在可由相同交互记录提出并被原生证明的任务，也修复了新 v3 Schema 的确认操作字段缺少类型约束问题。离线子智能体不是 InferAI 的 DeepSeek，因此不能据此声称外部模型已修复或具备稳定自主出题能力。
