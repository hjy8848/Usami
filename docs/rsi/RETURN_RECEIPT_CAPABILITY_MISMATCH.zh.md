# 最小真实运行阻塞：退货签收能力与 Challenge 接口不一致

**记录日期：** 2026-10-25

**范围：** 只讨论一次真实模型最小运行中，退货签收能力未配置导致 Challenge 无法认证的问题。

## 后续实施状态

后续两次真实 Service 都停在报价展示与 Customer 结束处，已单独整理为 [给 GPT 的报价交互专项审阅](QUOTE_PRESENTATION_CUSTOMER_TERMINATION_GAP.zh.md)。该问题与本文件讨论的退货签收能力分开记录。

已执行路径 A：复用原冻结 World，真实 Designer 根据上一轮公开拒绝原因修订为无需退货的 Hub 单目标退款任务，获得原生 `CERTIFIED` 后执行了真实 Service、Oracle 和 Replay。9 次业务操作均合法，Replay verified；Service 准备报价后没有提交正式报价展示动作，确定性 Customer 直接结束，最终退款目标没有达成，评价为 `UNRESOLVED`。[完整运行记录](../../experiments/rsi/results/live-one-world-task-revision-20261025-003/REPORT.zh.md)。

随后落实动态 Schema：退货能力关闭时，每个 `LineSelector` 必须显式提供 `return_required=false`；能力开启时保持原 Schema。模型响应还会在本地按同一动态 Schema 校验。绕过模型 Schema 的直接调用仍由 Compiler 的 `RETURN_RECEIPT_UNAVAILABLE` 检查拒绝。

真实退货计划、外部事件、Runtime 和 Replay 的整套联调仍未实施。以下保留最初问题和评审上下文。

## 希望 GPT 判断的问题

这次失败应如何归因和修复？模型收到 `return_receipt_event_configured=false` 后，仍然为需要退货的商品提出换货/补发目标；但 Challenge Schema 允许这些目标，Compiler 才在提交后拒绝。请判断：

1. 这是模型没有遵循能力提示、系统能力契约不完整，还是两者共同造成？
2. 最小的正确修复是什么，才能让 Designer 只提出当前 Reference 与 Runtime 真正能执行和认证的任务？
3. 如果要支持退货类任务，如何保证 Customer 场景、Reference、Engine、外部退货签收事件和 Replay 使用同一份冻结计划？
4. 当前是否应先在同一冻结 World 上，让 Designer 修订为不需要退货的一道任务，以继续验证最小 Service 流程？

**评审约束：** 不要建议移除原生认证、把能力标记直接强制设为 `true`，或伪造退货签收。业务规则、Reference、Engine、Oracle 和 Replay 必须保持独立有效。

## 本次真实运行

运行采用 `dashscope/qwen3.7-plus`，每次请求超时为 180 秒，只生成 1 个 World 并提交 1 个 Challenge。没有重试。

| 阶段 | 结果 |
| --- | --- |
| World Designer | 实际模型提交；原生 Builder 返回 `SAT` |
| World | 1 位顾客、1 个订单、3 条商品行：损坏笔记本、错发鼠标、缺少配件的 USB Hub |
| Challenge Designer | 实际模型提交一项 3 商品目标的结构化挑战，Schema 校验通过 |
| Grounder | `GROUNDED`，找到 1 个业务对象绑定 |
| Challenge 编译 / 认证前置检查 | `UNVERIFIED / CAPABILITY_UNSUPPORTED` |
| 阻塞代码 | `RETURN_RECEIPT_UNAVAILABLE` |
| Service / Oracle / Replay | 未运行；未认证任务不会交给 Service |

- 两次模型请求均成功返回：1 次 World 提案、1 次 Challenge 提案。
- 总计 4,428 prompt tokens、4,296 completion tokens，用时约 71.5 秒。
- 完整请求、模型响应、World 构造记录和认证拒绝记录保存在对应的实验结果目录中。
- World hash：`8c3a18f2b241c269149ef4bc9cb6eba45c437319ae0c81c0e5eccbcb46133fd2`
- 运行报告：[live-one-world-one-task 报告](../../experiments/rsi/results/live-one-world-one-task-qwen3.7-plus-20261025-002/REPORT.zh.md)

## 这道挑战具体要求什么

模型为一个顾客、同一订单中的三条商品行提出了目标：

1. 损坏的笔记本：退款或换货。
2. 错发的鼠标（数量 2）：换货或补发。
3. 缺少配件的 USB Hub：退款。

World 拓扑确实满足顾客、订单和商品行关系，Grounder 找到了 1 个合法绑定。因此失败发生在 Grounding 之后，不是“世界里没有这些商品”或“Designer 编造了订单”。

