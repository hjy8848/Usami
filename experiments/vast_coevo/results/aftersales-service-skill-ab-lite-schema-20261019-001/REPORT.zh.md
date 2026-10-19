# After-sales Service Skill A/B：报价协议修复后的配对复测

**结论：报价字段的 Schema 缺口已修复并通过协议测试；真实 A/B 两组都运行并通过离线 Replay，但实验仍不能判断 Skill 是否改善了目标行为。** 修复后的 Schema 被注入两组每一次 Service 请求，不过两组都没有真正提交报价操作；带 Skill 组还在 Customer 身份范围和确认未展示报价时发生协议错误。

## 修复内容

`respond_to_customer.offered_operation` 过去允许任意对象或 `null`，因此 `{}` 和 `verify_evidence` 都能通过模型侧工具结构检查，直到运行时才失败。现在 After-sales Schema 明确规定：

- 没有向顾客展示报价时传 `null`。
- 有报价时只能传符合该操作参数结构的 `commit_resolution` 或 `release_refund`。
- 对象必须含有效的操作名、作用范围、资源 ID 和严格匹配的参数；不接受缺失字段或额外字段。
- 运行时仍用当前世界的 `offer_for` 核实是否存在真实报价。Schema 不告诉模型报价是否存在，也不替代业务规则、顾客授权或 Oracle。

无效输出仍可获得一次已有预算内的格式恢复机会；它不会触发业务动作。修复不改变 Engine、Reference、Oracle、Skill 内容或任务。

## 固定条件

同一冻结 After-sales 世界与任务，seed 0；同一顾客、模型 `dashscope/qwen3.7-plus`、temperature 0、工具、Sandbox、预算与执行协议。唯一 A/B 差别仍是 Service 是否收到候选 Skill `aftersales.current_quote_consent`。模型调用没有设置 `max_tokens`，也没有自动重试。

候选 Skill snapshot：`0a22df6944e48eecd15ee42e5fc55536e264fbcb0dadd9e5c812841542a63d35`；内容哈希：`af918d45f3946fb60cd80327511114dc21f0685c7f80403f95cd4cb609a6c19d`。候选此前通过静态检查；本次未运行 Dynamic Gate。

## 结果

| 指标 | 不带 Skill | 带 Skill |
|---|---:|---:|
| Episode 状态 | 顾客结束对话 | Customer 协议错误终止 |
| Customer / Service 模型调用 | 4 / 13 | 4 / 11 |
| 总模型调用 | 17 | 15 |
| Token（输入 + 输出） | 101,000 | 92,985 |
| 业务工具调用 | 10 | 9 |
| Oracle 确认的成功业务违规 | 3 | 1 |
| 最终任务目标达成 | 否 | 否 |
| 非空报价操作提交 | 0 | 0 |
| 离线 Replay | 通过 | 通过 |
| Skill 注入核验 | 对照组未注入 | 通过 |
| 新报价 Schema 在所有 Service 请求中 | 通过，13/13 | 通过，11/11 |

不带 Skill 组出现两次 `PREFERENCE_RESOLUTION_REQUIRED`，以及一次 `STALE_CUSTOMER_CHOICE`；相关调用还被 Oracle 标记为未授权写操作。它最后以 `customer_finished` 结束，但退款目标没有达到，Oracle 状态为 `fail`。

带 Skill 组出现一次 `PREFERENCE_RESOLUTION_REQUIRED` / 未授权操作。随后 Customer 提交的请求超出单一冻结顾客范围，并尝试确认一份 Service 实际没有展示的报价；这两次协议错误导致 Episode 以 `customer_protocol_error` 结束。最终目标也未达到，Oracle 状态为 `fail`。

两组都没有调用带非空 `offered_operation` 的 `respond_to_customer`。因此，Schema 修复确实消除了工具定义中的“任意对象”缺口，但这次模型运行没有走到报价展示和顾客确认环节。违规次数较少的一组不能据此视为 Skill 更有效：这是单个世界、单次配对，且两边的对话轨迹不同。

## 成本与复现

整对共 **32 次模型调用**，消耗 **193,985 Token**（输入 179,253，输出 14,732）；用量字段完整。模型服务没有返回价格，本报告不估算费用。

保存了完整请求和回复、工具结果、Oracle 记录、精确 Skill Prompt、候选 Snapshot、Schema、配置、Replay 与运行脚本。两条 Episode 的模型请求重放和业务轨迹 Replay 均验证通过。完整清单见 `manifest.json`；证据包见 `raw-evidence.tar.gz`，SHA-256 见 `ARCHIVE_SHA256.txt`。

## 判断

**修复与协议验收：通过。** 空对象、非报价操作、缺参和额外参数被静态 Schema 拒绝；`null` 及结构有效的两种报价操作可通过；运行时对空对象有明确拒绝且恢复时不产生业务动作。相关 After-sales Dialogue 测试 10 项通过，完整 Dialogue 测试集 52 项通过。

**Skill 效果：证据不足。** 本轮没有发生报价展示或确认，且两组最终任务均失败。下一步应先解决顾客偏好写入与顾客身份/确认交互中的协议问题，再决定是否重做配对测试；不要把这次的 3 对 1 违规数解释为 Skill 带来的提升。
