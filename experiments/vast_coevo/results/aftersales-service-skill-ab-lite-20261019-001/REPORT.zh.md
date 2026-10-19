# After-sales Service Skill A/B 小型真实模型测试

**结论：两组都实际运行并通过离线 Replay，但本次结果不足以判断 Skill 是否修复了目标错误。** 两组都在退款报价/确认阶段之前触发了 Service 工具协议错误，因此没有完成任务，也没有真正测试到“无结构化同意时是否会阻止结算”。

## 固定条件

- 模型：LiteLLM `dashscope/qwen3.7-plus`，temperature 0；A/B 运行没有设置 `max_tokens` 输出上限。
- 同一冻结 After-sales 世界和任务，seed 0；顾客模型、Customer Policy、业务工具、预算和 Sandbox 语义相同。
- 唯一实验变量：Service 是否收到候选 Skill `aftersales.current_quote_consent`。
- 不带 Skill 使用空 Service Snapshot `be7e66f910c2d0ec5143c7abfea8491fd9a1eb9cbc70a766c992436bebefb728`；带 Skill 使用 Snapshot `0a22df6944e48eecd15ee42e5fc55536e264fbcb0dadd9e5c812841542a63d35`，Skill 内容哈希 `af918d45f3946fb60cd80327511114dc21f0685c7f80403f95cd4cb609a6c19d`。
- 这是对已知问题场景的定向回归，不是 Held-out 泛化评测。候选 Skill 之前通过静态检查；本次没有运行 Dynamic Gate。该候选来自离线替代反思，不是本次 LiteLLM 生成。

## 结果

| 指标 | 不带 Skill | 带 Skill |
|---|---:|---:|
| 结果 | Service 协议错误，任务未完成 | Service 协议错误，任务未完成 |
| Service / Customer 调用 | 6 / 1 | 5 / 1 |
| 工具调用 | 4 | 5 |
| Token（输入+输出） | 33,737 | 33,175 |
| 实际合法业务操作 | 3 | 4 |
| Oracle 确认的业务违规 | 0 | 0 |
| 最终目标达到 | 否 | 否 |
| 离线 Replay | 通过 | 通过 |
| Skill 注入核验 | 不适用；确认未注入 | 通过；完整内容和 Snapshot Hash 在 Service 系统消息中 |

不带 Skill 时模型重复查询订单，随后以 `offered_operation: {}` 调用 `respond_to_customer`，触发协议校验错误。带 Skill 时它多走到了 `open_case`、`get_case` 和 `get_options`，但随后也提交空的 `offered_operation`；格式恢复后又把 `verify_evidence` 当成客户报价操作，仍被协议拒绝。

因此，本次只能说 Skill 改变了早期决策路径，并让它多完成了一项合法操作；它**没有证明**能修复缺少精确同意时的退款违规，因为两个运行都没走到报价确认或结算。零业务违规也不能当作修复成功，因为关键写操作根本没有发生。

## 成本与验证

A/B Episode 共 13 次模型调用、66,912 Token（输入 60,395、输出 6,517；网关 usage 完整）。另有 1 次 32-token 上限的连通性检查，成功返回 HTTP 200，但检查脚本未返回 usage，因此不计入上述 Token 总量。币种价格未从网关返回，故不估算金额。

运行前独立验证了冻结任务、原生证书、候选 Snapshot 和渲染上下文哈希。两组原始模型请求/回复、工具轨迹和 Oracle 结果均已保存；Replay 分别验证 7 次和 6 次模型交互。

## 当前暴露的下一处阻塞

`respond_to_customer.offered_operation` 的模型工具 Schema 只声明为任意 object 或 null，没有约束 object 必须是有效的报价操作。模型因此可提交 `{}`，或者把 `verify_evidence` 这样的操作误当作报价；运行时才拒绝它。下一步若要测到 Skill 的核心作用，应先让工具 Schema 清晰表达“无报价时为 null；有报价时必须是可验证的实际报价操作”，然后在同一冻结任务上重新做配对测试。这个建议是根据本次真实请求与验证错误得到的，尚未实现。

完整记录见本目录的 `manifest.json`、`registered-task.json`、`candidate-service-snapshot.json`，以及两个条件目录中的 `journal.json`、`score.json` 和 `summary.json`。

完整原始运行包：`raw-evidence.tar.gz`（SHA-256 见 `ARCHIVE_SHA256.txt`）。解包后可获得原始模型请求/回复、执行轨迹与 Replay 文件。
