# Evidence-only static selection：离线验证

本目录是代码测试记录，不是真实模型进化实验。测试使用脚本化模型响应及真实 CloudOps Engine / Reference / Oracle / Replay。

- `targeted.log`：阶段性定向回归 92 项通过，195.32 秒。
- `final-focused.log`：最终补充后的 8 项定向验证通过，36.31 秒，包含静态继承、严格记录 Schema、无执行时保留 Service、完整 Replay 及恢复旧动态 Gate。
- 不修改旧实验结果，不运行真实收费模型或 Held-out。

机制与限制见 `docs/vast-coevo/EVIDENCE_ONLY_SELECTION.md`。Skill 更新仅表示静态接受，性能改善为 unknown。

`interrupted-before-schema-fix.log` 保留了一次为补齐记录 Schema 而主动中止的全量检查；该次不计为全量通过。最终全量结果另行保存。

`varied-worlds.log`：补充的不同冻结世界/任务实例跨代测试，1 项通过，10.55 秒。该测试在最终全量检查收集后加入，单独执行；不将 seed 差异冒充业务结构多样性。

最终全量回归：`PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q -x`，**1044 passed in 489.17s**，原始输出见 `full-regression.log`。另有收集后补充的 1 项不同世界任务测试通过；合计覆盖当前 1045 个测试。
