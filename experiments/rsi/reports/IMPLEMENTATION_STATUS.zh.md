# RSI v0.2 实施状态

本文件逐项区分已经执行的工程检查与尚未完成的目标。2026-10-24 起按用户提供的 v0.2 规范对齐；下文早期 v0.1 记录作为历史实施日志保留，不自动代表当前版本状态。

## 基线和本阶段变更

- 基线：Usami `229ed3e55ce0dee53f75e95fa3f7b8e337f99a69`。
- 独立工作区：`/Users/spring/RSI/Usami-rsi-core`；分支 `feature/rsi-core-v01`。
- 原工作区的未提交内容、网页、业务规则、Oracle、原生评分与历史实验均未修改。
- 新增独立 `rsi_core`、Docker 隔离 worker、Usami Adapter、种子程序、协议夹具和相关测试。

## 当前已经具备的行为

1. P/M 都有不可变源码、父引用、哈希及不同入口；候选只通过 Host 返回四类研究决定。
2. 容器使用已缓存的固定摘要 Python 镜像，不拉取镜像；无网络、只读根文件系统、非 root、无 capabilities、无 Host 目录或凭据挂载。仅挂载公开 worker 脚本。
3. STAGE 失败消耗候选名额；第一次 PROBE 后冻结候选集合；提交父版保留原引用。
4. SELF_EDIT 的 M 探针只通过 ADAPT_TASK 评价候选，从共同 P0 培养 P，随后在私有 query 上计分；ADAPT_TASK 不能登记 M 或调用未登记实验。
5. 外层包分区检查使用 family、source_lineage 与任务引用；候选公开视图不序列化 query。真正的来源审核和任务包采样器仍待完成。
6. 独立选择只消费 C_select，不能用 C_reward；均值、配对绑定、UNKNOWN 和已知越界分别检查。
7. 三代真实容器协议 smoke 覆盖 ACCEPT、保留父版、后继 M 实际主持下一代；固定编辑器对照保持 M0，同时 target 继续推进。
8. Usami 适配从公开历史调用原生工具，沿用 Customer、Engine、Oracle、Replay 和 strict_task_success；原生退款夹具已实际完成，操作没有读取隐藏 ID。
9. 根轨迹导出保留轮次，prompt mask 为 0，生成 token mask 为 1，内层评价不入根 loss；缺 token/logprob 的推理接口明确不能导出为 RL。

## 可重复命令

依赖：Python 3.9+、jsonschema、可用 Docker，以及预先审查并缓存的固定摘要 Python 镜像。下面的镜像是本机实际执行过的镜像，不自动下载。

```sh
python -m rsi_core.smoke \
  --image sha256:f06d01d4ba3f8ad5af45a3ec87df19c1d317d8e8961edc0fabda61811af6f7cf \
  --output outputs/rsi-core-contract-NEW

python -m pytest tests/test_rsi_core.py tests/test_rsi_evaluation.py \
  tests/test_rsi_usami_adapter.py tests/test_rsi_training_records.py -q
```

输出目录必须新建。smoke 是手写程序驱动的算术协议夹具，模型调用和训练更新均为 0，不是自然错误实验、真实模型学习、第二正式环境或 H1/H2/H3 证据。`experiments/rsi/seeds/M0.py` 是单独的通用模型驱动种子；smoke 的手写继承链不是该初始算法。

## 阶段验收矩阵

