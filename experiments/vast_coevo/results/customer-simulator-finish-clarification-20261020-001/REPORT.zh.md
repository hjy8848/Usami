# Customer 授权与结束冲突修复 Smoke

日期：2026-10-20
协议：`business-dialogue-task-agents-v3-finish-clarification-v1`

## 结果

使用同一冻结 After-sales 世界、真实 GLM-5.2 Customer、温度 0 和本地受控 Service fixture；每次最多 12 次 Customer 调用。没有调用远端 Service 模型，也没有自动重试。

| 运行 | Customer 调用 / Token | 业务结果 | Oracle / Replay | 说明 |
|---|---:|---|---|---|
| `finish-fix-001` | 8 / 66,205 | 未完成；未释放退款 | Oracle pass；Replay pass | 同一通用格式恢复额度先被无效偏好输出消耗，授权+结束冲突随后被拦截，但没有机会澄清。 |
| `finish-fix-002` | 9 / 87,258 | 退款完成；执行 `release_refund` | Oracle pass；Replay pass | Harness 单独请求澄清；Customer 以 `finish=false` 重申授权，Service fixture 随后执行退款释放。 |

第二次运行的 8 项业务操作均为合法执行，Oracle 违规数为 0。固定世界哈希、任务哈希和 Customer 场景哈希详见 `SUMMARY.json`。定向回归 `tests/test_scenario_customer.py tests/test_vnext_dialogue_agents_v3.py`：**33 passed**；独立离线 Replay：**verified，0 次在线调用**。完整原始模型请求、回复与执行记录保留在本机 `outputs/` 对应目录；本报告保存其文件 SHA-256 与字节数，原始目录被 Git 忽略，因此没有将大型原始 JSON 提交到仓库。

## 实现变化

- 新增协议版本 `business-dialogue-task-agents-v3-finish-clarification-v1`。旧 `business-dialogue-task-agents-v3` 执行仍按旧语义重放，避免改写历史证据。
- 新协议在确认退款或提交写授权与 `finish=true` 同时出现时，在 Session 变更前拒绝该轮，并给 Customer 一次独立、有限的澄清机会。该机会消耗 Customer 模型调用预算，但不占用普通格式恢复额度；重复矛盾时安全终止。
- 单纯结束、拒绝报价后结束等无待执行授权的既有行为保持不变。

## 解释边界

这是控制流协议的单场景 Smoke，不是 Skill A/B，也不能证明 Customer 或 Service 的模型能力提升。第二次运行完成退款，但 Customer Fidelity 仍为 `fail`：模型最初确实同时提出授权和结束，随后才根据 Harness 澄清改正。业务闭环成功与模拟顾客每轮都符合协议是两项独立判定。
