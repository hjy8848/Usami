# After-sales Service Skill 配对评估（对话协议 v3）

`aftersales_service_skill_ab_v3.py` 是独立的只读评估入口，专门测量售后对话协议 v3 下的 Service Skill 差异。它与 v2 配对评估入口和历史结果分开编号、分开保存，不能把两种对话协议的数字合并。

每个 S0/S1 配对使用同一份通过原生编译器与证书验证的 validation 任务、冻结世界、Customer `UserScenario`、模型配置、预算、工具、Oracle 与显式 Engine 模式。Customer 可选择冻结的 `scenario-llm` 模拟器，或确定性本地 Customer 驱动；该选择会写入 Manifest，单次实验内保持固定。唯一研究变量是 Service Skill Snapshot。S1 必须是 S0 的直接子 Snapshot，且恰有一个 Skill 内容变化。

入口会保存 v3 完整执行、实际模型请求与回复、Customer Fidelity 诊断、独立 Oracle 结果、严格任务分数与 `replay_v3()` 回放结果。严格成功要求原生任务评分成功、状态为 `customer_finished` 且调用/工具/格式恢复预算合规。Customer Fidelity 中需要人工复核的自然语言项目只作诊断，不决定 Service Skill 成败。

任务必须属于 `validation` 分区，并通过 `--exclude-world` 提供已知训练世界。分区标签不是隔离证据；入口会同时排除精确 World Hash 和结构签名冲突。每个运行输出目录不可覆盖；模型调用有全局上限，不自动重试，不运行 Reflection、Gate 或 Skill 更新。

```bash
python -m experiments.vast_coevo.examples.aftersales_service_skill_ab_v3 \
  --task artifacts/validation/task-01.json \
  --task artifacts/validation/task-02.json \
  --exclude-world artifacts/pilot/world/frozen_world.json \
  --s0 artifacts/pilot/libraries/service/initial.json \
  --s1 artifacts/pilot/libraries/service/snapshots/<S1-SNAPSHOT-HASH>.json \
  --mode sandbox \
  --customer-mode scenario-llm \
  --repeats 3 \
  --max-model-calls 256 \
  --output artifacts/paired/aftersales-v3-s0-s1-001
```

用 `--customer-mode deterministic` 可在固定 Customer 决策下隔离 Service Skill 的影响；该驱动仍走 v3 授权、报价和业务执行流程，但 Customer 不产生在线模型调用。真实 Customer 模式使用独立 `USAMI_CUSTOMER_LLM_*` 配置。该小规模配对运行是开发诊断，不是动态 Gate、统计显著性或 Held-out 泛化证明。
