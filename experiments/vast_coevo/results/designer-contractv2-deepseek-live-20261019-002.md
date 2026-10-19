# DeepSeek Designer 实时出题记录（contract-v2）

- 模型：`deepseek-v4.1-flash`，InferAI OpenAI-compatible API。
- 调用：1 次；输入 5,349 tokens，输出 2,451 tokens，总计 7,800 tokens；未设置输出 token 上限。
- 结果：提案通过结构校验，并在冻结的 3 个 After-sales 训练世界中找到匹配；4 个匹配均通过原生 Reference 证明。
- 挑战：针对已送达订单中的损坏商品，验证客服是否依次处理证据、审批、退货签收和原路退款等前置条件，最终完成退款目标。
- Replay：通过；重放 1 个模型响应、1 个提案和 4 份原生证书。Service 执行次数为 0。
- Run hash：`77ca46b614d68f7ee874a688c956c860888052f772d35f44431eaa638ac11166`
- Frozen index hash：`0f957b7c779095dbb7a8bb27f13686bfe2b1cf24282e4f2904a4bf001c1897fd`

完整请求、原始回复、冻结索引、证书、清单和 Replay 记录见同名 `.tar.gz`。解压后可在仓库根目录运行：

```sh
./.venv/bin/python -m usami_benchmark.designer_batch replay --run-dir <解压目录>
```

这是一次真实模型出题与本地任务证明记录；没有运行 Service，也不构成模型性能结论。
