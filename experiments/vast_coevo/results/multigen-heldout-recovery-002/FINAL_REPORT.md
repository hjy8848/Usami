# Customer 协议错误隔离修复与多代实验续跑

**C2C：EXECUTED（修订协议续跑）。** A/B 各 2 代均完成，72/72 场 Held-out 完成；136 个完整 trace 精确 Replay 通过。原两次 BLOCKED 记录保留，没有改写成成功。

## 修复了什么

原实验将一次 Customer 动作格式错误升级为整条训练链失败。现在由实验入口显式选择 isolate-recorded-customer-output-v1：收到完整回复且 Replay 通过的 CUSTOMER_OUTPUT_INVALID 只结束该 Episode，保留失败标签、完整证据和预算消耗，继续后续步骤，不修补、不重试。
日志按 Agent 分组；检查采用最后一条 Customer 调用，而不是列表最后一项，并要求所有调用结果均已知且无传输错误。因此第二轮格式错误也能正确隔离。未知调用、完整性异常和 Service 错误仍按原逻辑阻断。
World、Engine、Reference Rules、Oracle、权限、Customer/Service Reflection、Skill Schema、Static Gate、Service Dynamic Gate 均未改动。历史严格停止协议仍可按归档源码解释。

## 修改文件与原因

- `experiments/vast_coevo/examples/episode_resilience.py`：小型 Controller 子类，仅隔离已记录的 Customer 输出错误。
- `experiments/vast_coevo/examples/recover_multigen.py`：新目录、版本化协议、原日志与成本继承、跳过已完成 Smoke，复用训练检查点。
- `experiments/vast_coevo/examples/multigen_heldout.py`：根据 Manifest 显式选择故障策略；复用相同最终评估函数，不改变评分。
- `tests/test_episode_resilience.py`：覆盖检查点恢复、三种主阶段、第二轮按角色分组的日志，以及未知/Service/Replay 错误仍阻断。
- `experiments/vast_coevo/examples/MULTIGEN_HELDOUT.md`：恢复入口、语义与兼容性说明。

## 恢复证据

父原始运行 multigen-heldout-small-001 已有 388 次调用；首次续跑增加 73 次，保留为 multigen-heldout-recovery-001。最终续跑继承 461 次已知结果。
A 的 117 次调用完全复用；B 已有 94 次也全部复用。最终两代完成检查点的推进使用 0 次新训练调用；只新增 381 次 Held-out 调用。四条 Customer 格式错误原样保留，全部可回放。
严格实验的停止规则经用户授权修订；这不是原方案无故障完成。父 Manifest、状态、源码和完整归档保留。模型、Prompt、世界、身份、工具、预算机会和评分不变；Held-out 阶段上限预留 400 万，仍受 1000 万累计总上限约束。

## 两代是否真的更新了 Agent

|组别|代际|Customer|Service|
|---|---:|---|---|
|A|1|fixed|noop|
|A|2|fixed|noop|
|B|1|rejected|noop|
|B|2|accepted|noop|

A 固定 C0。B 第 1 代 Customer 提案因具体环境 ID 被静态拒绝；第 2 代更新 customer.state_dependency 并正式静态选中。新经验探测依赖顺序、权限、暂停状态和配额，实际注入 4 次 Customer 请求，完整注入内容保存在 POLICY_RECOVERY_AUDIT.json。静态接受不等于性能改善。
四次正式 Service Reflection 输入各有 4 个 Episode，经独立证据核对均没有 VerifiedFailure 或成功业务违规，模型均返回 NOOP。因此没有 S1、没有正式 Service 动态接受；不能说 Service 已学会修复。两次完整 Service Gate 回放来自原 Smoke，其候选均被拒绝。

## Held-out 结果

|标签|场数|正确任务数|合法完成|正确拒绝|真实违规场数|未授权成功写场数|
|---|---:|---:|---:|---:|---:|---:|
|S0|24|17/24|12/12|5/12|7|0|
|A|24|15/24|12/12|3/12|9|0|
|B|24|14/24|12/12|2/12|10|0|

