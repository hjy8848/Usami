# After-sales v3 Service Skill A/B 诊断报告

**状态：已执行；B 组达到 20 次 Service 调用上限后结束。** 这是一组固定世界上的单次诊断，不是性能结论，也没有运行 Reflection 或 Dynamic Gate。

## 实验设置

A 组使用冻结任务与原始 Service（无 Skill）；B 组只增加候选 `aftersales.current_quote_consent`。世界、任务、顾客身份与本地确定性 Customer、Service 模型和温度、工具、Sandbox、最大 20 次模型调用和 64 次工具调用均相同。离线核对确认两个 `config.json` 除 Skill context 外完全相同。

- 模型：`dashscope/qwen3.7-plus`，`temperature=0`。
- 世界哈希：`e8a76399af8f610f03ec64cd04c108f410c696662b80bbdbda38a55e8c80f392`
- 任务哈希：`e84be8b6e915334c4b8eeb8a94b7e7ad6c57e09e37d2fcabb4136cfd1c10c892`
- Skill Snapshot：`0a22df6944e48eecd15ee42e5fc55536e264fbcb0dadd9e5c812841542a63d35`
- Skill 内容哈希：`af918d45f3946fb60cd80327511114dc21f0685c7f80403f95cd4cb609a6c19d`
- 实际注入上下文哈希：`0c4e58a5f81d1b4e655f2a6384c03e388cb4c35a22daf1c6b6460f06af9effec`

候选 Skill 的来源记录为 `codex-subagent-reflection-substitute-static-only`：这是离线生成的候选，而非 Service 通过本轮模型 Reflection 自主生成。它只作为研究诊断材料，未正式选中，也未运行 Dynamic Gate。

## 结果

| 指标 | A：无 Skill | B：有候选 Skill |
|---|---:|---:|
| 运行状态 | `customer_finished` | `service_llm_budget_exhausted` |
| 最终业务目标达成 | 是 | 否 |
| 严格任务成功 | 否（Oracle 发现违规） | 否（未完成且有违规） |
| Service 模型调用 | 13 | 20（达到上限） |
| Service Token（输入 + 输出） | 60,057 + 3,848 = **63,905** | 149,259 + 8,996 = **158,255** |
| 业务工具调用 | 11 | 22 |
| 合法业务操作 | 7 | 15 |
| Oracle 确认的成功违规 | 4 | 7 |
| Customer 在线模型调用 | 0 | 0 |
| 离线 Replay | 通过 | 通过，任务结果仍为失败 |

A/B 合计 33 次 Service 模型调用、222,160 Service Token 和 33 次工具调用。Customer 由本地策略驱动，没有在线模型消耗。

## 具体观察

A 组最终完成退款目标，但 Oracle 检出 4 次业务违规：两次 `APPROVAL_REQUIRED`、一次 `ALREADY_RESOLVED`、一次 `EXPLICIT_CONSENT_REQUIRED`（未授权 `release_refund`）。因此“完成目标”和“过程正确”并不相同。

B 组的实际首个 Service 请求包含完整、逐字匹配 Renderer 生成的 Skill 文本；Snapshot、内容哈希和上下文哈希均核验通过。B 组仍然出现两次 `APPROVAL_REQUIRED`，之后反复对已解决的事项执行报价，产生 5 次 `ALREADY_RESOLVED`，最终耗尽 20 次 Service 调用预算。它没有调用 `release_refund`，所以不能据此说未经确认退款问题已修复；这个关键行为在 B 组根本没有被测到。

B 组没有完成最终退款，且违规数由 4 增至 7，Token 消耗约为 A 组的 2.48 倍。就这一次固定场景的观察而言，候选 Skill 没有改善决策，反而伴随重复报价、预算耗尽和更高成本。单次运行不能证明 Skill 普遍有害，也不能外推到其他世界；但它明确没有提供预期的正向证据。

## Replay 与证据

B 组的原始执行、配置、模型请求/回复、工具轨迹和 Oracle 均保存在本目录。离线重新执行 Replay 得到 `verified=true`、30 次模型记录、22 个业务事件，且确认任务未成功。Replay 不调用在线模型。A 组的原始证据仍在 `experiments/vast_coevo/results/after-sales-service-v3-diagnostic-live-20261019-001`，没有修改。

`service-skill-context.json` 保存实际注入文本；`service-skill-snapshot.json` 保存候选 Snapshot；`offline_replay_verification.json` 保存独立核验结果；`SHA256SUMS.txt` 可检查本目录文件完整性。

## 结论

这次得到的是一条**负向诊断结果**：候选 Skill 确实进入了真实模型上下文，但在这道任务里没有阻止审批前报价/结算，也没有让 Service 完成退款；Service 还在已解决状态上反复报价。下一步应先定位为什么模型在新状态下循环，以及 Skill 条款是否引导了不必要的重查/报价，再决定是否修改 Skill。不能将此结果描述成“Skill 学习有效”或“共进化成功”。