| 阶段 | 已有证据 | 尚未满足的要求 |
| --- | --- | --- |
| P0 | 原生公开请求与 S0 请求逐项一致；已认证退款夹具经原生执行与 Replay；可信包注册、原生证书核验、分区抽样与恢复 | 正式来源审核及足量自然任务池、固定 Customer/业务模型实际配置、适配预算完整登记 |
| P1 | v0.1 容器与递归夹具；v0.2 新增完整 `(B,P,K)` Service / `(φ,M)` Designer 快照、挑战基线顺序、直接任务集和 K+1 周期编排；新增针对性合同测试 | 周期编排测试使用采集器替身；完整 Native Adapter + 动态认证器周期尚未端到端运行；固定预算恢复尚未验收 |
| P2 | 可执行 probe 与独立 query 路径 | 自然失败固定候选集、随机/难度/分歧/学习选择和反馈遮蔽对照及独立 query 结果 |
| P3 | 根 token/logprob/mask 数据协议；verl 0.9.1 的可选 AgentLoop、归档轨迹转换与 GRPO 单组导出代码（未运行） | 可训练研究模型、verl 运行时验证、真实参数更新、checkpoint 身份核对和独立开发比较 |
| P4 | SELF_EDIT、Adapt/F、C_select 选择；G 条根轨迹采集、私有配对奖励；新增 `r_service` / `r_self` 分组优势与 verl 周期数据导出代码（未运行） | verl 加权 loss hook、训练启动器、checkpoint 对照、实际参数更新与自然任务数据 |
| P5 | 三代工程夹具和固定编辑器语义 | 使用经训练 φ 的冻结模型多代运行、固定预算和全部独立审核 |
| P6 | Core wheel 可独立构建；不导入 Usami | 独立 M* 交叉检验、第二真实环境 Adapter、跨环境/迁移和统计报告 |

CPU 账本当前记录 Host 测得的单 vCPU 容器墙钟上界，并明确标注不是实际 CPU 利用时间。该值用于保守限制候选，不接受候选自行报告的资源消耗。实际训练 GPU 时间尚未发生。

## 已执行检查

- 第一轮相关 Core、Adapter、训练数据契约测试 18 项通过。
- 加上原生 Runtime 相关回归的一轮 35 项通过。
- 当前最终相关检查：Core、嵌套评价、Adapter、训练记录契约和原生 Runtime 共 38 项通过（10.50 秒）；`compileall` 和 Git Diff 空白检查通过。
- 实际三代容器 smoke：`ACCEPT / KEEP_PARENT / KEEP_PARENT`，0 模型调用，0 参数更新。
- Core wheel 已构建；另用 `python -I -S` 在无法导入 Usami 的解释器中执行 wheel 内的通用 smoke，检查结果见本地输出目录。
- 以上计数是阶段执行记录；后续修改后的最终检查以新报告为准，不把旧测试结果默认为当前代码全量证明。

## 历史下一项实现（v0.1 记录）

本节记录在预算、采集和包注册实现之后的原计划。verl 适配代码进展见文末的 2026-10-24 更新；P3/P4 仍未完成。

本目标仍在进行。工程协议、实际参数训练、任务收益和 RSI 研究证据分别验收。

## 预算分配修复（2026-10-24）

根因：旧 `Reservation.spend()` 暂时释放整笔预留，但没有局部分配上限；区间内可以借用根账本余额，退出时还会重新预留已经消费的份额。

`rsi_core/budget.py` 现在按真实子调用消耗扣减分配余额，仅恢复未使用部分；超额消费明确失败且保留实际成本。`reserve_group()` 在进入调用方之前登记全部阶段额度，任一阶段无法预留则释放已登记额度，不启动采样。各阶段顺序执行；区间内嵌套评价沿用同一账本，不能另开预留。省略的资源额度为零。

新增的状态检查分别约束已关闭、重复进入、超额后重用及区间内另开预留；非有限消耗拒绝入账。这些是预算契约检查，没有添加自动重试、兼容回退或默认成功。

实际检查：新增预算测试 8 项；与 Core、评价、原生 Adapter、训练记录及原生 Runtime 合计 **46 项通过，10.50 秒**；`git diff --check` 通过。

本次完成的是可调用的预算原语及边界验证。G 条根轨迹采样器、完整组 Controller、持续奖励包抽样和真实训练器尚未接入，不能据此登记 P3/P4 完成。没有在线模型调用或参数更新。

## 整组采集与奖励来源（2026-10-24，后续实现）

