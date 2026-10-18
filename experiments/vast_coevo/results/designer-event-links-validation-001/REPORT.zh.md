# Designer 事件关联修复与独立验证

## 1. 确定的查询 Bug 已修复

原 `read_profile` 将事件值与 `private.protected_objects` 比较。After-sales 的受保护对象是订单 ID，而经理审批和退货事件绑定 `line_id`，因此漏掉了已登记的关联事件。

新查询保留旧对象匹配，增加画像同名 `*_id` 字段关联。只返回世界中实际存在、与当前画像匹配的原始事件。不改事件结果，不触发事件，不替模型选择事件日程。测试核对了审批和退货事件、排除其他商品/顾客事件、世界不变和查询 Replay 篡改检测。

新会话记录 `include_profile_events=true`；旧日志未记录该字段时保留原语义，修复前 InferAI 失败日志依然能精确重放。旧实验没有重写。

## 2. Reference 单独验证

所有对照只使用同一个冻结 seed=1 世界，哈希 `c5227e1dc9d8b1a49d93b17eaf64018e64ce3c1bf8b00f3e20611c4a581bb3e6`。没有业务状态、规则、权限或 Oracle 变更。

| 对照 | 结果 | 原生业务步数 |
|---|---|---:|
| 现有五步退款题，重复编译与证书 Replay | 通过且结果稳定 | 5 |
| 同一题，删除全部登记事件 | 仍通过，实际未消费外部事件 | 5 |
| 真正需要审批的退款，登记原生批准事件 | 通过且证书 Replay 通过 | 6 |
| 同一审批任务，删除批准事件 | 有界搜索未证明 | — |
| 真正需要退货的退款，登记原生收货事件 | 通过且证书 Replay 通过 | 8 |
| 同一退货任务，删除收货事件 | 有界搜索未证明 | — |

关键区别：现有五步题的商品不要求退货，金额低于审批额度，两种事件对它都不是必要条件。初写负对照时假设它们必需，测试明确失败；核对原生规则后改为断言这道题不消费事件，再使用冻结世界中真正有条件依赖的对象建立负对照。初次失败日志保留在 `initial-control-assumption-tests.log`。没有通过放宽验证器来获得测试通过。

这些结果说明当前对照上的原生证明、必要事件依赖及 Replay 正常，不能据此保证所有可行任务都能在有限搜索预算内找到证明，也不能直接解释旧实验另外两份提案的全部失败原因。

## 3. 验证范围与运行入口

相关回归 43 项通过；新增的事件上下文精确 Replay/篡改检测 1 项通过。共 44 项测试，两次命令结果分别保存。未重复全量回归；未修改 Service Gate、World、Engine、Reference Rules、Oracle 或任务评分。

新增最小入口：

```sh
.venv/bin/python -m experiments.vast_coevo.examples.designer_event_link_check \
  --output experiments/vast_coevo/results/designer-event-links-local-NEW
```

默认完全离线。只有明确添加 `--live` 才运行一次 Designer 会话，最多 9 次模型请求，不运行 Customer、Service、Reflection 或 Skill 更新。离线对照必须先通过，而且控制题、对象及证明答案不会放入 Designer 的提示词。

独立记录：`designer-event-links-offline-001/`、`designer-event-links-live-001/`。本报告目录包含测试日志和本次实际源码快照/哈希。

## 4. 唯一一次真实 Designer 会话

使用前一轮已确认可用的 InferAI `deepseek-v4.1-flash`，相同模型、世界、4096 输出 Token 上限及温度 0，传输不重试。没有另发连通探针，也没有换模型。结果 **BLOCKED**，0 份证书，0 次 Service 执行，0 次 Reflection，0 次 Skill 更新。

实际 9 次模型请求、8 次只读查询。模型读取了两个画像的 4 条原生关联事件，并在完整提案中选择了实际收到的 `manager_review_u0_order2_line0`。因此能够直接确认查询修复进入了真实上下文，而不只是离线测试通过。

后续失败分别是：多次 `finish_reason=length`；提交的 JSON 字符串未闭合；一份完整提案的自然语言请求提到所选画像原生作用域之外的标识，被原生检查拒绝；最后一次请求收到 HTTP 502，当即停止，未重新开启会话。该完整提案还继续围绕原先过期商品要求退款，因此看见审批事件不代表出题目标正确。不能把本次失败统称为 Reference 搜索能力不足。

收到 usage 的请求合计输入 80,151、输出 23,150，**已知至少 103,301 Token**。HTTP 502 没有 usage，实际计费总量未知。原始请求仍发送 `thinking.type=disabled`，但多次响应输出了 `reasoning_content`；不能宣称提供方始终遵守了关闭思考的配置。本轮不修改模型调用协议来掩盖这个问题。

失败会话的查询、响应、反馈和错误均已精确离线回放，新增在线调用 0，详见 `designer-event-links-live-001/live-replay.json`。这验证了记录完整性，不是任务成功或真实学习收益。

结论：代码侧的关联事件可见性已修复，原生 Reference 在所选正负对照上正常；唯一真实出题会话尚未成功，后续还需分别处理模型输出可靠性、出题目标和作用域表述。没有扩大规模或启动后续进化。

## 4. 按要求取消输出 Token 上限后的单次复跑

我在新的独立目录 `designer-event-links-live-002/` 再跑了一个有界会话。9 次请求中都**没有发送 `max_tokens` 字段**；模型服务自身仍有产品端的上下文/输出上限，但请求没有我之前加的 4096 Token 限制。本次 9 个响应全部以工具调用结束，没有 `finish_reason=length`，输出共 19,899 Token。

Designer 查询到审批/退货事件并尝试4份提案。移除截断后，它能完整交付请求；但 Reference 依次指出操作参数结构错误，最后提案又因确认操作超出该顾客授权范围被拒。故最终仍为 **0/1 题获证，Service 0 条，Reflection 0 次，Skill 更新 0 次**。这说明输出上限确实造成了上次的截断现象；取消上限解决了该现象，但没有自动解决提案格式与顾客授权边界判断。

本次 9 次调用用量完整：输入 95,341、输出 19,899，共 **115,240 Token**。会话失败记录精确离线 Replay 通过，回放新增线上调用 0。结果、原始请求、每轮反馈和注册世界均保存在新目录。

离线重放命令：

```sh
PYTHONPATH=. .venv/bin/python experiments/vast_coevo/examples/verify_designer_event_links_live.py
```

它复核第二次会话的 9 轮失败过程与模型请求序列，不调用在线模型。
