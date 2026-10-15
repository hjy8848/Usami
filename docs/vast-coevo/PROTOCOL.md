# VAST-CoEvo 提案与验证协议 v2

这份协议约定：模型可以修改什么、程序负责什么、什么证据才足以接受一次更新。它让实验把预算用于探索方法和业务决策，而不会因为模型重复填写系统元数据而无谓失败。协议同时保留失败、NOOP 和拒绝，避免只展示成功案例。

## 适用范围、实验范围与实际覆盖

| 字段 | 来源 | 含义 |
| --- | --- | --- |
| Skill 的 `scope.domains` | 初始库；UPDATE 继承父 Skill；ADD 从实验配置生成 | 检索策略时适用于哪些领域；不是授权或跨领域有效性证书 |
| Reflection 的 `domain_policy.add_domains` | 已固定的开发验证 Cases；独立 CLI 从 Plan 的 validation/regressions 读取 | 新增策略的默认领域；是配置，不是执行成绩 |
| Gate 的 `validated_domains` | 实际执行且通过独立 Replay 核验的父版与候选 Episode 的共同领域 | 哪些领域实际参与了比较；Gate 是否通过另看 `passed` |
| Evolution 的 `domain_coverage` | 程序结合规范化 Patch 和实际 Gate 结果计算 | 分别保存 `declared_domains`、`validated_domains`、`unvalidated_domains` |

例如四域通用策略在 CloudOps 实验中更新：

```json
{
  "declared_domains": ["saas", "cloudops", "fulfillment", "stayops"],
  "validated_domains": ["cloudops"],
  "unvalidated_domains": ["saas", "fulfillment", "stayops"]
}
```

这可以通过 CloudOps 的开发 Gate，但不能宣称通过其余三域测试，也不能证明泛化。`validated_domains` 表示执行过比较，不保证该比较通过；失败仍须读 Gate 的指标与理由。未进入动态 Gate 的 ADD/UPDATE，已验证领域为空。空验证集不能通过 Gate。

领域不会增加工具、改变 Customer 身份、生成写授权或选择另一个世界。每个 Episode 的世界、身份、工具和预算仍由固定 `EpisodeConfig` 和原生 Session 控制。`scope.tools` 是检索所需工具的约束，不是权限列表；所需工具不可用时不注入该策略。历史通用 `*` 可以继承，但有限实验不能把 `*` 标记为已全面验证；新 ADD 配置必须列举具体领域。

## 模型输出与程序补全

模型通过一次 `submit_skill_patch` 提交一个 ADD、UPDATE、REMOVE 或 NOOP。模型负责经验内容、触发条件、修改原因与开发证据引用。协议 v2 允许模型省略 `skill.scope` 或仅省略 `skill.scope.domains`，并建议省略程序计算的 `content_hash`。

- UPDATE：按 Skill ID 找到父策略，继承其 domains；省略 tools 时也继承原工具约束。模型仍提交完整的新经验内容，版本必须恰好增加 1。
- ADD：程序按实验中已配置的开发验证领域生成 domains；没有可信 DomainPolicy 则拒绝。省略 tools 时为空约束。
- REMOVE：只引用已有 Skill ID，记录删除原因。
- NOOP：明确没有足够依据改变经验，保持父版本。

兼容旧式完整输出：如果模型显式填写 domains，必须与程序决定的领域集合一致，列表顺序不改变范围。不同范围会拒绝，不能静默纠正。缩小、扩大或切换领域都不属于普通内容 UPDATE；需要另开具有相应验证 Cases 的实验与初始库。本协议没有新增范围修改动作。独立 Core 包版本为 1.0.1。

输出层的 Schema 是 `proposal_json_schema()`，规范化后仍生成完整的 `SkillPatch` / Skill / Library v1 对象。公开 Skill 的 domains 依然必填。ReflectionRecord 的 `proposal_protocol_version=2` 标记新提案协议，`scope_resolution` 记录领域来自 `parent_skill` 还是 `experiment_policy`。因此原始模型输出与最终可执行提案可分别审计；提供了错误 content hash 时仍然拒绝。