新增 `rsi_core/collection.py::collect_self_edit_group()`：相同 editor/target、冻结模型、公开输入和阶段额度下，运行多条独立根轨迹；默认实验调用方可登记四个不同 seed。采样前预留所有根、选择与奖励额度；所有根提交之后，才在 C_select 选版本、在独立 C_reward 计算奖励。相同候选的外部评价去重，但每条根轨迹均保留。

新增 `collection.training_records()`，只接受完整可用组；`training.root_training_record()` 进一步核验根运行、上下文、冻结模型、奖励回执、C_reward 配对绑定和实际评价归档，拒绝用任意字符串或 C_select 分数作为奖励来源。提供方故障、评价预算不足或超出 UNKNOWN 有效性阈值的组不会导出部分训练样本。合法 M 在内层培养失败仍以 F=0 参与均值；根失败 -1，NOOP 为 0。

整组容器测试也暴露并修复了 CPU 浮点余额释放残差：预留总额现在根据仍存活的分配计算，退出全部分配后精确归零。没有添加重试或静默成功路径。

验证性质：脚本模型返回明确标注的 token/logprob 夹具，实际隔离程序、任务执行和配对评分走真实 Core 路径。它证明奖励和导出工程语义，不证明真实模型生成质量或参数训练。可信包采样器、自然失败固定候选实验、真实 RL 后端与后续 P5/P6 验收仍未完成。

最终相关检查：**54 项通过，20.68 秒**；`compileall` 与 `git diff --check` 通过。覆盖四根奖励 `1/0/-1/0`、重复候选评价去重但保留四根训练记录、提供方故障、UNKNOWN 整组失效、采样前预算不足以及非有限选择阈值拒绝。原生 Runtime 测试纳入本次检查，业务评分未改动。

下一步接可信 PackageProvider 与持续 C_reward 来源抽样，再接实际可训练模型后端、warm-up 和 SELF_EDIT 参数更新。当前采集器仅接受调用方提供的已登记任务包，不冒称已经具备经审核的正式训练分布。

## 可信任务包来源与抽样（2026-10-24，后续实现）

新增 `rsi_core/packages.py`：注册任务包时要求每条 support 的原始来源、每个 probe/query 的来源及独立证书；验证器未明确通过的任务不能入池。family/source_lineage 跨外层分区或用途冲突、原数据跨 support/probe/query 角色、同一私有 query 用不同包名重复登记均明确拒绝。

采样使用冻结清单、显式 seed 和剩余池，逐次无放回；抽样、清单和恢复状态都有内容哈希。恢复时重算此前每次抽样，不能只信任保存的 ID 列表。训练上下文的三个池先共同预检，某池不足时不消费其他池。耗尽后要求登记新的数据与协议，不自动循环使用旧奖励包。

新增 `integrations/rsi_usami/packages.py::NativePackageVerifier`：以既有 `verify_task_certificate` 复算真实原生证书，并绑定实际世界、任务、Customer 配置、预算、模式、外生事件及 Customer 工厂源码引用。证书的 business/full_task/interaction 覆盖范围原样保留。该层没有新增 Oracle、业务规则或任务完成判定。

`collection.collect_sampled_self_edit_group()` 将抽样接入既有整组执行；采集上下文记录抽样引用，执行前校验包 ID 与冻结清单中的完整内容，不能保持包名却替换 query。此信息只进可信归档，不进候选或模型公开输入。

范围说明：这是注册池与数据协议实现，尚未产出经过独立审核的大规模自然任务池。来源标签必须来自可信数据登记，程序检查不能自动证明两个不同标签确实具有结构差异。现有测试使用明确标注的通用协议夹具，另有两个真实 Usami 世界的原生证书复算。

实际检查：包括新包采样、原生证书、整组采集与原有 Core/Runtime 在内 **63 项通过，24.64 秒**。随后补充旧 hash 的 `model_copy` 篡改检查并对原生证书测试复测 **2 项通过，0.52 秒**；`compileall` 和 `git diff --check` 通过。模型 API 调用及参数更新仍为零。

下一项为实际可训练模型接口和 warm-up RL 奖励/更新路径；正式训练仍需实际模型、硬件、自然数据与预算登记。注册池已经接入采集器，但尚不代表 P2 自然失败实验、P3/P4 参数训练或 P6 来源独立性研究验收已经完成。

