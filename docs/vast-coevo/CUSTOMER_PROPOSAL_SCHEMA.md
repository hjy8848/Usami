# Customer 提案条件约束与真实历史复测

Core 1.0.3 将原来只在解析后执行的动作约束同步到 JSON Schema。持久化 SkillPatch 仍为 v1，字段、默认值、hash 和历史判定不变。

| 动作 | 工具 Schema 的约束 |
| --- | --- |
| ADD / UPDATE | 必须包含非 null 的完整 skill；Customer 使用 exploration，Service 使用 decision；id、type、trigger 和对应四组非空步骤必须齐全 |
| REMOVE | 必须包含非 null skill_id；skill 必须省略或为 null |
| NOOP | skill、skill_id 必须省略或为 null |

实现位于 `vast_coevo/skills/models.py` 的条件 Schema 与 `vast_coevo/reflection/scope.py` 的角色专属工具 Schema。Trigger 至少提供非空 keywords 或 intents。Scope/domains 继续由程序生成或继承，content_hash 由程序计算；没有要求模型填写路由元数据。

Schema 让模型在生成提案时获得准确的结构合同；解析、版本、引用、hash、授权边界和静态检查继续验收实际提交。不同 OpenAI-compatible 网关不一定提供严格约束解码，因此 Schema 不保证任意模型永不生成非法输出。一次调用、一次 Patch、无自动重试保持不变；不从 reasoning_content 或 rationale 补造缺失 skill，不放宽规则或 Oracle。

## 本次真实结果

`customer-schema-history-001` 使用与上一轮 `customer-goal-history-001` **完全相同的 ReflectionInput、两条 messages 和 ModelSpec**。唯一不同的请求字段是 `tools` 中的 Schema。源证据仍为 `cloudops-live-002`，先用历史固定源码离线核验 8 个 Episodes、54 次 Agent 请求和完整 Controller 判定。

模型 `dashscope/qwen3.6-plus`，temperature 0，max_tokens 4096，timeout 90 秒，最多一次真实调用。凭证仅在运行时从本机 Keychain 读取。

| 比较项 | 上轮目标修正 | 本轮 Schema 修正 |
| --- | --- | --- |
| 模型提交 | ADD，有 rationale，无 skill | UPDATE，完整 exploration skill，version 2 |
| 结构解析 | ADD requires one skill | 通过 |
| JSON Schema 校验 | 旧 Schema 放行缺 skill 的 ADD | 新 Schema 拒绝旧输出、接受本次完整输出 |
| 静态候选检查 | 未进入 | 全部通过 |
| completion tokens | 912 | 1518 |
| 调用 / 自动重试 | 1 / 0 | 1 / 0 |
| 动态 Gate / 正式选中 | 未执行 | 未执行 |

模型完整写出了资源引用识别、RESOURCE_NOT_FOUND 恢复、操作前置条件与项目状态变化的测试假设、探针、反馈分支和停止条件；UPDATE 继承原策略的四领域范围，CloudOps 历史证据不代表验证了其他领域。原始参数中的 p2/bill2 只在 rationale 引用观察，Skill 探针使用通用资源关系。

本次证明该模型在这一次同历史复测中交付了可解析、静态合法的经验。**没有证明探索收益、泛化或共进化成功，也没有更新选中的 Library。** 语义状态保持 requires_experiment_review；条件变化尚是待检验假设，权限和暂停条件并未因文字生成而得到实证。

原始提交、完整输入/请求/响应、Schema、解析结果、模型用量与来源核验见 [记录目录](../../experiments/vast_coevo/results/customer-schema-history-001) 和 [对照报告](../../experiments/vast_coevo/results/CUSTOMER_SCHEMA_COMPARISON.json)。旧输出与旧失败保持原样。新调用时的 151 个源码模块与记录保存在 [回放包](../../experiments/vast_coevo/results/customer-schema-comparison-bundle.tar.gz)，manifest 明确注明基准 commit 和当时未提交的源码改动，实际模块 hash 为回放依据。

## 运行与验收

新的真实调用需要独立目录，命令最多调用一次，不会继续重试本次 Run：

```bash
export USAMI_LLM_KEYCHAIN_SERVICE=litellm
export USAMI_LLM_KEYCHAIN_ACCOUNT=litellm-api-key
python experiments/vast_coevo/examples/compare_customer_reflection.py \
  --run-id unique-schema-run --out outputs/unique-schema-run \
  --purpose customer_proposal_schema_comparison
```

无需凭证的源码固定回放：

```bash
python experiments/vast_coevo/examples/replay_customer_reflection.py \
  --bundle experiments/vast_coevo/results/customer-schema-comparison-bundle.tar.gz
```

新增测试直接使用 Draft 2020-12 JSON Schema 校验器验证实际工具参数，覆盖 ADD/UPDATE 缺失或 null skill、缺字段/步骤、空 trigger、角色类型错配、REMOVE/NOOP 的冲突载荷、wire 与持久化 scope 差异，以及上一轮真实非法输出。jsonschema 只加入开发依赖；独立 Core 运行依赖仍只有 Pydantic。

全量回归 **850 passed in 226.08s**（新增 10 项测试）。固定源码回放核验全部 151 个模块，重新生成的请求与完整 ReflectionRecord 一致，在线调用 0。独立 Core 1.0.3 wheel 构建及隔离导入通过，运行依赖保持只有 Pydantic。四领域 Engine、Reference Rules、Oracle、动态 Gate 阈值与冻结 Benchmark 均无修改。
