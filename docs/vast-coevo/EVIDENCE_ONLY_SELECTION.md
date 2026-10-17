# Evidence-only static selection

新建 Frozen-World 训练默认采用 `training_selection_protocol = explicit-selection-v2`，并冻结：

```yaml
designer_quality_scoring: false
designer_dynamic_gate: false
service_dynamic_gate: false
```

这三个开关控制实际调用路径，不只是报告显示。Designer 动态 Gate 如需恢复，必须同时显式启用质量评分。恢复前应先建立可比较的固定开发评估设计。

## 默认执行链

独立生成并冻结 World Pool → 原生 Reference 证明任务 → 固定 Customer 与 Service 多轮执行 → Oracle 与 Replay 核验 → Designer Reflection / Static Gate → Service Reflection / Static Gate → 保存并继承实际选中 Snapshot。

Designer 不修改世界初态。Customer 不参与进化。合法任务、正确拒绝、成功违规、错误拒绝、未授权操作、未触发及不确定结果仍是逐题事实，不是能力评分。

## 关闭的路径

- 不调用 Designer `compare()`、Bootstrap、置信区间或发现收益阈值。
- 不执行新旧 Designer 配对挑战，不要求新根因或更高检出率。
- 默认报告不调用 `summarize()` 输出综合质量或单位成本发现评分。
- 不调用 Service DynamicGate，也不额外执行父/候选 Discovery、失败回归、合法完成或拒绝验收 Episode。
- 关闭动态模式附带的 Reflection 正常任务预执行；已经完成的训练 Episode 仍按原证据输入 Reflector。

旧评分模块、原 Service Gate 和独立 Benchmark 没有删除。显式恢复开关可沿用旧路径；这不构成推荐的实验设计。

## 保留的约束与证据

保留 Skill Schema、Patch action、父版本、Scope、工具/实体限制、静态安全检查、内容哈希、不可变发布和开发/Held-out 分区隔离。Service Reflection 前仍独立 Replay 输入证据。

Designer 接收真实训练 Trial 的提案、Reference 预期、逐题发现事实、构造错误及实际成本；原始对话、模型请求/输出、Skill 注入、工具操作、Oracle 结果和证明保存在档案中。Service 接收已完成训练 Episode 的事件、失败、任务判定、消息，以及适用时独立核验的 TaskDecision。没有新造错误标签或修改 Oracle。

成功更新的含义仅是：有效 Patch 通过静态检查并完成 Snapshot 发布。每代记录：

- `selection_mode = evidence_only_static`
- `performance_validated = false`
- `skill_updated = true/false`
- `performance_improved = unknown`

NOOP、无效输出、Reflection 传输错误或静态拒绝都保留父版本。没有性能回滚，也不能声称新版本更好或更安全。世界、执行、档案等完整性错误仍阻断运行；它们不是性能拒绝。

## Replay 与历史解释

Manifest 冻结三个开关及选代协议。Replay 使用相同模式重放 Reflection、静态验证、Patch、Snapshot 和跨代继承，不补跑已关闭的动态测试，也不发起在线模型请求。

历史 `designer-service-v1` 保持原默认动态语义。旧 Frozen-World **归档 Manifest** 若缺少选代协议字段，读取为 `legacy-dynamic-v1`、三开关开启；新建 FrozenPlan 缺省采用新模式。精确历史 Replay 仍需历史源代码快照，不能将旧结果重标为新协议。

示例：[frozen-cloudops-plan.json](../../experiments/vast_coevo/examples/frozen-cloudops-plan.json)。运行、审计和 Replay 命令沿用 [Frozen-World 说明](FROZEN_TASK_DISCOVERY.md)。历史审计和实验结果均未重写。

## 代码入口

- `integrations/usami/designer/controller.py::designer_update/run`：Designer 静态继承、模式与事实报告。
- `vast_coevo/evolution/evolvers.py::Evolver.update`：可选 `dynamic_gate=False`；旧调用缺省仍开启动态 Gate。
- `integrations/usami/designer/replay.py::verify_selections`：依据冻结开关复算继承；`frozen/controller.py::archived_plan` 解释历史配置。

本次仅做离线测试，不开展真实付费 LLM 或 Held-out 实验。软件机制闭环不等于实际模型性能改善。

## 实际验证（2026-10-17）

- 阶段性定向回归 92 项通过；最终补充后的 8 项定向检查通过。
- 最终全量回归 **1044 项通过，489.17 秒**。
- 全量收集后补充的不同世界/任务跨代测试另行执行，**1 项通过，10.55 秒**；当前 1045 个测试均已覆盖。
- 测试将 `compare()`、`summarize()` 和 `DynamicGate` 替换为调用即报错，默认两代训练仍完成，双方静态继承、实际 Skill 注入及离线 Replay 通过。
- 两代最小 fixture 共 18 次脚本模型调用，无 Gate 或 Reflection 预执行任务调用；这不是在线 LLM 消耗统计。
- 静态非法、无效模型输出、传输错误、NOOP、构造失败、旧动态 Gate 恢复、记录 Schema、固定 Customer 和历史配置解释均已覆盖。
- 日志保存在 `experiments/vast_coevo/results/evidence-only-static-validation-001/`。没有运行真实收费 LLM 或 Held-out。
- `git diff --check` 通过；原生业务规则、Oracle、旧评分与 Gate 算法未修改。
