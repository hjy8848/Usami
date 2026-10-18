# Designer 离线子智能体出题诊断：混合挑战

日期：2026-10-19

范围：只验证 After-sales Designer 的冻结世界探索、开放式任务提案和原生证明；不运行 Service、Customer 或 Skill Reflection。

## 输入与过程

将当前 `frozen-world-designer-exploration-v4` 的实际 system/user 消息、只读查询工具、强制提交工具 Schema、构造预算和冻结世界登记信息提供给 Codex 子智能体。请求上下文的模型标签是 `deepseek-v4.1-flash`，但这次没有调用 DeepSeek 或任何外部 API；子智能体通过本地只读查询接口自主调查并提案。

使用 After-sales seed 2，冻结世界哈希为 `f6c3ec9a4178972535bbb6f85d597a92d400bf5fad92cd48987b91311b79b482`。预算上限为 20 次查询、4 次提案（初次加最多 3 次修正）、4096 个 Reference 节点、深度 16。实际使用 15 次查询和 2 次提案。

第一次提案组合了一个创建开案目标和一个正确拒绝目标，但 bounded Reference search 未能证明该组合。系统没有替它改题或提供证明答案。子智能体根据可见反馈，改选同一顾客已观察到的另一条商品明细后再次提交。

## 成功提案

同一 Customer `u3` 的两个订单被组合成一个任务：

- 对已送达的 `u3_order1_line1` 创建并保持一个售后 Case。该商品明细未结案、处于售后期内、证据有效且商品可退。
- 对仍处于 `processing`、尚未实际送达的 `u3_order0_line0` 请求开案。独立规则要求 Service 拒绝该操作。

Designer 只给出了业务目标和对象引用，没有提供 Reference 答案、执行路径或创建对象 ID。原生编译器用冻结世界推导权限帧并搜索任务见证。独立重建结果为：创建目标通过、正确拒绝目标通过、Oracle `pass`、任务评分成功、Replay 通过；见证包含 4 个 Customer 交互轮次和 1 个业务操作。`verify_task` 从冻结 seed 重建证书后通过，世界、注册、请求哈希均与存档一致。

这证明在当前接口下，子智能体能够从只读世界信息中自主组成“合法完成 + 正确拒绝”的多对象挑战，且原生 Reference 能够证明它。它没有证明真实 DeepSeek 能力，也没有运行 Service，所以不能据此判断 Service 是否答对或共进化是否有效。

## 错误诊断改动

这次还补充了 v4 Designer 失败分类：结构/schema、对象不存在、范围、授权/确认、未注册外部事件、业务前置条件、Reference 未证明、模型输出协议、传输失败及验证器内部错误。失败反馈会区分“搜索预算内未证明”和“任务不可能”；预算耗尽时也会把最后的失败类别写入 journal。旧 v2/v3 的反馈分类和 Replay 分支保持原有语义。

此改动只改善诊断信息，不会自动修复提案、放宽权限、修改世界或调整 Reference/Oracle。

## 成本与边界

- 外部 API/LLM 调用：0
- Customer / Service 执行：0
- Reflection / Skill 更新：0
- 本地 Designer 子智能体尝试：15 次只读查询、2 次任务提案（不作为模型 API 调用或基准性能结果）

## 重放

在仓库根目录执行：

```bash
.venv/bin/python experiments/vast_coevo/examples/verify_designer_subagent_run.py experiments/vast_coevo/results/designer-subagent-v4-003
```

该脚本不调用模型；它从登记的 `WorldSpec` 重新生成并冻结世界，核对请求与世界哈希，重新编译保存的成功提案，调用 `verify_task` 并保存 `native-certified-task.json` 与 `independent-verification.json`。

## 自动化验证

执行命令：

```bash
.venv/bin/pytest -q tests/test_designer_exploration.py tests/test_vnext_open_compositions.py
```

结果：45 passed。覆盖当前 v4 失败分类、预算耗尽 journal、传输错误、Reference 未证明反馈，以及 v3 既有失败反馈和 Replay 兼容性。