## verl 后端代码准备（2026-10-24）

新增 `rsi_core/verl_backend.py`，将完整、已核验的 G 条根轨迹导出为 verl `0.9.1` 的 AgentLoop/GRPO 单组数据包，并提供 ResearchHost 到 verl 异步推理客户端的显式适配。GRPO 的 `uid` 绑定已登记采样组；输出保留每个 root 的 token、生成掩码、行为 logprob、终局奖励和证据引用，loss 使用 `seq-mean-token-mean`。

多轮轨迹只有在后续 tokenized prompt 精确延续此前 prompt 与模型生成序列时才允许合并；其他轨迹明确拒绝导出，避免把不同条件下的动作伪造成一条序列。配置导出是 verl 配置片段，不是独立训练启动命令。

本次仅写代码和文档：没有安装 verl，没有调用模型，没有启动 Ray / GPU，也没有进行参数更新；没有运行测试或训练。实际 verl API 兼容性、checkpoint 权重与 `ModelSnapshot.parameter_hash` 的对应关系、参数更新后的重新采样和跨组训练流程均未验证。TRL 草稿未保留。P3/P4 因此仍未验收。

## v0.2 规范对齐与周期数据接口（2026-10-24）

将研究状态改为明确的 `(φ,M)` Designer 与 `(B,P,K)` Service 快照，并补上主链继承检查：B 固定，P/K 分别继承已选父版；Designer 可在保持 M 时更新 φ，或由 M 自修改，但模型基座和采样配置不变。evaluation-only Service 副本不能发布到主链。

Service 根轨迹现在使用独立、经证书登记的 `service_probe / service_select / service_reward` 任务集。Host 强制新挑战先冻结认证、再由父 Service 执行基线，最后才允许候选在该挑战上 PROBE。Service 候选是完整 P/K 包。适应任务评价继续使用分开的 C_probe/C_select/C_reward 包。Usami 候选可见反馈经过版本化投影，仅包含公开工具交互、任务分数/状态与聚合安全标记；Oracle 分类和隐藏任务结果留在可信 Episode/Replay 中。

`rsi_core.period.run_period()` 以 K 个 Service 组、一次 M 自修改组为顺序编排；M 自修改的所有包绑定阶段 A 最终接受的同一个 Service 快照。周期末更新钩子只调用一次，并收到原始归档组以及分开的 `r_service` / `r_self` 记录和组内 GRPO 优势，便于在 φ 仍冻结时调用 verl 周期导出。没有训练钩子时记录为 `READY_FOR_TRAINING`；训练回调失败时记录 `TRAINING_FAILED`，不发布新 φ。数据导出会把两个根类型及组内优势写入同一周期 manifest，并显式保存等类型、等上下文的 loss 权重；stock verl 不会自动使用该权重，定制 weighted-loss hook 仍是训练前置条件。

实际检查：新增 `tests/test_rsi_v02.py`，并与 Core、包注册、整组采集、评价、训练记录、Usami Adapter、预算测试合计 **48 项通过，24.56 秒**。覆盖版本谱系、挑战必须先跑父版、周期调用顺序、两类 advantage 隔离、直接任务 UNKNOWN/安全门槛、verl 周期数据权重及 rollout manifest、Usami 反馈不向 Designer 暴露 Oracle。另运行了三代离线算术协议 smoke：`ACCEPT / KEEP_PARENT / KEEP_PARENT`，0 模型调用、0 参数更新；`py_compile` 与 `git diff --check` 通过。

限制：周期编排测试用替身验证顺序，不是完整自然任务周期；动态 Usami challenge 提案认证尚未接成可直接启动的完整入口。verl 未安装，AgentLoop / weighted-loss hook / checkpoint 权重身份没有实际验证。未调用真实模型、未启动 RL、未改变任何训练参数；48 项测试和离线 smoke 只能证明工程协议，不是能力提升或 RSI 效果。
