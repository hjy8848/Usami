# 小规模 Customer–Service 多代实验报告

C2C 状态：**BLOCKED**。

本轮独立运行；历史中止记录保持不变。A 固定 C0，B Customer Reflection + Static Gate；Service 均沿用原 Reflection、静态和动态 Gate。基础模型和 Prompt 不变，最大并发 4，训练实际两条依赖链并行。

计划：A/B 各 2 代、各 1 次重复，12 个独立 Held-out 世界，每世界合法/拒绝各一题，共 72 场。源码提交：`0bccdc5d5d9d45c2c47684ae10c38af0aa5a884b`。
Manifest：`c49e8282d517ccb08a18ce21ae7a8f28a45af84ee0a6b9686606321ce2f75411`。

## 阻塞

ValueError: training incomplete; heldout remains sealed

## Customer/Service 版本选择

|运行|代际（从0计）|Agent|结果|原因|选中 Snapshot|
|---|---:|---|---|---|---|
|r0-A|0|customer|fixed|customer_updates_disabled_by_preregistered_ablation|`405e4a3acb6068b1815f546138f37b15d4d63a67516b823c1e5f1eb2698f856b`|
|r0-A|0|service|noop|explicit_noop|`6e42c560d19223634c454da907f314de209ec74e1459621913380f0930f65e4a`|
|r0-A|1|customer|fixed|customer_updates_disabled_by_preregistered_ablation|`405e4a3acb6068b1815f546138f37b15d4d63a67516b823c1e5f1eb2698f856b`|
|r0-A|1|service|noop|explicit_noop|`6e42c560d19223634c454da907f314de209ec74e1459621913380f0930f65e4a`|
|r0-B|0|customer|rejected|skill contains a concrete environment identifier: bill1; skill contains a concrete environment identifier: p0; skill contains a concrete environment identifier: p0_r0; skill contains a concrete environment identifier: p0_r1; skill contains a concrete environment identifier: p1; skill contains a concrete environment identifier: p1_r0; skill contains a concrete environment identifier: p2; skill contains a concrete environment identifier: p2_r2; skill contains a concrete environment identifier: p3; skill contains a concrete environment identifier: u2|`405e4a3acb6068b1815f546138f37b15d4d63a67516b823c1e5f1eb2698f856b`|
|r0-B|0|service|noop|explicit_noop|`6e42c560d19223634c454da907f314de209ec74e1459621913380f0930f65e4a`|
|r0-B|1|customer|accepted|static_gate_passed_snapshot_updated|`ec79ca36f4edb7dde32d0cbc0dbefd1ea43e8f5fcdabb551d8afec845efc1398`|
|r0-B|1|service|noop|explicit_noop|`6e42c560d19223634c454da907f314de209ec74e1459621913380f0930f65e4a`|
|smoke-A|0|customer|fixed|customer_updates_disabled_by_preregistered_ablation|`405e4a3acb6068b1815f546138f37b15d4d63a67516b823c1e5f1eb2698f856b`|
|smoke-A|0|service|rejected|known_failure_not_reproduced_in_baseline|`6e42c560d19223634c454da907f314de209ec74e1459621913380f0930f65e4a`|
|smoke-B|0|customer|accepted|static_gate_passed_snapshot_updated|`90821faea4cf4b0035f0255463d34826e9c53e8089f2a3424dc1fbc39ed67cff`|
|smoke-B|0|service|rejected|known_business_failure_not_repaired|`6e42c560d19223634c454da907f314de209ec74e1459621913380f0930f65e4a`|

Customer accepted 只表示静态检查通过并更新版本，不表示经过性能验证。Service accepted 才表示通过原有动态验收；Smoke 的候选不用于正式初始化。

## Held-out 结果

完整 Held-out 结果尚未形成；已保存进度 0/72。无完整结果不计算胜率，不伪造剩余实验。

## 12 个独立世界（固定环境，不给 Customer 隐藏题目）

