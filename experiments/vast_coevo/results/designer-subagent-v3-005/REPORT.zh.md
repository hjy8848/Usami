# 离线子智能体 Designer 出题验证 v3-005

本次复用已归档 API Designer 上下文（未重新发送请求），让离线 Codex 子智能体在已观察到的资料和工具范围内重新设计一条挑战。它省略了可选确认字段，并直接使用顾客可请求的完整 `open_case` 操作。

编译器使用同一 After-sales seed 1 生成任务；Reference 证明该请求应被拒绝，Oracle 与 Replay 均通过。任务没有执行 Service，因此这是任务提案与证书验证，不是 Service 评测或共进化实验。

- 外部模型/API 调用：0；外部 Token：0。
- Customer / Service 执行：0。
- Reference 证明业务操作数：0。
- Oracle：pass；Replay：True。
- 原 API 对话来源：`experiments/vast_coevo/results/designer-subagent-v3-004/designer-context.json`，SHA-256 `ddc6d0e67b3a5d4504229dbfea41aae078673ac22bb1457881daeaa00d5e97e6`。
- Task hash：`82056f9aa710903dd17ebd244879bfbe4fddb9dfe482a1e25378f76ab6677a73`。

Agent 的一项早期候选把 `line_id` 放在 `quote_resolution` 的参数里；本机 Schema 正确指出其缺少 `case_id` 且 `line_id` 不允许。Agent 随后放弃该参数猜测，改用上下文中完整可见的 `open_case` 操作。公开规则说明也补充了开案本身受实际送达日和退货窗口约束；Reference/Engine/Oracle 未修改。
