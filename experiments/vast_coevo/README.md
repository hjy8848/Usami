# VAST-CoEvo 实验入口

研究定义与验收见 [Roadmap](../../docs/vast-coevo/ROADMAP.md)、[方法](../../docs/vast-coevo/METHOD.md)、[架构](../../docs/vast-coevo/ARCHITECTURE.md)、[Schema](../../docs/vast-coevo/SCHEMAS.md) 和 [实现报告](../../docs/vast-coevo/IMPLEMENTATION.md)。以下命令从 Usami 仓库根目录执行。

## 安装与模型配置

Core 可以单独安装，依赖只有 Pydantic，不要求安装 Usami：

```bash
python -m pip install ./vast_coevo
```

运行 Usami 集成时安装原有可选模型客户端和测试依赖：

```bash
python -m pip install -e '.[service,dev]' -c constraints-tested.txt
```

真实执行沿用现有 `USAMI_LLM_MODEL`、`USAMI_LLM_BASE_URL`、`USAMI_LLM_OPTIONS` 配置。凭证由原客户端读取 `USAMI_LLM_API_KEY` / `OPENAI_API_KEY`，或 `USAMI_LLM_KEYCHAIN_SERVICE` 与 `USAMI_LLM_KEYCHAIN_ACCOUNT`；模型配置、Skill、报告不写入密钥。不需要修改 Keychain。

四个角色可以分别覆盖模型配置：`VAST_CUSTOMER_*`、`VAST_SERVICE_*`、`VAST_CUSTOMER_REFLECTOR_*`、`VAST_SERVICE_REFLECTOR_*`；支持后缀 `MODEL`、`BASE_URL`、`OPTIONS`、`TIMEOUT`、`TRUST_ENV`。也可在 Plan 中显式给出四份 `ModelSpec`。首次创建 Run 时将实际配置冻结；恢复运行采用持久化配置，改变环境变量或 `--generations` 不会改写已有 Run。需要另一模型或额外代数时创建明确的新 Run。

## 计划与初始 Skill Library

| Plan | 开放探索 | 正常任务回归 | 默认运行 |
| --- | --- | --- | --- |
| [cloudops-pilot.json](configs/cloudops-pilot.json) | Seed 42、固定身份 `u0`、一个 CloudOps Sandbox 世界 | dependency_boot 合法完成、viewer_refusal 正确拒绝 | 1 代；全局最多 300 LLM / 500 Tools |
| [cloudops-scoped-pilot.json](configs/cloudops-scoped-pilot.json) | 同一固定 CloudOps 世界、独立的 CloudOps 专属初始 Library | 同上；任务身份独立固定 | 1 代；不覆盖前一实验或重试其 Reflection |
| [four-domain-development.json](configs/four-domain-development.json) | 四域各一个开发世界；SaaS/Fulfillment/StayOps Reference、CloudOps Sandbox | 每域各一个合法完成和正确拒绝，共 8 个场景 | 2 代；全局最多 1,200 LLM / 2,000 Tools |

Discovery 只从权限过滤的世界观察开始，不使用正常任务目标或 Witness。正常任务回归是独立 track。开发 Plan 不是正式 Held-out 测试集，运行结果不能证明 H1/H2/H3。

两份 [Customer](examples/customer-library.json) / [Service](examples/service-library.json) 初始 Library 是人工审核的 bootstrap 数据，Schema 与 Snapshot hash 已封装；它们不是 Evolver 的预置候选结果。可以离线查看：

```bash
python -m json.tool experiments/vast_coevo/examples/customer-library.json
python -m json.tool experiments/vast_coevo/examples/service-library.json
```

第一次在线执行会将 Plan 引用的 Library 保存到 `--root/libraries`。每份候选由实际单次 Reflector 响应产生，再经过验证接受或拒绝。

提案协议 v2 由程序管理领域元数据：UPDATE 继承原领域、ADD 使用 Plan 配置的开发验证领域；模型可省略 `scope.domains`。实际覆盖由执行结果另行记录，四域通用策略在 CloudOps 更新不会被误拒，也不会因此获得其余三域的验证结论。详见 [协议设计与意义](../../docs/vast-coevo/PROTOCOL.md)。历史 Pilot 判定保持原样，完整原始 Customer 修改可读提取见 [范围审计](results/CUSTOMER_UPDATE_SCOPE_AUDIT.json)。新实验使用新的 run ID。

