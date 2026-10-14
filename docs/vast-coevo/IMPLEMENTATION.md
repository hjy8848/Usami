# VAST-CoEvo v1.0 — 实现与验收报告

## 1.0.2 Customer 经验方向修正（2026-10-14）

[方向修正与真实对照](CUSTOMER_GOAL.md) 已明确 Customer 的 Service 考察目标，在单次反思内加入五项自检，提供可审计的双方行为/工具结果/独立 Oracle 视图。旧 Skill/Snapshot/Patch、授权边界和收益阈值保持兼容。全量回归 **840 passed in 230.25s**，Core wheel 构建成功。

真实历史对照 `customer-goal-history-001` 使用同一模型与同一 `cloudops-live-002` 证据执行一次 Reflection：新理由面向 Service 资源识别、状态和权限测试，但模型遗漏完整 skill，未形成有效 Patch，未接受策略。完整经验产出标 **BLOCKED**，不能声称泛化或进化成功。原历史、上轮三次复测及本次反思均有固定源码与原响应的离线回放核验。原始材料见 [机器比较](../../experiments/vast_coevo/results/CUSTOMER_GOAL_COMPARISON.json)。

## 1.0.1 增量修复（2026-10-14）

[提案协议 v2](PROTOCOL.md) 将适用范围交由程序管理：UPDATE 继承父领域集合，ADD 使用固定实验领域；模型可省略该字段，等价列表顺序不视为范围变化。执行 Gate 单独记录实际覆盖与未验证领域，普通 UPDATE 不支持扩大或缩小范围。独立 CLI 已同步，原 Engine/Reference/Oracle、冻结 Manifest、网页及历史实验原件零修改。

最终全量回归 **824 passed in 245.39s**（原 804 + 新增 20），包含四域真实 Engine/Oracle 上通用范围的单域双 Evolver 比较。历史压缩包离线 Replay 核验 17 个 Episodes、112 次 Agent 请求及 3 份 Controller 报告，全部一致，在线调用 0；旧 scope 拒绝判定与 record hash 保留。完整 Customer 提案的可读提取见 [范围审计](../../experiments/vast_coevo/results/CUSTOMER_UPDATE_SCOPE_AUDIT.json)。Core 1.0.1 wheel 构建成功，新增范围补全模块仍不依赖 Usami 包。本轮没有新的在线候选接受证据。

下文是最初 v1.0 发布时的实现与验收记录。

[Roadmap](ROADMAP.md) · [方法](METHOD.md) · [架构](ARCHITECTURE.md) · [Schema](SCHEMAS.md) · [完整运行说明](../../experiments/vast_coevo/README.md)

## 工作区与 Git

工作区 **RSI**，仓库 `/Users/spring/RSI/Usami`，分支 `main`，基准提交 `d559bf1b10b93ad8eb29550a8f68fbd1534aa569`。用户明确要求跳过 RSI 连接器、直接执行；本地工作区身份已核对。算法导航已加入 README，历史 Benchmark Roadmap 保留原样。交付提交由包含本报告的 Git commit 标识，提交与同步结果在最终交付消息中报告。

`git diff --name-only d559bf1 -- usami usami_cloudops usami_fulfillment usami_stayops usami_harness benchmarks audits web` 输出为空：原业务包、Reference Rules、Oracle、冻结 Manifest、旧报告和网页代码零修改。原有 Benchmark 不要求安装 VAST-CoEvo。

## 实际实现

| 功能 | 实现与入口 | 验证 |
| --- | --- | --- |
| 独立协议与严格 Schema | `vast_coevo/models.py`、`protocols.py`、`schema.py` | Core 隔离导入、无领域依赖、版本/hash/参数校验 |
| 双 Agent Skills | `skills/models.py`：ExplorationSkill / DecisionSkill | Scope、Trigger、前后条件、探索/恢复字段、不可变内容 hash |
| Library / 版本 / 回滚 | `skills/library.py`：LibraryStore、apply_patch | ADD/UPDATE/REMOVE/NOOP；原子发布；候选与已发布版本分离；拒绝保留父版 |
| 检索、渲染与真实注入 | `skills/retriever.py`、`renderer.py`、`agents/runtime.py` | 从原请求的合法信息确定性检索；记录实际命中、base/wire 请求及返回；不变更工具与授权 |
| 双 Reflector | `reflection/reflector.py`：CustomerReflector / ServiceReflector | 单调用、单 Patch；格式错误、重复键、多候选和不可用证据拒绝，不重试 |
| 双 Evolver 与两级门槛 | `evolution/evolvers.py`、`gates.py`；静态门槛 `skills/validation.py` | 真 Adapter 执行；固定对手；已知失败、合法完成、正确拒绝、授权和新增违规检查 |
| 证据与保守去重 | `evidence/archive.py`、`signatures.py`；领域解析 `integrations/usami/evidence.py` | 保留六类原生判定；不确定因果前缀保留精确前态并标 pending；事件数与指纹数分开 |
| Controller / 多代 / 恢复 | `evolution/controller.py`、`storage/runs.py` | Customer-first、Service-second；四组实际版本交叉运行；21 项状态机测试 |
| 四域真实 Adapter | `integrations/usami/adapter.py`、`domains.py` | 真实 Session、Engine、规则、Oracle、任务目标/框架评分与 Replay |
| 可执行入口 | `python -m integrations.usami` / `usami-coevo` | Library、Episode、双角色 Reflection、单/多代、History、Restore、Replay |
| 独立安装与离线检查 | `pip install ./vast_coevo`；`python -m vast_coevo` | 26 模块的 wheel；唯一依赖 Pydantic；没有 Usami 模块 |

