# v0.1.0 协议与目标生成验收

执行日期 2026-10-13；基线 main 为
`0eb3fcf0447715817194f1c87a3e4488c5bdf141`。

## 实际执行

```bash
PYTHONPATH=. .venv/bin/python examples/benchmark/build_release.py
PYTHONPATH=. .venv/bin/python examples/benchmark/verify_release.py
.venv/bin/python -m pytest -q
```

完整测试：**251 passed in 31.22s**（原有 225 + 本轮 26 项）。

新增测试覆盖：可重复生成、匿名签名、至少两条真实因果路线、不同合法终态、
可选授权未执行不产生不完整请求、参考证据不进入 Service 消息、文本自称成功
不计分、错误顺序的真实拒绝、越域参数与写授权、身份/模型/预算篡改、配额
不足、结构留出、全 instance × trial 汇总与重复拒绝、Discovery 自主选择协议、
被拒绝尝试不计发现、真实 sandbox 违规、目标 Service 固定、frame、预算耗尽、
CLI 冻结/绑定模型/回放评分、未知能力域不可扩大。

实际冻结候选世界池：三个 Split 各 64 个 Seed，共 192 个世界。搜索直接执行
Reference Rules，无模型调用。冻结的 40 个 Service Task 都有至少两条合法且
包含真实状态依赖的路线：Train 16、Validation 8、Test Demo 16。配额、候选数、
结构/语义签名、Manifest/Data hash 全部保存在 coverage.json 与各 Manifest。

Train/Test Demo：**0 共享业务实例、0 共享结构、0 共享语义类**；Test 需要的
change_plan/change_seats 原子操作均已在 Train 出现。Validation 是明确的
同分布验证：2 个结构共有、3 个语义类共有、业务实例不同。这里验证的是
划分机制与证据，不是实际 LLM 泛化成绩。

已用离线 fixture 分别走每个任务的两条路线，共 **80 次**真实 Engine 执行、
原有 Oracle 和完整 Replay，全部成功。Oracle 使用独立固定顾客授权；未选的
可选写不会伪装为未完成的顾客请求。Discovery Demo 固定 2 个世界与各 3 个
trial，共 **6 次**协议回放；fixture 只选择 stop，不能解释成模型探索表现。
详细机器记录见 verification.json；完整执行痕迹在忽略的 outputs/benchmark-contract
中，可运行 verify_release.py 重建。

发布 JSON 用相同代码重建两次并核对逐字节 SHA256 一致。每个 Manifest
包含运行源码 SHA256，加载会检查源码、Generator/Rules/Agent/Goal/评分版本、
实例初态与完整实验 hash。模型设置按 profile 单独冻结；改变模型不改变
任务 dataset_hash，但改变完整 manifest_hash。

对比基线 Git blob：**25 个**既有核心及 Service/Customer/Interaction 源文件
逐字节未改动。旧 Scenario Generator、World Engine、Reference Rules、Oracle
与真实 Agent 语义保持；新增 Benchmark 的可选授权适配位于独立模块。

## 交付文件

- usami/benchmark：Goal 搜索/证据、版本化 Manifest、预算与结构配额、现有
  Agent 适配、独立回放评分、完整性汇总及 CLI。
- tests/test_benchmark.py：26 项协议、因果、授权与评分验证。
- benchmarks/v0.1.0：冻结 Train/Validation/Test Demo/Discovery Demo、覆盖数据、
  协议说明、验收与后续 P1→P2 方案。
- examples/benchmark：可编辑 freeze 配置、确定性构建脚本、明确标识的离线
  契约验证脚本；实际 CLI run 不运行证据路线。
- README.md 与 pyproject.toml：文档入口及 usami-benchmark 命令。

## 范围与局限

本轮实现协议和现有规则的 Goal Task 基础，不新增业务操作。当前有两种依赖
方向 × 两种角色，搜索限制为深度 4、512 节点、最多存 4 条解法；不是穷举所有
任务。不同终态或路线都按同一目标谓词接受，但有限操作域中的每个授权仅用
一次，未覆盖任意参数或无限重试。状态依赖证据可包含间接效应，不把信息
查询算作因果迁移。回复质量只检验达到正常完成边界，不作主观文本评分。

尚未实施真实 LLM 对这些冻结数据的全套评测，没有能力、方差或漏洞发现率
结论；也没有制造或发布盲测数据。公开 Test 始终为 Demo，私有测试由评测方
另行冻结与保存。下一阶段先 P1 成员生命周期，再 P2 支付/订阅激活，详见
NEXT_PHASE.md；这两项业务扩展仍未实现。
