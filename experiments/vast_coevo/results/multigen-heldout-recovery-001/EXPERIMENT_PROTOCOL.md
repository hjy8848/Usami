# 故障隔离修复后的续跑协议

Manifest: c49e8282d517ccb08a18ce21ae7a8f28a45af84ee0a6b9686606321ce2f75411

父实验 /Users/spring/RSI/Usami/experiments/vast_coevo/results/multigen-heldout-small-001 全部记录保留，原 Manifest 不变。此次由用户“修复吧”授权，续用相同模型、Prompt、2 代、1 次重复、12 个陌生世界 / 72 场 Held-out，并发上限 4。

只将已收到完整回复、真实 Replay 通过的 CUSTOMER_OUTPUT_INVALID 视为 Episode 局部失败。保留原回复、消耗、失败标签及统计分母；不修补输出、不重试该 Episode。其余安全、证据、预算、未知调用与 Service 错误仍按原逻辑阻断。Service Reflection、Static/Dynamic Gate 不变。

A 两代全部复用；B 已完成操作复用，从未执行步骤继续。跳过已完成 Smoke。继承 388 次 / 2448150 Token；本轮累计硬上限仍为 1000 万，历史更早 961580 Token 另计。Held-out 桶从 300 万增至 400 万以预留上下文波动，仍受同一个 1000 万总上限约束；训练两臂上限不变。不能称为原 v2 协议无故障完成。

测试题、证书、业务世界、身份、工具、评分与 Bootstrap 定义不变；单次独立训练重复只支持探索性结论。先完成训练、冻结最终服务，再解封 Held-out。