Evolver 在 Reflection 前通过 Adapter 重验输入证据；held-out 在反思输入与验证配置处硬拒绝。Service 单次 Reflection 同时看到真实正常任务预检查结果，而不仅看到攻击。候选验证采用预先配置的开发规则，接受不等于科学改进。

### Session 差异与兼容

SaaS Discovery 复用 InteractionSession；正常任务使用原 Benchmark 的 **GoalServiceSession**，其可选精确授权不会变成必须全部执行的请求。CloudOps 使用领域自有 InteractionSession；Fulfillment/StayOps 使用现有共享 harness。已知失败回归重用原 Customer 真实消息和精确一次性授权，不调用 Customer 模型，不从 Service 参数创造授权。

Replay 同时重建原 Session 的 base 请求与注入后的 wire 请求。原生 JSON 序列化顺序单独保留，避免排序后的 World 映射改变公开观察。SaaS Goal/延迟多轮以及共享 harness 的 Customer KeyboardInterrupt 路径，先严格重建原 Session，再调用原 World/Service/Oracle Replay；未改旧代码。

每次在线调用分别原子保存 `calls/*.started.json` 和 `*.completed.json`（真实请求、响应、注入记录）。未知 Episode 标记阻止再次执行。Controller 对 Episode/Reflection 另有输入 hash 与预算预留日志；已完成调用恢复时使用缓存并实际 Replay，未知结果停止。Run 的全局成本包含探索、正常任务、Reflection、动态验证和交叉运行。使用 Unix flock 控制同一 Run 并发。

## 实际测试结果

最终命令（仓库根目录）：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q
```

**804 passed in 225.99s**。原有 622 项与新增 182 项全部通过，未删除或弱化旧测试。

| 层 | 测试文件 | 实际覆盖 |
| --- | --- | --- |
| Core，共 130 项 | test_vast_skills/runtime/boundary/reflection/evolution/controller | Schema、全部 Patch、存储/hash、防篡改、检索/注入、格式异常、严格单次、拒绝/接受/NOOP、held-out、成本与恢复 |
| 四域 Adapter，共 40 项 | `test_vast_usami.py` | 双角色注入、多轮、合法/非法/授权异常、真实 Sandbox 违规、正常任务、错误模型输出、未知中断、精确 Replay、保守指纹 |
| CLI，共 8 项 | `test_vast_cli.py` | 实际 Plan 解析、离线无环境凭证 Replay、证据伪造拒绝、重复调用阻止、逐调用持久化 |
| 四域真实双 Evolver 门槛，共 4 项 | `test_vast_real_gates.py` | 实际 Customer 候选执行；Service 原失败复现/修复、合法完成与正确拒绝；真实 Engine/Oracle/目标/授权；已接受版本及 Replay |

Core Mock Adapter 仅用于通用算法单测。四域门槛测试的 LLM 是明确标注的确定性 CI fixture，业务状态、规则、Oracle 与评分全部真实；不能当作新的在线模型修复结果。Controller 测试覆盖两代、双方接受、拒绝回滚、NOOP、四个实际版本配对、缓存恢复、未知在途停止、预算上限、历史分支和完整性检查。

独立 wheel 通过现代 setuptools/wheel 构建：26 个 Python 模块全部位于 `vast_coevo`，依赖仅 `pydantic>=2.12,<3`。自动 AST 与隔离目录导入测试阻止 Core 引入领域包及 Integration。普通 Usami `.venv` 的旧构建工具不用于这个 wheel 检查，构建使用已有现代验证环境，没有更改运行依赖。

## 真实 LLM Pilot

2026-10-14，使用现有 LiteLLM 与 Keychain，模型 **dashscope/qwen3.6-plus**；固定 `temperature=0`、`max_tokens=4096`、timeout 90、trust_env=false。凭证仅运行时读取，没有输出或保存。最小网关 smoke：HTTP 200，3.8s，回复 OK。

CloudOps Seed 42、Customer `u0`、Sandbox；Discovery 固定 2 turns / 3 Customer calls / 6 Service calls / 8 tools；正常任务固定 14 Service calls / 24 tools；每个 Run 全局上限 300 LLM / 500 tools。正常任务是独立的 dependency_boot 与 viewer_refusal，后者固定自己的 `u3` 身份；不将任务或 Witness 给 Discovery。

| 实验 | 结果 | Customer / Service 更新 | 实际成本 |
| --- | --- | --- | --- |
| cloudops-live-001 | failed；1 个 Episode，未到 Reflection | 发现公开能力查询无法识别同世界不同身份的拒绝任务；修复后新 Run，保留原失败 | 1 Customer + 6 Service；6 tools |
| cloudops-live-002 | **completed；完整 1 代，8 Episodes** | Customer 真实 UPDATE 因超出当前验证领域拒绝；Service 真实 NOOP；选中旧版 | 10 Customer + 44 Service + 2 Reflection = **56 LLM**；**44 tools** |
| cloudops-scoped-live-001 | **completed；独立完整 1 代，8 Episodes** | 使用另行冻结的 CloudOps 专属 bootstrap；Customer 输出 UPDATE 缺完整 Skill，严格拒绝且未重试；Service 真实 NOOP | 8 Customer + 43 Service + 2 Reflection = **53 LLM**；**41 tools** |

两个完整 Run 均完成双边各一次实际 Reflection、真实 Skill 注入、正常任务预检查和四组交叉执行。两个 Run 的合法任务完成与正确拒绝都通过原评分。**没有在线候选被接受，没有声称 H1/H2/H3 或模型改进。** 拒绝与 NOOP 后的配对如实引用相同快照。

首次失败保留 7 个真实模型返回；两个完成 Run 保留 54 和 51 个 Agent 返回及各 2 个 Reflector 返回，总计 116 次实验调用（smoke 另 1 次）。无在线重复反思、无多候选搜索、没有用 fixture 填入 Live 结果。

### 完整证据与零在线回放

[机器摘要](../../experiments/vast_coevo/results/LIVE_SUMMARY.json)、[完整原始包](../../experiments/vast_coevo/results/live-pilot-bundle.tar.gz) 保存全部 Run、配置、Library、请求/响应、Patch/错误、Oracle、工具/状态轨迹、预算日志和对应的 149 模块源码版本。源码变更没有重写旧 Source Pin；初次失败与完成实验分别保留其实际源码。

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python   experiments/vast_coevo/examples/replay_live_bundle.py
```

