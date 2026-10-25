# Qwen3.7-Plus 最小真实 RSI 运行记录

**结果：未跑完整。** 真实 LiteLLM 连通性检查通过，但正式 `run_open_period` 在 World 生成阶段遇到超时；没有进入 Challenge、Service Episode、Oracle/Replay、P/K 更新或 M 自修改。未运行训练。

## 观测

- 网关：`http://10.130.138.46:8010/v1`；模型：`dashscope/qwen3.7-plus`。Key 从 macOS Keychain 运行时读取，未写入输出。
- 预检请求：一次最小对话请求返回 `READY`，用量 15 prompt / 123 completion tokens。
- 正式周期的第 1 条 World Designer 请求：约 60 秒后得到 `PROVIDER_TIMEOUT`，底层阶段为 `ReadTimeout`；该请求没有用量回报。
- 代码随后对另一个预注册 World 槽位发出第 2 条请求，返回一个 `submit_world_constraints` 结构化工具调用（2,157 prompt / 2,216 completion tokens）。停止后，我把这份响应按原槽位与种子离线送入原生 Schema、编译器、Builder 和 `verify_build`：全部通过，结果为 SAT。它包含 1 位顾客、1 笔订单、3 个商品家族（laptop/mouse/headset），问题分别为 damaged、wrong_item、missing_parts，符合该槽位的多商品、多问题设计目标。World Hash 为 `6018f3178ba726434649bb974a80fb7ced674df9b516b9aefe80b3b1babfc32c`。
- 按照“遇到错误就停止”的要求，我在观察到第 1 条失败后中止进程。记录了 2 条已完成/失败响应；由于本次日志在请求返回后追加，无法确认中断瞬间是否已有下一条请求在途，其用量未知。

## 结论

这次证明了 LiteLLM API 可用，也证明模型至少返回过一次完整结构化 World 工具调用；没有证明 World 通过 Builder，也没有证明 RSI 周期能完成。当前直接阻塞是结构化 World 生成请求的超时，而不是已观察到的 Schema 拒绝或业务认证失败。超时原因可能是模型/网关响应延迟；仅凭一次失败无法区分是哪一端，也不能推断模型输出质量。

同时，当前 `WorldPopulation.next_period()` 会先遍历整批槽位（`integrations/rsi_usami/open_world.py:150-158`）；`design_world_slot()` 将 Provider 失败记录为 `BLOCKED` 并返回（`usami_v2/scenarios/designer.py:815-838`）。所以当前正式批次不会在首个 World 错误处自动 fail-fast。为了遵守本次停止要求，本次由外部中止，没有继续到后续阶段。

## 证据文件

- `model-calls.jsonl`：本次运行已记录的请求摘要、状态、脱敏 Provider 响应及用量；没有 API Key。
- `diagnostic-summary.json`：整理后的状态、已知/未知用量及第二个 World 的离线验证结果。
- `second-world-offline-validation.json`：第二个 World 的原生 Schema/Builder/Replay 校验摘要。
- `run_minimal.py`：本次使用的一次性真实模型工厂与运行器。
- `process-stop-summary.json`：进程中断时最初写出的原始摘要。