|世界|种子|合法任务结构|拒绝边界|状态 Hash|
|---|---:|---|---|---|
|heldout-0|202610190000|legal_0|DEPENDENCY_NOT_RUNNING|`e74f4069d535c186dbde27605f6d83da11d068b69144e12f6f6970155bb76fd0`|
|heldout-1|202610190001|legal_1|QUOTA_EXCEEDED|`edd3fc35bbf9c95bbfafdccbb888924a9396c84cd730be8ae4eb7b8c7f623111`|
|heldout-2|202610190002|legal_2|INVOICE_NOT_PAID|`cf00ab4c99016e665094e269ebc641b0dcbc6972d64da59c82e85ebaa0443d52`|
|heldout-3|202610190003|legal_3|PERMISSION_DENIED|`9bfd2e56931bed7950e3d66ed6d8a23a516ec954b6be2629ad7c9203be8aefa3`|
|heldout-4|202610190004|legal_0|PROJECT_ACCESS_REQUIRED|`f47b711439c861ee8b296b97efb2f2f5ef34ff3290510656504281cc7a130169`|
|heldout-5|202610190005|legal_1|PROJECT_SUSPENDED|`9d673ff61629bed7c7f7b7ca428b683462901fb82e951d6684b0bc6b1dab92cf`|
|heldout-6|202610190006|legal_2|DEPENDENCY_NOT_RUNNING|`1169da2b2f6bc25b76d4b003e8f1b0f9d19dc377c47a0943d73f8f46e7add37b`|
|heldout-7|202610190007|legal_3|QUOTA_EXCEEDED|`5a8bf0b406d64dd4b2f95621b94b4c6bf2614ec4867795d34c30d86f0c8cd1c8`|
|heldout-8|202610190008|legal_0|INVOICE_NOT_PAID|`40e4e17ca77022b5c4a0a0a07f1ccd16539ea1eb0b551e483883097cb38d3e0d`|
|heldout-9|202610190009|legal_1|PERMISSION_DENIED|`049e51187eb9315c4d5f595ce26d0ebf1264923eb8d0ab9f150809f7fc1b678d`|
|heldout-10|202610190010|legal_2|PROJECT_ACCESS_REQUIRED|`d4dc5ea69553dc294f9bd885ed087b6ba0378fba570483fdfd0148a2a02c69ad`|
|heldout-11|202610190011|legal_3|PROJECT_SUSPENDED|`ed1f0b4df62e57231c0a67de4f9bdcdda56fd5ddc3f144ed02e020c76306ddbc`|

每个世界包含原生合法构造的权限、账单、状态、配额与依赖配置，完整初态在 worlds/ 与 MANIFEST。训练/开发/Smoke/Held-out 不同业务结构；Held-out 不进入任何 Reflection 或 Gate。

## 真实调用成本

|角色|调用|输入 Token|输出 Token|合计 Token|
|---|---:|---:|---:|---:|
|customer|68|332,379|94,006|426,385|
|service|384|2,187,634|85,634|2,273,268|
|reflection_customer|3|41,260|5,585|46,845|
|reflection_service|6|184,833|7,174|192,007|

本轮合计 461 次 / 2,938,505 Token；已知历史另计 145 次 / 961,580 Token；累计 606 次 / 3,900,085 Token。用量来自供应商 usage，不能用 Controller 预留预算冒充实际消费。货币网关账单未知。

## Replay 与测试

REPLAY_AUDIT.json：`{"heldout_rows": 0, "manifest_hash": "c49e8282d517ccb08a18ce21ae7a8f28a45af84ee0a6b9686606321ce2f75411", "online_calls": 0, "reflection_calls_reproduced": 9, "replayed_episodes": 64, "service_gates_reproduced": 2, "source_pins_verified": true, "status": "PASS"}`

945 passed in 271.80s (0:04:31)

修复前全量 945 项测试通过；原始请求、响应、模型配置、Skill 注入、工具行为、Oracle、原始 Snapshot 和源码在 raw-evidence.tar.gz。部分中止 Episode 若缺少完整 trace 必须标记 partial，不得算完整 Replay。

本次没有修改 Service 的学习方法、Gate、业务规则或 Oracle，没有自动重试，没有用 Held-out 结果调整候选。

## Role-grouped call ordering boundary

This intermediate recovery retains BLOCKED. B completed generation 0 and all generation 1 Episodes, but the initial isolation guard inspected the last globally listed call. Native calls are grouped by Agent, so a second-turn invalid Customer response can precede older Service calls in that list. The corrected guard selects the last Customer call and requires all model outcomes to be known. No failed Episode is retried. All 64 complete traces and 9 Reflection calls reproduce; all 461 wire calls match evidence. Held-out remains unopened. This intermediate state is preserved before continuation.
