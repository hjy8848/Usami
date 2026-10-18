# After-sales 真实模型闭环尝试：BLOCKED

本轮确实调用了真实 LiteLLM 模型，但三条业务执行任务完成 **0/3**。四次独立登记均在 Designer 出题阶段阻塞；没有进入 Customer–Service 交互或双方 Reflection，没有生成、接受或消费新 Skill。

## 实际执行

| 登记 | 模型 | 调用 | 原生结果 | Token |
| --- | --- | --- | --- | --- |
| [aftersales-coevo-live-20261018-attempt-007](../aftersales-coevo-live-20261018-attempt-007/manifest.json) | `dashscope/qwen3.7-plus` | 1 | 目标指向冻结世界中不存在的业务对象。 | 37036 |
| [aftersales-coevo-live-20261018-attempt-008](../aftersales-coevo-live-20261018-attempt-008/manifest.json) | `dashscope/kimi-k2.6` | 1 | 声明的修改范围不符合顾客原生契约，包含遗漏 selector_field 的条目。 | 32988 |
| [aftersales-coevo-live-20261018-attempt-009](../aftersales-coevo-live-20261018-attempt-009/manifest.json) | `dashscope/qwen3.7-plus` | 1 | 目标包含 lines.status=resolved；该状态不属于原生 Line 的合法枚举，Reference 未证明可达。 | 40545 |
| [aftersales-coevo-live-20261018-attempt-010](../aftersales-coevo-live-20261018-attempt-010/manifest.json) | `dashscope/kimi-k2.6` | 1 | finish_reason=length，4096 输出 Token 用满，未返回所要求的 Function Calling 提案。 | 35507 |

四次调用均保留原始请求和回复、冻结世界、初始 Library Snapshot、失败原因和模型用量。每次换模型或修改请求契约均建立了新目录，没有覆盖记录，也没有把多次尝试挑选成一次成功运行。所有尝试均使用 seed=1 的同一冻结世界。此次不是模型效果对比：模型与提示契约发生过变化。

## 修复的工程缺口

- `aftersales_coevo_live.py::_execute_task` 原来在返回结果路径时引用未定义的 `base`。现改用实际任务目录；新增原生 Engine + Replay 回归测试。
- `aftersales_coevo_live.py::_designer_context` 明确说明目标对象、原生修改范围、事实、确认和外部事件契约，不提供题目、答案或执行见证。
- `native_field_enums` 从原生 World 的 Pydantic Schema 自动读取字段枚举。Designer 原先只能看到当前字段值，缺少合法状态词表；新接口提供公共业务词表，而不提供 Reference 预期结果。
- 抽取共享初始 Skill 和 Evidence 适配，脚本化回归与真实运行复用同一套原生证据接口。脚本化模型不参与本轮线上请求。

第 007、008 次使用原始出题上下文；第 009 次补充契约说明；第 010 次进一步提供原生字段枚举。最后一次因输出预算耗尽而失败，因此不能宣称字段枚举补充已在线解决整个问题。

未修改 Engine、Reference、Oracle、业务权限或正式实验 Gate。此三任务集成入口延续仅静态选择的限定设置；没有运行任何动态性能验收、Held-out 或额外 Service 验证任务。

## 可复核记录

四个目录的 `verification/proposal-replay.json` 均通过离线复算重现同一拒绝，额外模型调用为 0。由于没有 Service Episode，**不存在三条业务轨迹的 Replay 通过结论**。

第 009、010 次另附 `source/registration.json` 与运行器、适配器、测试源码快照。原始请求可核查当时实际注入的契约和初始 Skill。所有旧实验记录保持不变。

## 成本与结论

真实实验调用 **4 次**，全部属于 Designer。输入 **130,332** Token，输出 **15,744** Token，合计 **146,076** Token。Service 调用 **0**，Reflection 调用 **0**。没有失败重试被隐藏在同一个请求中。跨这些登记的调用上限为 41，实际只消耗 4 次后停止。

真实瓶颈目前是 Designer 提案的可执行性和交付协议，尚未验证共同进化闭环，更未验证真实模型学习收益。后续应在独立注册中检查模型输出预算与工具交付行为，再继续这条三任务工程链；不应扩大题库或宣称性能改进。

## 自动验证

命令：`.venv/bin/python -m pytest -q tests/test_aftersales_coevo_live.py tests/test_vnext_open_compositions.py`。

结果：**19 passed**。覆盖调用预算、真实请求记录、原生字段枚举、实际业务执行与 Replay、冻结世界开放组合及身份边界。另对四次在线提案执行了离线拒绝复核，均准确重现，未增加模型调用。`git diff --check` 通过。

这是定向回归，不是全量回归。单元测试中的脚本化执行单独计为离线验证，不计入真实三任务完成数。