**三个标签使用完全相同的 Service Snapshot。** 以上是同一配置重复运行的表现波动，不能解释为 A/B 的学习差异或能力退化。相同 Skill 仍在陌生场景产生真实违规；合法业务完成良好，拒绝能力明显不足。
拒绝任务的失败和预算耗尽均保留在分母；真实违规由独立 Oracle 对实际成功写操作判定，不将查询失败或被 Engine 阻止的尝试当成漏洞。

## 12 个陌生世界

|世界|种子|合法任务结构|拒绝规则|初态 Hash|
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

完整状态、证书、模型和配额在 MANIFEST.json 与 worlds/，所有世界在正式运行前固定，六类拒绝边界各两个世界。未向 Customer 泄露测试答案，Held-out 不参加 Reflection/Gate。

## Snapshot

- C0：`405e4a3acb6068b1815f546138f37b15d4d63a67516b823c1e5f1eb2698f856b`。
- C_A_final：`405e4a3acb6068b1815f546138f37b15d4d63a67516b823c1e5f1eb2698f856b`。
- C_B_final：`ec79ca36f4edb7dde32d0cbc0dbefd1ea43e8f5fcdabb551d8afec845efc1398`。
- S0：`6e42c560d19223634c454da907f314de209ec74e1459621913380f0930f65e4a`。
- S_A_final：`6e42c560d19223634c454da907f314de209ec74e1459621913380f0930f65e4a`。
- S_B_final：`6e42c560d19223634c454da907f314de209ec74e1459621913380f0930f65e4a`。

## 成本：全部为原始供应商 usage

|角色|调用|输入 Token|输出 Token|总 Token|
|---|---:|---:|---:|---:|
|customer|68|332,379|94,006|426,385|
|reflection_customer|3|41,260|5,585|46,845|
|reflection_service|6|184,833|7,174|192,007|
|service|765|4,207,964|174,299|4,382,263|

本方案含父运行与续跑共 **842 次 / 5,047,500 Token**。本次修复后新增 **454 次 / 2,599,350 Token**；最终续跑仅新增 Held-out **381 次 / 2,108,995 Token**。更早首轮中止与连通检查另计 145 次 / 961580 Token，因此全部相关尝试累计 **987 次 / 6,009,080 Token**。没有将缓存调用重复计费。
模型始终 dashscope/qwen3.6-plus，temperature=0、max_tokens=4096、没有配置 provider seed。配置并发上限 4，Held-out 实际观察到 4 个并发请求。

## Replay、测试与局限

946 项全量测试通过（274.56 秒），相关测试和完整日志在本目录。136 个完整 trace、9 次 Reflection、2 个原 Smoke Service Gate 均复现，全部 72 行 Held-out 的评分与配对统计重算一致，所有 wire 调用与原生/Reflection 证据一一匹配；未知调用为 0。完整 trace 可复现不等于每场业务成功；预算终止和协议失败均未删除。
只有 1 次独立训练重复；世界配对 Bootstrap 区间条件于此次训练，不能证明训练稳定性。STATISTICAL_ANALYSIS.json 三组对比均标记同 Snapshot，收益支持结论均为 false。
目前证据支持的是错误隔离和无重复调用恢复有效；**没有证明 Service 进化或整个共进化算法有效**。本轮正式学习材料未提供经 Oracle 确认的错误，后续应先改善开发阶段探索覆盖，再使用新的独立测试世界，不能把本次 Held-out 回灌后重新选历史候选。

## 完整记录与复现

本目录 raw-evidence.tar.gz 包含本次及继承的 wire/native/evolution/source 日志；PARENT_EVIDENCE.tar.gz 单独保留父完整归档，避免嵌套重复压缩。继承的内容寻址 trace 路径保持原父路径，离线恢复时按 Manifest 中的 parent_root 保留/恢复父目录。
```bash
.venv/bin/python experiments/vast_coevo/examples/multigen_heldout.py replay --root experiments/vast_coevo/results/multigen-heldout-recovery-002
.venv/bin/python -m pytest -q tests/test_episode_resilience.py tests/test_multigen_heldout.py tests/test_vast_controller.py
```

执行源码提交：`2a4cfb0f93d6481d3c300c2fcf93064d828704e9`；Manifest：`0bb0fa295d975dd10e1aad207ea21759eb30e8cdbe5020555f2d3c7d724f8901`。结果本地提交见 Git 历史；未推送 GitHub。
