# Designer 出题离线诊断（v4）

日期：2026-10-19
范围：只检查 After-sales Designer 出题与任务证明；不执行 Customer、Service 或 Skill Reflection。

## 本次结果

用 Codex 子智能体替代外部模型，向它提供当前 v4 的 Designer 初始请求、提交工具 Schema 和预算，并让它通过同一份冻结世界的只读 `inspect_world` 接口自主调查。它查询了规则、顾客列表和一份顾客档案及关联对象，然后提交 1 道正确拒绝任务：顾客要求为 `u0_order0` 的缺件商品开案；实际送达日为 2025-12-01，商品售后窗口为 14 天，冻结时钟为 2026-01-15。顾客档案中的 2026-01-25 是其提出的期限，不会改写实际送达日或延长售后窗口。模型无需填写 `confirmation_requirements`，提案将其省略。

提案在 native compiler 中获证。独立 `verify_task` 重建并验证相同任务记录；证书中的 Oracle 状态为 `pass`，正确拒绝计数为 1，Replay 标记为通过。冻结世界哈希为 `c5227e1dc9d8b1a49d93b17eaf64018e64ce3c1bf8b00f3e20611c4a581bb3e6`。

## 这说明什么

- 当前 v4 的只读探索、可选确认字段、提案编译和纠错协议能够表达并证明这类任务；旧 v2 在线尝试中因错误提案而失败，并不等于 Reference 无法验证任务。
- 这次离线成功只能定位到“上下文和现有规则足以支持一个合法提案”。Codex 子智能体不是 DeepSeek，也没有外部模型请求，因此不能证明 DeepSeek 已能成功出题，更不能说明 Service 已经正确作答。
- 本次没有运行 Service，所以这是“可证明的挑战任务”，不是一次真实发现的 Service 错误。

## 运行与复现

`offline-run.json` 保存查询和提案；`native-certified-task.json` 保存原生任务证书及确定性见证；`independent-verification.json` 保存本地重编译及 Replay 的核验结果；`request-context.json` 保存 v4 请求上下文与提交 Schema；`archived-api-request-v2.json` 保存之前真实 DeepSeek 请求体（不含模型回复或凭据）；`manifest.json` 保存哈希清单。

本次外部 API 调用、Customer 执行、Service 执行和 Reflection 均为 0。相关自动测试 `tests/test_designer_exploration.py` 与 `tests/test_vnext_open_compositions.py`：43 passed。没有修改业务规则、Reference、Oracle 或 Designer 源码。