笔记本和鼠标对应的 SKU 标有 `return_required=true`。本次 Customer 绑定只配置了顾客和授权商品行，没有退货取件安排或预计签收时间。实际运行在 Compiler 的能力检查处就停止了，Reference 没有被调用；如果只把 Compiler 的能力开关强行打开，后续 Reference 仍会因为 Customer 场景没有取件/签收计划而无法认证。

这里的“退货签收”是模拟世界中的业务状态事件：商品被退回后，仓库确认收到。它不是顾客上传一张照片，也不是可以由 Designer 自行声明的文本凭证。

## 为什么既是模型问题，也是系统接口问题

### 模型的直接错误

提交内容符合结构化 Schema，且抽象 selector 成功 Ground 到真实对象；但是模型没有据 `return_receipt_event_configured=false` 避开需要退货的商品目标。这是目标选择上的语义错误，不是 JSON 或 Function Calling 格式错误。

### 系统暴露的契约缺口

当前公开能力清单提供 `return_receipt_event_configured=false`，同时仍将 `refund`、`exchange`、`reship` 列为支持 remedy；Challenge Schema 也没有依据每条商品行的退货要求限制可选目标。Compiler 到 `compile_task()` 才检查：商品行需要退货、但本次能力未配置时，抛出 `RETURN_RECEIPT_UNAVAILABLE`。

因此模型被告知了一个抽象限制，却没有得到可执行的“哪些商品行/目标组合不可选”约束。最终拒绝是正确的，但系统把一个可以前置表达的限制留到了提交后的 Compiler 检查。

此外，当前真实运行的 `customer_binding()` 没有填写 `CustomerScenario.return_pickup_slot` / `return_received_after_days`，桥接器也没有传入 `external_event_factory`。不能只把能力布尔值改成 `true`：那会宣称系统支持一个实际没有配置的状态转移。

## 代码核查位置

- [`_abstract_challenge_schema()`](../../integrations/rsi_usami/open_world.py)：目前按全局 `supported_remedies` 收窄 Schema，没有按 `return_required` 对每个商品行施加条件。
- [`task_design_capabilities()` / `compile_task()`](../../usami_v2/scenarios/designer.py)：能力清单的退货事件默认关闭；Compiler 对需要退货的目标返回 `RETURN_RECEIPT_UNAVAILABLE`。
- [`OpenChallengeBridge`](../../integrations/rsi_usami/open_world.py)：存在 `capability_options` 和 `external_event_factory` 接口，但本次真实运行没有配置真实退货计划与事件。
- [`customer_binding()`](../../experiments/rsi/fixtures/open_world_validation.py)：当前默认绑定不包含退货取件与签收计划。
- [`_base_candidate_options()`](../../usami_v2/scenarios/task_certification.py)：Reference 只有在冻结顾客场景提供取件时间及签收时间后，才会将需要退货的目标纳入可行路径。
- [`test_native_return_receipt_capability_remains_available()`](../../tests/test_rsi_open_world.py)：测试夹具在补入可信的顾客退货计划并启用能力后，任务认证通过。这证明 Reference 侧已有能力接口，不代表真实 Service / 外部事件 / Replay 的整条链路已经联调通过。

## 候选修复路径

### 路径 A：先完成最小 Service 诊断

复用本次已冻结的 World，让 Designer 基于公开的 `RETURN_RECEIPT_UNAVAILABLE` 拒绝原因，修订成一项不涉及退货商品的任务。例如，只选择 `return_required=false` 的 USB Hub 并提出一个符合当前规则的退款目标。之后仍需通过原生 Grounder 与 Reference，认证通过后才能执行 Service。

这会再产生一次 Challenge 提案，但不需要重建 World。它能继续验证“真实 Designer → 认证任务 → Service → Oracle / Replay”中尚未触达的阶段。它不证明退货类任务已支持。

### 路径 B：正确支持退货类任务

给冻结 Customer 场景安排合法取件时间与真实的签收时刻；将同一份计划提供给 Reference，并通过可信的 `external_event_factory` 把 `return_received` 事件登记给原生 Runtime。Replay 必须能够复算同一事件及其状态变化。只有这些条件全部成立，才能公开声明 `return_receipt_event_configured=true`。

同时，Challenge 输入应公开每条候选商品行是否可认证，或提供由 Host 派生的可行目标约束；不可认证的 selector/目标组合应在 Schema 或前置校验阶段明确排除。认证器仍保留最后的独立裁决。

## 本次结论边界

- 已证明：真实模型生成了 1 个合法 World，并针对它提交了一个结构合法、成功 Grounding 的多商品挑战。
- 已确认：当前运行没有退货签收计划，Compiler 能力门因此拒绝该挑战；Reference 尚未运行。
- 未证明：真实 Service 是否能完成该挑战；Service 没有运行。
- 未证明：为退货启用真实外部事件后，Service、Oracle 和 Replay 能否完整一致地执行。
- 未改变：业务规则、认证标准、训练状态或 held-out 信息边界。