## 静态 Skill Episode 与离线 Replay

使用已经配置的真实模型网关运行一个新的 Episode ID，保存便于后续引用的通用 Evidence：

```bash
mkdir -p artifacts/vast-coevo
python -m integrations.usami --root artifacts/vast-coevo \
  --plan experiments/vast_coevo/configs/cloudops-pilot.json \
  episode --profile cloudops-dev --id static-cloudops-001 \
  > artifacts/vast-coevo/static-cloudops-001.evidence.json

python -m integrations.usami --root artifacts/vast-coevo library
python -m vast_coevo library --store artifacts/vast-coevo/libraries
```

检查具体 Snapshot 时给 `library` 加 `--hash`，使用输出中的实际 hash。Episode 同时检索并注入 Customer/Service Skills，运行真实 Session、Engine、Oracle，保存最终 wire request、raw response、工具轨迹和原生 Replay 记录；无匹配 Skill 时保留基础 Agent。

Replay 使用保存的响应重建交互，不请求在线模型，不需要模型环境变量、网络或凭证：

```bash
python -m integrations.usami --root artifacts/vast-coevo \
  --plan experiments/vast_coevo/configs/cloudops-pilot.json \
  replay --evidence artifacts/vast-coevo/static-cloudops-001.evidence.json

python -m vast_coevo evidence --store artifacts/vast-coevo/evidence
```

`--evidence` 接受 Evidence JSON 路径或 archive hash；Core `evidence` 可加 `--hash` 查看具体记录。集成 Replay 逐项校验源代码固定值、冻结配置、实际 Skills、注入后请求、原响应、真实状态与 Oracle。单纯 Core archive 检查不会取代原生 Replay。

## 单次 Reflection

Reflection 从 Plan 指定的当前 Library 和经原生回放核验的开发 Evidence 提出一个 Patch，不自动应用候选：

```bash
python -m integrations.usami --root artifacts/vast-coevo \
  --plan experiments/vast_coevo/configs/cloudops-pilot.json \
  reflect --role customer --generation 0 \
  --evidence artifacts/vast-coevo/static-cloudops-001.evidence.json \
  --output artifacts/vast-coevo/customer-reflection-001.json

python -m integrations.usami --root artifacts/vast-coevo \
  --plan experiments/vast_coevo/configs/cloudops-pilot.json \
  reflect --role service --generation 0 \
  --evidence artifacts/vast-coevo/static-cloudops-001.evidence.json \
  --output artifacts/vast-coevo/service-reflection-001.json
```

可以重复传入 `--evidence` 汇总多个真实 Episode。一次命令只有一次反思和一个 Patch；无依据时可以 NOOP。调用前写入 `OUTPUT.started.json`；输出或在途标记已存在时拒绝再次调用，未知中断不会自动重试。完整反思输入、请求、响应/错误和解析结果保存在输出中。Controller 才负责形成候选、静态/动态验证和接受/回滚。

## 单代、多代、历史与恢复

```bash
python -m integrations.usami --root artifacts/vast-coevo \
  --plan experiments/vast_coevo/configs/cloudops-pilot.json \
  run --id cloudops-coevo-001 --generations 1

python -m integrations.usami --root artifacts/vast-coevo-four-domain \
  --plan experiments/vast_coevo/configs/four-domain-development.json \
  run --id four-domain-coevo-001 --generations 2

python -m integrations.usami --root artifacts/vast-coevo history --id cloudops-coevo-001

python -m integrations.usami --root artifacts/vast-coevo \
  restore --source cloudops-coevo-001 --id cloudops-branch-001 \
  --generation 0 --generations 1

python -m integrations.usami --root artifacts/vast-coevo \
  --plan experiments/vast_coevo/configs/cloudops-pilot.json \
  run --id cloudops-branch-001
```

同一 Run ID 和同一 Plan 路径再次执行 `run` 会恢复已保存配置。已完成 Episode 与 Reflection 返回缓存结果并执行原生 Replay，不再次调用模型；已开始但结果未知的操作将运行标为 interrupted。Restore 从已完成 Generation 创建新 Run，保留原 Run 的历史与报告，不能把未知反思自动伪装成可重试步骤。配置预算无法预留下一操作时返回 budget_exhausted；非 completed 状态以退出码 2 报告。

