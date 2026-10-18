# InferAI DeepSeek v4.1 Flash：有界真实联调

状态：**BLOCKED，0/3 主 Service 任务**。

在代码基线 `472a6dd` 上，使用账号当前模型列表确认的准确 ID `deepseek-v4.1-flash`，端点 `https://inferaiapi.com/v1`。凭据读取既有 InferAI Keychain 条目，未写入记录。一次无工具 JSON 探针成功后，实际运行原有三任务入口，不改业务世界、Reference、Engine、Oracle、Skill、编译器或提示词。没有切换模型、隐藏重试或增加后备任务。

## 实际结果

- 连通探针：1 次调用，37 Token，约 3.45 秒，返回有效 JSON。
- 正式尝试：9 次调用，均为 Designer；4 次提交机会，其中 3 份完整结构化提案、1 次输出截断而没有提交工具。
- 有效证书 0；Customer/Service 主执行 0；Reflection 0；Skill 更新 0。没有完成真实共同进化。
- 正式调用消耗：输入 89,338、输出 6,413，合计 95,751 Token。加探针总计 **10 次调用，95,788 Token**，均有 usage。
- 原注册上限为 65 次正式模型调用；在有界 Designer 纠错预算耗尽后停止，没有消耗剩余预算重新开始。

## 四次提交的区别

1. 请求同一顾客三条商品明细全部退款。独立有界搜索未证明。
2. 缩为一条商品退款，并登记已有经理审批事件。仍未证明。
3. 模型输出达到 4096 Token 上限，没有完成工具提交，消耗一次提交机会。
4. 改为报价目标，但引用自己编造的 `quote_u0_order2_line0`；该报价不在冻结对象中，因而被拒绝。

离线原生 `eligibility` 审计确认：上述完整提案都围绕已超过售后期限的 `u0_order2` 商品。实际送达日期为 2025-12-01，世界时钟为 2026-01-15，商品售后期限已过。前两次编译反馈本身仅声称“有界搜索未证明”，并不等于完整不可达证明；这份过期判断是运行结束后的独立核对，未反馈给模型。最后一次自然语言错误声称仍在 30 天内，也没有改变真实世界。详见原始提案及 `offline-proposal-audit.json`。

## 接口行为

所有正式请求均配置 `thinking: {"type":"disabled"}`，但第 4 和第 8 次响应仍带 `reasoning_content`。第 8 次以 `finish_reason=length` 结束，无提交工具。因此只能确认请求已发送，不能宣称提供方始终遵守关闭思考或强制工具调用的要求。保留原始响应及 usage，不根据可见内容长度自行重算费用。

## 验证

- 相关测试：**35 passed in 103.06s**，见 `tests.log`。没有额外运行全量回归。
- 失败 Designer 会话精确离线 Replay：通过，复现全部 9 次记录及失败，新增在线调用 0。
- 实际源码快照 SHA256 与基线文件核验：全部一致。
- 没有 Service Episode，因此不存在 Service 执行回放；失败的出题记录回放不能表述为三任务闭环通过。
- 本轮只增加实验记录和报告；旧实验保持不变。不构成与 Qwen 的受控性能比较。

## 记录与复核

正式记录：`experiments/vast_coevo/results/aftersales-coevo-inferai-v41-001/`，包含模型请求/响应、冻结世界、初始 Skill、Designer journal、源码快照和离线核验。

从仓库根目录执行（零在线调用）：

```sh
.venv/bin/python experiments/vast_coevo/results/inferai-deepseek-v41-validation-001/verify_offline.py
```

结论：InferAI 的准确模型可用，实际自主出题已经尝试，但换用它没有让本轮通过原生任务证明。失败仍发生在出题阶段，尚未验证 Service 执行、双方反思或更新收益。
