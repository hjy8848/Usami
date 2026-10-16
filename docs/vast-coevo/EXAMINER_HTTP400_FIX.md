# 考官 HTTP 400 修复

## 已确认的原因

2026-10-16，用同一 `dashscope/qwen3.7-plus` 网关执行两次最小参数对照，每次最多 64 输出 Token：

| 请求 | HTTP | 结果 |
| --- | --- | --- |
| `tool_choice` 指定函数对象 | 400 | `The tool_choice parameter does not support being set to required or object in thinking mode` |
| `tool_choice: auto` | 200 | 正确调用 `submit_exam`，参数为 `{"title":"hello"}` |

这是网关返回的实际错误，不再是推测。两次请求仅含测试标题和极简工具定义，没有业务世界。原诊断保存在本地 `outputs/vast-coevo/examiner-http400-diagnostic-001/`；不含 API Key。

## 修复

删除考官运行器强制覆盖 `tool_choice` 的一行，保留原 `ModelSettings.request()` 的 `auto`。不关闭或更改模型思考设置，不改变 Service 参数、工具 Schema、Reference、Oracle、身份或权限。

`auto` 仅改变 HTTP 请求的工具选择参数。返回后仍要求恰好一个 `submit_exam`；错误工具、普通文本、多个调用、缺字段、非法世界、不可达目标或越权 witness 都记录失败，不自动重试，也不调用后续 Service。

请求差异由原 wire journal 和 source pins 记录。历史失败实验保留，使用原源码包 Replay，不重新解释为成功。

## 自动验证

相关回归 56 passed，31.40 秒：考官协议、递归训练、历史网页样例。包含四领域 `auto` 请求断言，以及错误工具、多个调用和缺字段的拒绝测试。

## 完整真实请求复测

新目录 `outputs/vast-coevo/examiner-v1-smoke-002/`，不覆盖 `001`：

- 初始 Service Task 完成。Customer 收到正常模型回复，`finish_reason: tool_calls`，调用 `submit_exam`；原 HTTP 400 未复现。
- 但模型生成的 arguments 不是合法 JSON：`Expecting ',' delimiter: line 7 column 809 (char 7735)`。严格解析拒绝该提案，未进入后续 Service。未自动修补、重试或放宽验证。
- 7 次真实调用：Customer 1、Service 6；8 次业务工具调用；Reflection / Held-out 0。
- Customer input / output / total：23,712 / 4,842 / 28,554 Token。
- Service input / output / total：32,547 / 1,534 / 34,081 Token。合计 62,635 Token，不含前面的两次微型参数诊断。诊断 auto 请求另报告 327 Token，诊断 400 请求 usage 未知。
- 两场记录的精确离线 Replay 均通过；源码包 `source.tar.gz` 保存当次 161 个 pinned 模块。

结论：HTTP 参数冲突已修复；完整真实模型出题仍受非法 JSON 输出阻塞。这两种结果必须分开。原始回复保留在本地证据中，不公开，也没有将格式错误当成业务漏洞或出题成功。