每代记录当前探索、Customer 更新、选定 Customer 再探索、Service 正常任务预检查与更新、四组跨代执行。拒绝与 NOOP 时相邻代可以引用同一 Snapshot。全局预算包括全部探索、验证、正常任务、Reflection 和交叉执行；每个 Episode 先预留配置上限，完成后按实际调用计费，未知结果保留预留上限。

## Python API

```python
from pathlib import Path
from integrations.usami import UsamiAdapter, UsamiProfile
from vast_coevo.models import ModelSpec
from vast_coevo.skills.library import LibrarySnapshot

profile = UsamiProfile(config_id="cloudops-dev", domain="cloudops", seed=42,
                       identity="u0", mode="sandbox", split="dev")
# 使用已有 ModelSpec；示例中的变量由调用方配置。
adapter = UsamiAdapter(Path("artifacts/vast-coevo/native"), [profile])
config = adapter.config_for("cloudops-dev", customer_model, service_model)
customer = LibrarySnapshot.model_validate_json(
    Path("experiments/vast_coevo/examples/customer-library.json").read_text())
service = LibrarySnapshot.model_validate_json(
    Path("experiments/vast_coevo/examples/service-library.json").read_text())
evidence = adapter.run_episode(config, customer, service, "api-cloudops-001")
checked = adapter.replay(evidence, customer, service)
assert checked.verified
```

另一环境实现 `EnvironmentAdapter` 后可以直接使用 Core 的 `CustomerReflector`、`ServiceReflector`、`Evolver` 与 `CoEvolutionController`。Controller 构造参数是 Adapter、两份反思 CompletionClient、LibraryStore、EvidenceArchive、RunStore；`run(RunConfig)` 返回类型化 RunReport。Core 不创建 Usami World/Operation 对象。

## 保存布局与解释

```text
ROOT/
  libraries/       # 不可变 Skill 与 Library Snapshot；候选和接受版区分
  native/          # 实际 wire/native Trace、完整 Snapshot、源码固定值
  evidence/        # 通用 Oracle Evidence、分类与失败指纹
  runs/RUN_ID/
    config.json    # 冻结配置
    operations/    # started/completed；稳定操作 ID、输入 hash、实际成本
    evolution/     # 所有 Patch、请求、候选、验证和接受/拒绝/NOOP
    generations/   # 已完成代际和实际跨代版本
    report.json    # 当前状态、实际选中版本、成本和错误
    reports/       # 不可变历史报告
```

确定性 Core Tests 可以使用 Mock；真实四域 Engine Tests 可以使用录制模型响应，但它们都不是新的真实 LLM 实验。Pilot 是否完成、候选结果与完整证据路径以 [实现报告](../../docs/vast-coevo/IMPLEMENTATION.md) 为准。当前锁使用 Unix `flock`，部分未知因果失败按精确前态保守区分，通用 artifact 使用绝对本地路径；本次发布包提供不改写 hash 的只读重定位回放，任意新 Run 的通用打包 CLI 尚待提供。正式 Held-out 与统计显著性留待后续研究。


## 已保存的真实 Pilot

真实结果见 [机器摘要](results/LIVE_SUMMARY.json) 与 [验收报告](../../docs/vast-coevo/IMPLEMENTATION.md)。两轮完整真实运行均完成一代；Customer 候选分别因 scope 和缺完整 Skill 被拒绝，Service 均为 NOOP。在线没有接受新 Skill，不声称算法改进。一次先前失败也完整保留。

无需网关或凭证，回放全部 17 个 Episode 和三个完整 Controller 报告：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python experiments/vast_coevo/examples/replay_live_bundle.py
```

[原始压缩包](results/live-pilot-bundle.tar.gz) 包含完整实际请求/响应、轨迹、Oracle、Patch/错误、Library、配置、调用日志及当时源码。回放在固定源码的独立子进程执行，拒绝实际模型调用，并保留每个原始 JSON 和 hash。包里的 Skill 和模型返回只作为数据读取。
