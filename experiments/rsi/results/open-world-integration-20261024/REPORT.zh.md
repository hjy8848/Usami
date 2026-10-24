# EXECUTED · Benchmark 开放能力接入 RSI

基线：`feature/rsi-core-v01` / `26235b3`。本次集中于环境接入；RSI Core、P/K/M/φ、奖励、选代、Service RL 和聚合反馈契约未修改。

## 实际接入

正式入口 `integrations/rsi_usami/open_world.py::run_open_period()` 每周期从持久化 `WorldPopulation` 获取新的采样槽与冻结 World，并把认证回调和公开目录注入原有 `run_period()`。原来的固定 smoke 保留。

World 生成复用 `DistributionSpec`、`sample_schedule()`、`ScenarioDraft`、`build_world()`、`verify_build()`。原 `design_and_certify()` 的 World 阶段被提取为可单独复用的 `design_world_slot()`，原有 Task 阶段行为保留。

抽象挑战直接继承 `TaskDraft`，目标继续使用 `RemedyDraft`。新增内容只包括商品行筛选条件及 same/different-order 关系。Grounder 可返回多个同一 Customer 范围内的合法绑定，以声明的 seed 和候选哈希确定顺序；逐一复用原 `compile_task()`、Reference 认证及证书复算，选择第一项获证候选。完整候选和尝试均归档，不强制全局唯一匹配。

认证任务动态注册到现有 NativePackageVerifier 和 UsamiAdapter，进入原生 `PROPOSE_CHALLENGE → RUN_BASELINE → PROBE`。Customer、Service、Engine、Oracle、Episode 和 Replay 均使用现有实现。旧 `usami_benchmark` 的业务 Schema 和 Grounder 没有被修改或混入 v2 World。

## 确定性接口验证

- 实际执行两个 RSI 周期，每周期生成 3 个 World；每周期 3 个不同结构签名。
- 结构签名排除名字、ID、seed，记录 Customer/订单/商品行/SKU-family 拓扑、仓库、数量、退货条件及库存可用性。另有测试确认单纯换 seed 或商品 family 名称不会增加结构数。
- 挑战覆盖单对象退款、双对象退款与补发组合，并测试了跨订单关系和多候选绑定。
- 36 条原生 Episode 实际运行；业务目标均达成，安全检查均 PASS，36 条 Replay 全部通过；包含 7 个实际执行的 World。
- 这些运行使用明确标记的确定性 World 提案、研究模型和公开工具 Service 策略，证明接口接入。没有真实模型学习、参数更新或效果提升结论。

本机完整原始目录：`outputs/rsi-open-world-integration-20261024/`。`summary.json` 登记每条 Episode 的 SHA-256；52 MB 原始日志留在本机，未重复加入 Git。可用下方零 API 命令重新执行。

## 真实模型验证：与夹具结果分开

使用 LiteLLM `dashscope/qwen3.7-plus` 完成真实出题调用；成功提案“损坏设备退款”经过抽象筛选、真实冻结对象绑定、原生 Task 编译和独立 Reference 认证，随后在新进程中离线复算通过。原始输入、工具参数、响应和失败记录都保留。

另外，原有真实 World Designer 通过同一正式 WorldPopulation 接口生成了两个 SAT World，结构签名不同，均通过原生构造复算：

| World | Customer | 订单 | 商品行 | SKU | 仓库 |
|---|---:|---:|---:|---:|---:|
| 1 | 2 | 3 | 5 | 4 | 3 |
| 2 | 2 | 3 | 5 | 5 | 2 |

这些新 World 上的额外挑战调用逐项保留原生拒绝，包括未配置退货事件、公开商品描述存在歧义、遗漏字段以及未通过原有公开请求语义校验。没有修改业务目标或放宽验证来接受它们。逐调用最终状态、用量与证据索引见 `summary.json`；真实 Designer 的成功认证与确定性完整 RSI 执行分别统计。

此处的真实模型验证没有启动在线 Service、Reflection 或 RL。原生认证只声明其实际证明范围，不把 business reachability 当作自然对话成功。

## 来源隔离与失败策略

- 训练接入拒绝 validation/heldout WorldPopulation；恢复历史时校验分布、split、ScenarioSpec 来源和预注册采样槽。
- 新探索 World 不得与已注册独立任务的 World 来源重合。独立选择/奖励/测试任务仍由原有 Core Registry 管理，不进入 Designer 世界目录。
- Designer 目录提供聚合业务事实与原生认证能力声明，不含私有实体 ID、绑定表、Reference 见证或独立测试结果。运行反馈继续使用既有协议允许的聚合指标。
- Schema 失败、无匹配、截断搜索、编译拒绝、Reference UNSAT/UNKNOWN 和 Provider 失败都保留记录。API 没有自动重试；显式纠错只返回已记录的公开 Schema/编译契约反馈，不返回私有答案。
- 新增可选分支用于原生筛选字段、明确的预算边界、已授权训练证据、以及原生退货/审批事件能力；未增加静默模型替换、答案补写或默认成功路径。

## 验证与复跑

47 项相关既有测试、8 项新增集成测试通过，共 55 个不同测试。范围包含 Builder、Designer、Task Certification、Native Adapter、Package Verifier、原固定 RSI smoke、v0.2 Core 与新开放接入。另已实际运行下方两周期命令，并对记录进行离线验证。

```sh
PYTHONPATH=. python -m experiments.rsi.examples.open_world_usami period \
  --factory experiments.rsi.fixtures.open_world_validation:context \
  --output outputs/open-interface-check --periods 2 --world-count 3

python -m pytest tests/test_rsi_open_world.py -q

PYTHONPATH=. python -m experiments.rsi.examples.verify_open_world_results \
  experiments/rsi/results/open-world-integration-20261024 \
  --binding experiments.rsi.fixtures.open_world_validation:customer_binding
```

最后一条命令读取此次提交的小型真实模型证据包，复算 World、模型原始结构化输出、Grounder 与 Reference 证书；不访问网络。完整 RSI Episode 的 Engine/Oracle/Replay 由第一条命令及对应自动化测试验证。

正式研究配置使用同一 `run_open_period()` 或 CLI factory 入口，配置原生 World Designer、Host/模型、独立任务集和 Customer binding；不存在固定退款请求白名单。每周期的新 World、选中快照和原生 Episode 都有可追溯记录。接口与命令详见 `integrations/rsi_usami/README.md`。
