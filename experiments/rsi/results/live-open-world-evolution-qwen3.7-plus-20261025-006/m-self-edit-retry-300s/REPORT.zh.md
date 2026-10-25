# M 自修改 300 秒单次续跑

- 状态：`M_CANDIDATE_STAGED_NOT_SELECTED`。
- 来源：复用运行 `live-open-world-evolution-qwen3.7-plus-20261025-006` 的同一 M、冻结 World、真实 Service 基线/候选证据；公开上下文与原超时请求匹配：`True`。
- World hash：`8c3a18f2b241c269149ef4bc9cb6eba45c437319ae0c81c0e5eccbcb46133fd2`。
- 模型：`dashscope/qwen3.7-plus`；Provider 超时设为 300 秒。
- M 父版本：`e00f2f8ca806e3746c665c37a191e5c5a6b4313e3f51b55b52e64fcac46db08c`。
- 模型调用：1 次成功返回，10754 输入 + 6403 输出 Token，共 17157 Token；在 300 秒截止前返回。
- M 候选：`f5f045b4abf194ade9aaf54f38c24ddbf565fe1cc7b41d30a316f3751e99af6b`，源码 22753 bytes；通过现有静态接口检查，Host 归档校验通过。
- Host 结果：`NOOP`。候选已生成并归档，但因没有独立 M Probe，Host 保留父版本；候选未执行、未选中。
- 独立选代和参数训练：未运行。

模型请求/响应保存在 `model-calls.jsonl`；复用的公开研究上下文在 `public-context.json`；
候选程序和 Host 事件分别保存在 `programs/`、`research-archive/`。
