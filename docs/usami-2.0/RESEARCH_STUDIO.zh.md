# Usami 2.0 Research Studio

Research Studio 是本地的人工研究工作台，复用 Usami 2.0 的 Designer、Builder、Task Certification、Human Customer Runner、Oracle、Replay、ServiceReflector 和 Skill Snapshot。它不发布正式 Skill，不修改 Reference/Engine/Oracle，也不把人工 Episode 自动送入 Benchmark 或训练集。

## 启动

在仓库根目录：

```bash
python -m pip install -e '.[dev]'
cd web/frontend
npm ci
npm run build
cd ../..
PYTHONPATH=. python -m uvicorn web.backend.app:app --host 127.0.0.1 --port 5173
```

打开 `http://127.0.0.1:5173/?mode=research`。后端复用 Human Customer Playground 现有模型配置；密钥只由 Python 后端读取。浏览器的模型配置检查只返回模型名和是否配置，不返回凭据。若使用 Vite 开发服务器，启动 `npm run dev` 并按 `vite.config.ts` 将 API 代理至 FastAPI。

## 实际流程

1. **Designer**：显式点击“Designer 自主生成并认证”才发起真实模型请求。保存两阶段请求/回复、分布、Seed、预算与每次原生验证反馈。
2. **冻结世界与任务**：原生 Builder 构造世界；世界不变量、TaskSpecV2 和原生 Reference 证书独立复核。业务可达性不等于自然对话可达性。隐藏目标和 witness 只展示在本机研究者页面，不进入 Service 请求。
3. **人工 Service Episode**：Research Studio 将已认证的冻结任务注册到现有 Human Customer Playground；每次运行克隆场景，用真实 Service 模型、现有 Engine、Oracle 和 Replay。用户明确接受/拒绝报价仍由 CustomerRuntime 验证。
4. **诊断与人工标注**：时间线逐项展示原模型请求、工具操作/结果、Oracle 分类和状态哈希。研究者标注单独保存，明确不计入 Oracle 错误、不进入 Reflection。
5. **Reflection**：只有用户明确选择、分区为 `train`、原生 Replay 新鲜通过的 S0 Episode 才能进入一次真实 ServiceReflector。适配器保留真实公开请求、模型上下文、工具参数、返回结果与 Oracle 事件；不把隐藏目标或 Reference witness 加入证据。NOOP 是有效结果。
6. **候选 Skill**：Patch 通过 `StaticSkillGate` 后生成不可变、内容寻址 Snapshot，以 `publish=false` 保存，不覆盖正式 Library。静态合法不等于能力改善或正式接受。
7. **S0/S1 sanity check**：相同冻结任务分别启动真人 S0 和 S1 Episode。S0 不加载候选；S1 只在真实 Service 请求中检索命中后注入 Renderer 内容。请求、注入文本、Snapshot、工具集、模型信息和 Token 被记录。由于真人后续回应可能不同，这只作定性 sanity check；比较状态保持 `INCONCLUSIVE`，直到有独立任务及预先冻结的正式动态验收协议。

`validation` 和 `heldout` 运行可以生成、保存、查看，但不能进入此工作台的 Reflection。人工 Episode 固定标记为 `customer_source=human`、`study_type=qualitative_manual_pilot`、`benchmark_eligible=false` 和 `training_evidence_eligible=false`。显式选作 Reflection 只授权这一次候选学习用途，不提升证据等级。

## 数据与边界

- 默认研究记录：`research_records/<run_id>/current.json` 与哈希链 `journal.jsonl`；候选 Snapshot 保存于 `research_records/libraries/`。目录权限为当前用户私有，内容哈希和事件链在加载时核验。导出使用界面中的“导出完整研究包”。
- Human Episode 沿用 `human_records/<session_id>/episode.json` 与 `manifest.json`，原生 Replay 在进入研究档案或 Reflection 前重新运行。
- Research Studio API 只接受 localhost 请求并校验本地 Origin；耗时 Designer/Reflector 在受控后台线程运行，并发上限为 2。
- 当前没有自动 Customer Simulator、配对自动 Customer、独立新任务的正式动态 Gate、自动 ACCEPT 或候选回滚结论。不能将一个任务的复测称为泛化或 RSI 成功。
- Designer 和 Reflector 的真实 API 调用会产生费用；页面保存服务实际报告的调用与 Token。失败请求不自动重试，用户可显式创建另一条新运行。

## 验证

Research Studio 的离线测试覆盖：真实原生 Designer/Builder/Task 既有回归、Human Runner/Oracle/Replay、证据 Adapter、历史记录及 sidecar 哈希链完整性、held-out 隔离、S1 Skill 注入请求可观察性、S0 请求与工具未改变、共享本地会话 Cookie。Playwright 只验证工作台加载和离线导航，不发起真实模型请求。真实模型结果必须单独登记，不能由脚本替身测试代替。
