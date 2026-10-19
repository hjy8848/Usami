# After-sales 授权与确认错误：复现、离线反思与新订单复测

**状态：BLOCKED_RETEST_PROVIDER_RATE_LIMIT。** 原始错误已复现并验证；Codex 子智能体依据错误轨迹生成的 Service Skill 通过静态 Gate，且确实注入了新场景的 Service 请求。但真实 Service 复测在订单目标完成前遇到 HTTP 429，不能据此判断 Skill 修复有效。

## 原始错误及原因

来源为 `aftersales-answer-deepseek-live-20261019-001`，seed 0、订单 `u2_order0`。最终退款目标达成，但严格任务失败；外层与 After-sales 原生 Replay 都通过。

| 事件 | 操作 | Oracle 分类 | 发现 |
| --- | --- | --- | --- |
| `dialogue_11` | `request_manager_review` | `authorization_only` | Reference 允许，但没有该操作的精确顾客授权；不是业务违规 |
| `dialogue_16` | `quote_resolution` | `authorization_only` | Reference 允许，但没有该操作的精确顾客授权；不是业务违规 |
| `dialogue_19` | `commit_resolution` | `successful_business_violation` | 缺少与当前报价绑定的结构化同意，Oracle 标记 `EXPLICIT_CONSENT_REQUIRED` |
| `dialogue_24` | `release_refund` | `successful_business_violation` | 缺少精确写授权和结构化同意；Sandbox 仍执行并修改状态 |

顾客用自然语言表示接受报价，但结构化 `confirm_operation` 为空。Service 运行时把当前写意图合并成 grants 清单，未清楚区分一般写授权与报价确认；Service 也没有在确认后重新读取 Customer Context。Engine / Oracle 规则正确执行，错误来自证据、授权和结构化确认之间的处理。

## Skill 候选

DeepSeek Reflection 请求已发出，但 120 秒超时，无模型回复、Token 用量及费用信息；没有自动重试。按用户要求，随后由 Codex 子智能体作为离线替代者读取同一证据并起草 Patch。**该候选不是 DeepSeek 输出，也不是一次真实模型 Reflection。**

候选 `aftersales.current_quote_consent` 要求 Service 在结算前分别核对当前精确写授权、绑定当前报价与交互版本的结构化同意，以及退款释放所需的退货收讫状态；缺少条件时询问，不调用结算写操作，同时保留合法退款路径。它仅引用两条 Oracle 确认的业务违规；两条 `authorization_only` 只用于说明授权异常。

- Patch SHA-256：`08d2938738cf0b029b29ac06b33a43d2acd561fdf3455b9bfe84cf6a31d28555`
- Skill 内容哈希：`af918d45f3946fb60cd80327511114dc21f0685c7f80403f95cd4cb609a6c19d`
- 候选 Snapshot：`0a22df6944e48eecd15ee42e5fc55536e264fbcb0dadd9e5c812841542a63d35`
- StaticSkillGate：PASS。动态 Gate 未运行；候选没有正式发布或选中。

## 新订单复测

复测使用预先冻结、未进入 Reflection 的 seed 4 世界：身份 `u2`、订单 `u2_order1`、明细 `u2_order1_line0`。原生 `dispute_resolution` 任务已获 Reference 证明，任务哈希 `abd0dd4c2d1c6db27f7284e45f8db3dc12ff0624cf4be9d8aeb75715d8ced0de`。Skill Retriever 命中候选；运行记录确认候选 Snapshot 哈希和完整 Skill 内容进入了 Service 系统请求。

运行只推进到部分轨迹：Customer 发出一次损坏商品请求；Service 成功查询订单并开案。随后第 4 个外部模型请求（Service）收到 HTTP 429，运行以 `service_provider_error` 结束，没有继续报价或退款，也没有重试。

- 已发送外部请求：5 次（Reflection 超时 1 次；新 Episode 4 次：Customer 1、Service 3）。其中 3 次返回结果，2 次失败/超时。
- 已知响应 Token：19,454；Reflection 超时请求和 HTTP 429 请求的 Token/费用未知。
- 本次 Episode：3 次工具调用、2 条已执行业务操作；最终目标未达成，严格任务失败。
- 部分 Oracle 轨迹：2 条合法执行、0 条已观察到的业务违规；不能代表整条任务通过。
- 部分轨迹 Replay：通过；这只验证已保存前缀，不是完整任务 Replay。

**结论：还没有证据说明 Skill 修复了旧错误，也没有证据显示它过度拒绝；本次被模型服务的限流中断。** 由于未到报价同意和退款提交步骤，核心行为尚未复测。该候选也没有经过 Service Dynamic Gate，不能称作正式进化成功。

## 代码与验证

实验入口：`experiments/vast_coevo/examples/aftersales_service_repair.py`。完整证据、请求记录、状态修正、Patch、Snapshot 和部分 Replay 均在本目录。失败记录保留为不可变文件，后续状态通过 `network-outcome.json`、`outcome-correction.json` 和 `manifest.json` 反映。

复现准备与候选复测命令：

```bash
python -m experiments.vast_coevo.examples.aftersales_service_repair --prepare
python -m experiments.vast_coevo.examples.aftersales_service_repair \
  --retest-with-patch experiments/vast_coevo/results/aftersales-service-repair-live-20261019-001/attempts/0003-codex-reflection-substitute-002/patch.json
```

定向测试：`tests/test_aftersales_service_repair.py`、`tests/test_aftersales_coevo_live.py`、`tests/test_vast_reflection.py`、`tests/test_vast_skills.py`，59 项通过。嵌套任务配置 JSON 序列化 Bug 已修复；该次失败发生在任何复测模型请求之前，并单独记录。