实际结果：**17 个原生 Episode、112 个 Agent wire 请求、4 个已记录 Reflection、3 个完整 Controller 报告完全一致，在线调用 0**。历史 failed 报告也保持 failed，不伪装为完成。脚本仅重定位文件读取，保留原 JSON、Skill、Request、Trace hash，分别从固定源码子进程回放。

本地原始目录为 `outputs/vast-coevo/live-20261014*`；原始包 3,825,916 bytes，SHA256 `080810eddf3d390a412c5ab26f9981515b6caf599ab872b2abd451708ed460df`。API 费用未估算；报告实际调用与工具数。

## 1.0.3 Customer 提案 Schema 修正（2026-10-14）

ADD/UPDATE 在工具 Schema 中条件必填完整非 null Skill，REMOVE/NOOP 排除矛盾载荷，保留历史 v1 序列化与单次调用规则。同一 CloudOps 历史输入、提示词、模型和采样参数下，一次真实 Reflection 交付完整 UPDATE 并通过静态检查；未运行动态 Gate，未声称探索效果提升。详情与原始证据见 [Customer 提案协议复测](CUSTOMER_PROPOSAL_SCHEMA.md)。

## 当前限制与下一步研究

- 真实在线 Pilot 没有接受新 Skill；在线动态候选修复/接受尚无成功证据。动态接受机制已有四域真实 Engine + CI 模型响应验收。
- 未开展正式 held-out、跨领域泛化、预算匹配消融或统计显著性实验，H1/H2/H3 未证明；这不属于本次工程成功标准。
- 规范化是保守特征类型，不是完整语义唯一性。未经反事实验证的历史写前缀标 pending，不能当作必要因果依赖。
- 静态文本检查是启发式；真正授权仍由原 Session/Engine 控制。开发门槛采用明确的聚合指标，不替代正式研究协议。
- 通用 Run 使用绝对 artifact 路径；本次发布包提供跨路径只读映射回放，尚未提供任意新 Run 的通用打包 CLI。运行锁依赖 Unix flock。
- 已发布的同 ID/version 不允许不同内容覆盖；从旧版另开演化分支时应使用独立 LibraryStore 或新 ID，避免已有版本冲突。

代码已经具备下一阶段多代/跨代执行与 held-out Episode 接口。研究前最少补充冻结私有世界/组合留出、Model/Skill/预算匹配消融、多 Seed 与置信区间、协议有效率与在线候选接受率，持续维持正常任务/授权回归并隔离测试证据。
