# After-sales Service Skill 配对评估

`aftersales_service_skill_ab.py` 是训练后的独立只读评估入口。它不运行 Designer Reflection、Service Reflection 或 Skill Gate；只加载已保存的 S0/S1 快照和 1–5 个 After-sales 验证集认证任务。

对每个认证任务及重复轮次，S0 与 S1 都从该任务登记的同一冻结世界重新开始。Customer 模型、Service 模型、Customer 协议、预算、工具、业务规则和显式选择的 Engine 模式保持一致。唯一允许改变的是 Service Skill Snapshot 及由此得到的检索/注入文本。S1 必须是 S0 的直接子快照，且恰好有一个 Skill 内容变化。每个条件都保存完整请求、模型响应、工具事件、Oracle、严格任务评分和离线 Replay。

配对评估要求任务来自 `validation` 分区，并要求通过 `--exclude-world` 登记已知训练世界。分区标签本身不证明数据独立：WorldSpec 的 partition 是元数据，使用相同 seed 时不同 partition 可能生成完全相同的世界。评估器会拒绝与训练世界共享精确 World Hash 或匿名结构签名的任务。任务参数可直接使用 `CertifiedTask` JSON，也可使用 Designer 执行 JSON（读取其中的 `task` 字段）；两者都会由原生编译器重新证明。此小规模开发诊断用于定位效果，不是动态验收 Gate，也不构成显著性或 Held-out 泛化结论。

模式必须明确选择：

- `reference`：Engine 拦截 Reference 判定为禁止的写操作，适合检查正常完成与正确拒绝。
- `sandbox`：错误写操作可改变隔离模拟状态，之后由不变的 Oracle 判定，适合观察成功违规。

两种模式不会混在同一轮评估中；结果清单会冻结所选模式。正式进化入口仍默认 `reference`，可用 `--mode sandbox` 显式运行错误发现任务。

真实运行示例（运行前需配置客户/服务模型及本地凭证）：

```bash
python -m experiments.vast_coevo.examples.aftersales_service_skill_ab \
  --task artifacts/validation/task-01.json \
  --task artifacts/validation/task-02.json \
  --task artifacts/validation/task-03.json \
  --exclude-world artifacts/pilot/world/frozen_world.json \
  --s0 artifacts/pilot/libraries/service/initial.json \
  --s1 artifacts/pilot/libraries/service/snapshots/<S1-SNAPSHOT-HASH>.json \
  --mode sandbox \
  --repeats 3 \
  --max-model-calls 256 \
  --output artifacts/paired/aftersales-s0-s1-001
```

以上默认最多运行 18 个 Episode（3 个任务 × 3 次重复 × 2 个 Skill 条件），全局模型调用上限为 256；达到预算后，未启动的条件会明确记录为 `NOT_RUN_GLOBAL_BUDGET`，不会自动重试。输出目录若已存在，运行会拒绝覆盖。

配对指标至少应同时查看严格任务成功、最终业务目标、正常结束、Oracle 成功违规、错误拒绝、被拦截的非法尝试、Skill 实际注入、Replay 与两侧模型调用成本。业务目标达成但对话未以 `customer_finished` 结束，或任一预算超限，都不算严格任务成功。