## 单次更新如何被验证

1. 固定模型、世界初态、Customer 身份、工具、预算及双角色 Library hash；用真实 Engine 运行交互。
2. 独立 Replay 核验开发证据。正式 held-out 证据不能进入 Reflection 或候选选择；隐藏 Oracle 不进入执行 Agent 请求。
3. Reflector 只调用一次模型、只允许一个 Patch，异常和格式错误不重试。Service 反思还包含实际正常任务预检，避免只学习如何拒绝。
4. 程序补全范围并检查 Schema、父版本、角色、版本号、工具、指令边界和具体资源标识；文本安全检查是启发式，实际权限由 Session/Engine 执行。
5. Customer 静态通过后，校验内容与版本发布冲突，直接选中新不可变 Snapshot；不进行配对性能验收。NOOP 不生成版本，静态失败保留旧版。记录 `customer_selection=customer-static-only-v1`、`static_gate_passed_snapshot_updated`；动态验证为空，不能声称能力提升或跨域验证。
6. Service 仍按相同开发 Cases 对照父版/候选，检查已知失败修复、新失败、正常任务完成、正确拒绝与授权。通过原动态 Gate 才发布；否则保留旧版。此阶段使用实际选中的 Customer。
7. Controller 按 Customer → Service 顺序交替，并保存父/新 Customer 与父/新 Service 的四组交叉执行。这些证据供研究分析，不对 Customer 作性能回滚。QGD 及工具事件评价仅通过显式诊断入口运行，其 ACCEPT / REJECT / INCONCLUSIVE 没有版本选择权。

运行选择协议单独版本化为 RunConfig v2；提案协议仍为 v2，Skill / Library / Reflection 保持原格式。历史 RunConfig v1 可读取、验 hash、离线 Replay；继续运行它必须使用原始源码。详见 [当前选择与诊断入口](CUSTOMER_STATIC_ONLY.md)。

调用前写不可变操作日志并预留预算，完成后保存实际成本。已完成步骤可恢复；外部结果不明的在途调用停止，避免无意重复实验。代码、配置、请求、轨迹与 Snapshot 的 hash 共同约束复现。

协议的意义是把“模型提出建议”“策略被选中”“业务真的执行”“Oracle 判定违规”“某些领域已验证”区分开。否则格式错误会被误解为探索能力不足，模型自述会被当成业务成功，单域成绩会被当成跨域泛化。

## 历史范围错误

旧静态 Gate 使用本轮验证 Cases 的领域集合，限制所有新策略声明，错误拒绝继承四域范围的 CloudOps UPDATE。现在 UPDATE 只检查是否继承父范围；新增 ADD 使用固定实验策略。

原始 Customer 提案完整保留四个领域，新增了资源 ID 查询失败后调整查询、计算操作前检查项目 Admin/Operator 角色的建议。它含有从 CloudOps 得到的领域具体经验，因此这次修复不会证明它在其他领域有效，也不会自动接受它。

原始文本见 [Customer UPDATE 提取](../../experiments/vast_coevo/results/CUSTOMER_UPDATE_SCOPE_AUDIT.json)。该文件包含原始模型 arguments、规范化 Patch、原始 record hash 和压缩包 SHA256；只是可读提取，不是新实验。旧 `LIVE_SUMMARY.json`、原始压缩包、Scope 错误判定均未更改。旧记录读取时不补写新字段，内容 hash 保持原值；完整历史重现仍使用压缩包中固定源码。新协议实验使用新 run ID 与当前源码，不混用历史在线调用。

实现：[提案范围补全](../../vast_coevo/reflection/scope.py)、[静态校验](../../vast_coevo/skills/validation.py)、[实际比较](../../vast_coevo/evolution/gates.py)、[演化流程](../../vast_coevo/evolution/evolvers.py)。
