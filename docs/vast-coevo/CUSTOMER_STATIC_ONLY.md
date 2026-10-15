# Customer Static-Only Selection v1

当前运行配置采用 `RunConfig.schema_version=2`，明确记录
`customer_selection="customer-static-only-v1"`。本机制只改变 Customer 的版本选择，不修改 Reflection 策略或评价公式，不代表 Customer 的能力已经提高。

## 选择与推进

1. 保留原有开发集隔离和独立 Replay 核验，固定模型、预算、身份及 Snapshot。
2. Customer Reflector 最多调用一次，生成一个 SkillPatch。协议异常保留原输出，拒绝更新；NOOP 保持旧版本。
3. 原 `StaticSkillGate` 检查 Schema、角色、父版本、版本递增、作用范围、工具、资源标识和现有安全限制。失败保留旧版。
4. 静态通过后，用原 `apply_patch` / `LibraryStore` 计算内容哈希、保存并发布不可变 Snapshot。内容损坏、版本发布冲突或存储失败仍会拒绝；这些不是性能判断。
5. 发布成功直接选中候选，记录 `static_gate_passed_snapshot_updated`。`dynamic_validation=null`，`domain_coverage.validated_domains=[]`；不冒充动态或跨域验证。
6. Controller 持久化该记录，再加载其 `selected_snapshot_hash`。Service Reflection、Service Gate、交叉执行和下一代均使用这一实际选中版本。

Customer 的 `valid_actions`、有效探针率、违规数、独立错误、覆盖、成本、Bootstrap 或 QGD ACCEPT/REJECT/INCONCLUSIVE 均不参与该流程，也不触发性能回滚。Controller 后续因预算、协议、证据或未知在途调用中止时，会保留已完成的版本选择；中止不是 Customer 性能回滚。

Service 的正常任务预检、一次 Reflection、静态 Gate、动态 Gate、已知错误复现与修复、合法任务/正确拒绝/授权检查、发布与回滚均保持原行为。

## 默认关闭的显式诊断

进化 `run` 不调用 Customer 性能 Gate，不生成用于其验收的父版/候选配对 Episode。原有探索、选中 Customer 的交互、Service 验证和四组交叉执行仍消耗各自预算；不把这些必要执行描述为零成本。

QGD v1/v2、Customer Probe Evaluator、发现归因、覆盖、协议错误、角色/时序成本和精确 Replay 均保留。Python 入口仍为 `DynamicGate(...).customer(...)`，返回的 `GateResult.passed` 与 QGD 三态仅是诊断判定。该对象不拥有 `LibraryStore` 或 Controller 的选择权。

显式 CLI 可运行配对诊断（会真实调用模型，最多每个 validation case 两个 Episode）：

```bash
python -m integrations.usami --root outputs/vast-diagnostics --plan PLAN.json \
  diagnose-customer --id diagnostic-001 \
  --baseline C0_HASH --candidate C1_HASH --service S0_HASH
```

三个 Snapshot 必须事先存在于该 root 的 `libraries` 中；诊断不发布候选。Plan 的 `policy.customer_quality` 指定 QGD 版本、阈值和独立世界排除项，省略时运行历史工具指标诊断。旧 `customer_gate_version` 字段保留用于解释历史策略配置，不再赋予其选择权。QGD 对配置、只读协议、独立世界和证据完整性的检查仍生效，不足或错误按原评价器报告。

诊断使用独立 `diagnostics/ID/` 的冻结配置和操作日志，与进化的 `runs/ID/` 隔离。先写 `manifest.json`，记录协议、源码哈希、固定三方 Snapshot 和配置哈希；后写不可覆盖的 `result.json`，包含判定、来源证据哈希、调用/工具消耗。原始模型请求/响应与可用 Token 用量保存在链接的 Episode Evidence / 原生轨迹中；QGD 报告保留分角色成本。失败写出错误、已完成成本和 pending 操作；pending 计入预算预留上界，不能冒充已知实际 Token。失败不改变任何选中 Snapshot，不静默重试；重复 ID 拒绝执行。诊断仍严格验证配置、内容哈希和 Replay，不把损坏证据当成有效结果。

已有证据可用 `experiments/vast_coevo/examples/replay_customer_quality.py` 离线重建 QGD 诊断；不会调用模型。

## 历史兼容

- 原实验目录、压缩包、选中结果和记录不修改，不利用旧 held-out 结果重新选择版本。
- RunConfig v1、旧 EvolutionRecord 和 StoredEvolution 仍可解析并保持原序列化与 hash；新可选字段在旧记录中不补写。
- 当前 Controller / CLI 拒绝继续执行 v1 run，防止同一冻结实验中途改变选择协议。历史执行须用原源码快照；历史原生精确 Replay 仍要求原源码 pin。
- 新 run 使用新 ID，在 Plan 显式设置 `"customer_selection": "customer-static-only-v1"`；示例 Plan 已更新。程序创建的 RunConfig v2 同样固定该标记。提案、Skill 和 Library 的格式未改变。
- Customer `accepted` 仅表示静态合格且完成版本更新；Service `accepted` 仍表示通过其动态验收。统计时必须区分，均不能直接当作显著泛化提升。

本次只运行离线测试和确定性 CI 响应，不开展真实 LLM 进化实验。
