# After-sales v3：错误驱动 Skill Reflection 与配对诊断

**状态：EXECUTED（小规模开发诊断）**。12 个 Episode 均执行并通过独立 `replay_v3` 核验。结果没有证明候选 Skill 带来整体任务成功率提升。

## 实验设置

- 训练证据：使用冻结任务 `aftersales-v3-first-pair-live-20261020-001` 的 S0 真实轨迹。Oracle 确认 Service 成功执行了未经当前明确同意的 `release_refund`（`EXPLICIT_CONSENT_REQUIRED`、`UNAUTHORIZED_OPERATION`）；源轨迹在 Reflection 前重新 Replay。
- Reflection：Qwen3.7-Plus，temperature 0，单次调用、无自动重试。模型生成 `refund_settlement_authorization`，Static Skill Gate 通过。候选 Snapshot 哈希为 `2830d1c9bd035c36294914938514ef41b34746dd06453cee9ff0d17fc3de07a4`，父 S0 哈希为 `be7e66f910c2d0ec5143c7abfea8491fd9a1eb9cbc70a766c992436bebefb728`。没有运行 Dynamic Gate，也没有正式选中 S1。
- 评估：固定 Customer、Service 模型、温度、工具、预算和 Sandbox 语义；只改变 Service Snapshot。3 个冻结且经 Reference 认证的任务各重复 2 次，S0/S1 共 12 个 Episode。每个 Episode 最多 20 次 Service 模型调用、64 次工具调用；整个评估上限 240 次模型调用，串行执行。
- 世界在评估前固定：退款 seed `20261046`，换货 seed `20261047`，退款加重复申请拒绝 seed `20261048`。三者的 World Hash 与结构签名均不同，且排除了已消费的训练世界及之前诊断世界。

本次前的尝试也都保留了：`aftersales-v3-reflector-pilot-20261020-003` 因运行环境没有模型配置而在预注册前停止（0 次模型请求）；`aftersales-v3-reflector-pilot-20261020-005` 因预先指定的 profile ID 不存在而在任务准备时停止（0 次模型请求）；`aftersales-v3-reflector-pilot-20261020-004` 的 12 场执行虽完成，但事后审计确认候选 Skill 一次也没有被检索。它们没有被覆盖，也没有计入本次 12 场结果。

## 结果

| 指标 | S0：无新 Skill | S1：候选 Skill |
| --- | ---: | ---: |
| Episode | 6 | 6 |
| 严格任务成功 | 0/6 | 0/6 |
| 最终业务目标达成 | 4/6 | 3/6 |
| Oracle 确认的成功业务违规 | 4 | 2 |
| 仅授权违规（业务操作成功，但缺少本轮精确授权） | 4 | 6 |
| False rejection | 0 | 0 |
| 协议错误 Episode | 0 | 1 |
| 预算耗尽 Episode | 0 | 1 |
| 候选 Skill 实际注入 | 0/6（预期） | 4/6 |
| Service 模型调用 | 39 | 68 |
| Service Token | 164,930 | 374,415 |

S0 与 S1 的独立业务违规根因代码集合相同：`DELIVERY_DEADLINE_UNMET`、`EVIDENCE_REQUIRED`、`QUOTE_TERMS_INVALID`、`UNAUTHORIZED_OPERATION`。重复次数下降不代表发现了更少的根因类别。

逐任务配对结果：

| 任务 | Skill 是否检索 | S0：目标 / 业务违规 / 授权违规 | S1：目标 / 业务违规 / 授权违规 | 观察 |
| --- | --- | --- | --- | --- |
| 合法退款 | 是，2/2 | 0/2、2、0 | 1/2、0、3 | 目标业务违规消失，但 S1 仍有授权异常且没有严格成功 |
| 换货 | 否，0/2 | 2/2、2、0 | 1/2、2、1 | Skill 不适用；两组仍出现交付期限违规 |
| 退款并拒绝重复申请 | 是，2/2 | 2/2、0、4 | 1/2、0、2 | 两组都未通过预期的 `ALREADY_RESOLVED` 正确拒绝子目标；S1 有一次协议错误 |

候选确实进入了 4 个 S1 Episode 的每次 Service 请求，提示词内容与候选 Skill 一致；其余 2 个换货 Episode 没有触发候选 Skill。注入证据详见 `postrun-replay-audit-v2.json`。

逐条轨迹还显示一个关键差异：S1 的自然语言回复有时会说证据尚未验证、需要先验证，但工具轨迹仍在该 Customer 回合只授权 `verify_evidence` 时调用了 `request_manager_review` 或 `quote_resolution`。这说明“模型能复述规则”“Skill 已进入提示词”和“模型按规则选择工具”是三个不同事实。本次评估轨迹没有反馈给 Reflector，也没有据此修改候选。

## 解读与边界

这次有一个值得继续验证的局部信号：退款任务中，S0 两次均执行出带有证据/报价条件错误的 `quote_resolution`，S1 两次均未产生该类成功业务违规，其中一次达到最终退款状态。但 S1 在这些任务中还产生了 3 次授权违规，严格成功仍为 0/6；换货任务没有注入该 Skill，重复申请拒绝也没有成功。因此，不能把业务违规计数从 4 降到 2 解读成整体能力改善。

本轮只证明：真实 Reflector 能从经过 Oracle 和 Replay 验证的失败生成一份静态合法 Skill；检索器能在相关任务中选择它；Skill 确实进入真实模型请求；全过程可 Replay。它没有证明模型自主进化收益、Dynamic Gate 接受、泛化能力或完整严格任务成功。

## 成本与重现

- Reflection：1 次真实模型请求，18,700 输入 Token、2,051 输出 Token，共 20,751 Token。
- 配对评估：107 次真实 Service 请求，503,802 输入 Token、35,543 输出 Token，共 539,345 Token。
- 合计：108 次真实模型请求、560,096 Token。Customer 使用确定性脚本，无 Customer LLM 请求；所有模型调用均无自动重试。
- 预注册：`preregistration.json`；候选 Patch 与快照：`reflection/record.json`、`snapshots/S1-reflector-candidate.json`；执行记录：`evaluation/episodes/`；独立审计：`postrun-replay-audit-v2.json`。
- 离线复核命令：

```bash
PYTHONPATH=. python -m experiments.vast_coevo.examples.aftersales_v3_reflect_from_error audit
```

它逐场重新运行 v3 Replay，并检查候选 Skill 是否实际存在于 Service 请求中。
