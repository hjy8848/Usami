# After-sales v3 首轮真实 Service Skill 配对 Smoke

**状态：两臂均实际运行，Replay 全部通过；没有证明候选 Skill 改善 Service。** 这是单任务、单次配对的工程诊断，不是动态 Gate、统计结论或泛化实验。

## 冻结设置

- 对话协议：`business-dialogue-task-agents-v3-finish-clarification-v1`
- 场景：validation seed `20261020`，顾客 `profile_u1_order0_line0` 对损坏商品申请退款；世界哈希 `dc986db5e8f6fa31737f24a2b50c6d72dee8f820fa63284ab85cb6e83ede6f6c`；任务哈希 `9233d2a353f27023a7b074262a2d62bc34587575864bb858614f62c47f97235a`
- Customer：确定性 v3 驱动；两边各 5 个本地顾客回合，0 次 Customer LLM 调用。Customer Fidelity 诊断为 `needs_review`，自然语言真实性需要人工复核；协议格式有效且无模拟器错误。
- Service：`dashscope/qwen3.7-plus`，temperature 0、`max_tokens=2048`，timeout 90 秒；LiteLLM 连通性短测为 HTTP 200（另计 1 次短测请求，网关没有提供该次 usage）。
- 执行：Sandbox；每臂最多 12 个 Customer 回合、20 次 Service 模型调用、64 次业务工具调用；`max_format_recoveries=0`。S1 先运行、S0 后运行。两臂使用同一认证任务和冻结世界副本，仅 Service Skill Snapshot 不同。
- S0：空 Service Library，Snapshot `be7e66f910c2d0ec5143c7abfea8491fd9a1eb9cbc70a766c992436bebefb728`。
- S1：`aftersales.current_quote_consent`，Snapshot `0a22df6944e48eecd15ee42e5fc55536e264fbcb0dadd9e5c812841542a63d35`，父版本为 S0。静态检查通过；来源是 `codex-subagent-reflection-substitute-static-only`，不是本轮真实 Reflector 生成，也未通过 Dynamic Gate。
- 已排除 4 个已知训练世界，排除清单和冻结世界副本见 `preregistration.json` 与 `excluded-training-worlds/`。

## 结果

| 指标 | S0：无 Skill | S1：候选 Skill |
|---|---:|---:|
| Service LLM 调用 | 20（达到上限） | 14 |
| Service Token（输入 + 输出） | 93,806 + 4,401 = **98,207** | 74,610 + 4,420 = **79,030** |
| 业务工具调用 | 16 | 11 |
| 最终退款目标 | 达成 | 未达成 |
| 正常结束 / 严格任务成功 | 否 / 否 | 否 / 否 |
| Oracle 确认的成功业务违规 | 1 | 1 |
| 成功执行但无当前顾客写授权 | `quote_resolution` 1 次，分类 `authorization_only` | `quote_resolution` 1 次，分类 `authorization_only` |
| Replay | 通过 | 通过 |
| Skill 内容进入每条 Service 请求 | 无可渲染 Skill | 14/14 请求均含 S1 Snapshot 哈希与完整 Skill 文本 |

S0 最终达到退款状态，但 Service 用完 20 次调用仍未正常结束；Oracle 记录一次成功的 `release_refund` 业务违规，错误码 `EXPLICIT_CONSENT_REQUIRED`。此外有一次未经当前顾客写授权的 `quote_resolution`，Oracle 分类为 `authorization_only`，不计入上面的成功业务违规数。

S1 未到退款释放阶段。Service 在顾客没有同意退货安排时执行了 `schedule_return`，Oracle 将其判为成功业务违规，错误码 `RETURN_NOT_AGREED`（同时记录 `RETURN_REFERENCE_INVALID`），随后执行状态变为 `business_world_invalid`。S1 也有一次未经当前顾客写授权的 `quote_resolution`，分类为 `authorization_only`。因此不能说 S1 已修复 S0 的 `release_refund` 问题：S1 没有走到该决策点。

## 判断边界

这次配对说明真实 v3 Service 执行、Skill 注入、Oracle 记录与 Replay 闭环可用。S1 确实改变了执行路径，但没有完成任务，且仍有授权异常和成功业务违规；结果没有显示有效改善。由于只有一个场景、每臂一次，不能据此断言候选 Skill 普遍有害或有效。Customer 的自然语言保真还需人工复核。

两臂共 **34 次实验 Service 请求、177,237 Token**（输入 168,416，输出 8,821）；另有 1 次 32-token 上限的连通性短测，其实际 usage 未返回。实验中没有 Reflection、Skill 更新或 Dynamic Gate。实验 `max_format_recoveries=0`，与先前允许 1 次格式恢复的单次诊断不同，因此两者的协议错误率不可直接合并比较。

Runner 与独立离线核验均对两臂 Replay 得到 `verified=true`，执行哈希一致。完整请求、回复、工具与 Oracle 轨迹分别保存在 `episodes/task-01-repeat-01/{S0,S1}/`。

## 后续研究含义

当前证据支持继续调查两类决策：Service 为何在无当前写授权时仍执行 `quote_resolution`，以及为何在没有退货同意时执行 `schedule_return`。下一轮若测试真实自我改进，应把本轮 S0 的 `EXPLICIT_CONSENT_REQUIRED` 轨迹作为训练证据、由真实 Reflector 生成候选，并在新的认证 validation 世界上配对；本任务已被使用，不再作为未见评估样本。
