# After-sales Customer Simulator 多模型 Smoke

日期：2026-10-20

场景：固定 `aftersales-user-scenario-v1`，scenario hash `8ebcc5666e3729e6c89143b689363191d9dfc7cfb8a9aae8d90189b1408904e5`
模式：真实 LLM Customer + 本地 `ControlledRefundService` fixture；fixture 不计分、不用模型；温度 0；无自动重试。

这是一轮接口和模拟器诊断，不是模型排名、Service 评测或 Skill A/B。前三个候选各限制为一次 Customer 请求；之后选择首轮合法且实际执行了开案的 GLM-5.2，额外完成一个最多 12 次 Customer 请求的对话。

## 结果

| Customer 模型 | 结果 | Customer 请求 / Token | 观察 |
| --- | --- | ---: | --- |
| `dashscope/qwen3.7-plus` | HTTP 400 | 1 / 未返回用量 | 无模型回复；错误正文未被旧客户端保存 |
| `dashscope/qwen3.6-plus` | HTTP 400 | 1 / 未返回用量 | 无模型回复；错误正文未被旧客户端保存 |
| `qwen3.6-plus` | HTTP 400 | 1 / 未返回用量 | 使用 `/models` 返回的裸 ID 仍为 400，前缀不是唯一原因 |
| `DeepSeek-V4.1-Flash` | 首轮有效 | 1 / 2,776 | 自然表达损坏与退款诉求；没有结构化披露或授权，Service fixture 追问订单和开案许可；该单轮样本 Fidelity 需复核 |
| `Kimi-K2.6` | 首轮被 Harness 拒绝 | 1 / 2,039 | 将 `preferences.resolution` 输出为数组 `[`refund`]`，而冻结场景要求单一字符串；没有业务副作用 |
| `GLM-5.2` | 首轮有效 | 1 / 2,464 | 披露订单、商品行、问题和证据，选择退款并授权开案；Oracle 确认为合法 `open_case` |
| `GLM-5.2` 完整对话 | Customer 主动结束，退款未释放 | 7 / 57,185 | 7 次业务操作全部合法；完成报价、两次确认和退货安排，但 Customer 在 `release_refund` 执行前结束，因此目标未完成，Fidelity 为 `needs_review` |

三款非 Qwen 模型都接受了同一份工具调用请求，说明请求整体结构可以被网关处理；Qwen 的三次 400 更像是 Qwen 路由或后端兼容问题。由于客户端当时只保存 HTTP 状态，没有保存响应错误正文，具体原因仍无法确定。不能据此断言 Qwen 模型自身不支持工具调用。

GLM 完整对话的关键边界：顾客根据实际报价接受退款并授权结算；退货完成后又对退款释放作了明确确认，但同时设置 `finish=true`，Service 没有下一轮执行释放操作。Oracle 记录 7 项操作均合法、0 项业务违规；任务完成分数为 false。该结果显示结构化授权能正确落到 Harness，结束时机仍需在更完整样本中检查。

## 总成本与回放

- 实际 Customer API 请求：13 次，其中 Qwen 400 三次；成功返回请求 10 次。
- 已返回用量的 Token：64,464（输入 60,688，输出 3,776）；三次 HTTP 400 没有用量数据，故不计入该总数，也不能确认网关是否收费。
- Service 在线模型请求：0；受控 fixture 调用只在本地执行。
- 所有七个 Execution 均通过离线 Replay。Replay 验证记录与状态转移，不代表 Customer 目标完成；GLM 完整对话的 task score 仍为 false。
- 没有修改 Engine、Reference、Oracle、Customer Schema 或业务规则；也没有运行自动化测试。

## 原始运行记录

本机保留每次运行的 `manifest.json`、`config.json`、`scenario.json`、`execution.json`、`replay.json`、`customer-fidelity.json` 和 `summary.json`，路径位于被 Git 忽略的 `outputs/` 下：

- `outputs/customer-simulator-smoke-20261020-001`
- `outputs/customer-simulator-smoke-20261020-qwen36-001`
- `outputs/customer-simulator-smoke-20261020-qwen36bare-001`
- `outputs/customer-simulator-smoke-20261020-deepseekflash-001`
- `outputs/customer-simulator-smoke-20261020-kimi26-001`
- `outputs/customer-simulator-smoke-20261020-glm52-001`
- `outputs/customer-simulator-smoke-20261020-glm52-full-001`

原始 JSON 含重复的完整冻结世界，合计约 103 MB。为避免把大量重复状态加入 Git，本目录只保存这份汇总；完整原始记录仍保留在上述本地运行目录。
