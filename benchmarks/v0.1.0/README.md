# Usami Benchmark protocol release 0.1.0

这是首个冻结的 Goal Task 数据与双 Track 协议发布。协议细节和真实模型运行命令
见 [工具说明](../../usami/benchmark/README.md)。本发布的 ModelSettings 为明确
标识的离线 fixture 占位，不能把验收结果当作真实 Service/Customer 模型成绩；
用 `profile` 绑定真实模型后，任务 dataset_hash 保持不变，完整 manifest_hash 更新。

| Manifest | 世界候选池 | 固定实例 | 结构配额／用途 |
| --- | --- | --- | --- |
| service-train.json | Standard Seed 0–63 | 16 | seat_before_plan：owner 8、billing_admin 8 |
| service-validation.json | Standard Seed 1000000–1000063 | 8 | 同分布验证：owner 4、billing_admin 4 |
| service-test-demo.json | Standard Seed 2000000–2000063 | 16 | plan_before_seats：owner 8、billing_admin 8；公开 Demo |
| discovery-demo.json | test_composed Seed 3000000/3000001 | 2 × 3 trials | 固定 user_002 与模型/工具/四项预算；无目标或攻击脚本 |

Train 与 Test Demo 的世界业务实例、目标结构及语义签名均无重叠；两个原子
操作 change_plan、change_seats 在 Train 都出现。Test 留出的是依赖方向及目标
形式，不能据此声称已经证明真实 LLM 组合迁移。Validation 显式采用同分布
结构：结构重叠 100%，语义类共有 3，业务实例无重叠。详细候选数、hash 与
签名集合见 [coverage.json](coverage.json)。

全部 40 个 Service 任务有至少两条 Reference 验证的合法路线；终态按目标
谓词评分，不固定计划。每个实例都 Reset 到生成时固定初态，身份不变。角色
之间的权重由固定配额与宏平均控制，而非增加常见类别数量提高成绩。

Service 预算：1 个受信顾客输入、0 Customer LLM 调用、8 Service LLM 调用、
16 个 Service 工具调用，reference 模式。Discovery 预算：6 顾客轮次、8 顾客
模型调用、24 Service 模型调用、48 工具调用，sandbox 模式。工具集合、每次
模型请求上限与所有设置完整存入各 Manifest，不跨模式混报。

没有公开或伪装发布私有 Test。需要盲测的评测方另用未公布世界池生成
visibility=private 的 Manifest，先验证组合划分并承诺其 hash，再保存在
private/；不要直接把 Test Demo 换标签使用。一次完整评测必须覆盖 Manifest
所有 instance × trial，缺失则汇总主评分为 null。

重建与离线验收：

```bash
PYTHONPATH=. python examples/benchmark/build_release.py
PYTHONPATH=. python examples/benchmark/verify_release.py
python -m pytest -q
```

重建不会调用模型；搜索依据真实规则。`verify_release.py` **专门作为离线契约
fixture** 使用证据路线验证 Engine/Oracle/Replay；真实 CLI run 使用 Service LLM
自主工具决策，绝不运行此脚本或读取 witness 作为回答。验收结果见
[verification.json](verification.json) 和 [VERIFICATION.md](VERIFICATION.md)。

阶段边界：本轮不增加业务操作、改动旧 Rules/Engine/Oracle，也不修改既有
Service/Interaction 的运行语义。新 Benchmark 层为可选路径提供独立授权适配。
P1→P2 的后续建模、可验证依赖和验收条件见 [NEXT_PHASE.md](NEXT_PHASE.md)。
