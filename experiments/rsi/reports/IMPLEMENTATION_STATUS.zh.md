# RSI v0.1 实施状态

本文件逐项区分已经执行的工程检查与尚未完成的目标。原始范围是用户提供的《进化核心设计与实现规范 v0.1》，不以本阶段代码替代 P0—P6 的完整目标。

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
| P0 | 原生公开请求与 S0 请求逐项一致；已认证退款夹具经原生执行与 Replay | 正式来源分区任务池、固定 Customer/业务模型实际配置、适配预算完整登记 |
| P1 | 真实容器、四动作、模式隔离、候选冻结、三代继承、篡改检测、独立安装 smoke | 完整组评价预算预留接入 Controller；研究程序确定性重执行核验；额外资源对抗检查 |
| P2 | 可执行 probe 与独立 query 路径 | 自然失败固定候选集、随机/难度/分歧/学习选择和反馈遮蔽对照及独立 query 结果 |
| P3 | 根 token/logprob/mask 数据协议与拒绝无 logprob 接口 | 可训练研究模型、真实采样、warm-up RL 更新、checkpoint 重载和独立开发比较 |
| P4 | SELF_EDIT、Adapt/F、C_select 选择与根导出基础 | G 条完整组采集、持续 C_reward 抽样、r_meta 到真实训练器、冻结快照与训练链推进 |
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

## 下一项实现

优先补齐完整组预算预留、可信包采样与根奖励采集链，再接真实模型训练接口。当前 Usami venv 未安装 torch/transformers/TRL，也未找到预先准备的训练模型。缺少这些条件不影响继续完成离线实现，但不能标记 P3/P4 完成。

本目标仍在进行。工程协议、实际参数训练、任务收益和 RSI 研究证据分别验收。

## 预算分配修复（2026-10-24）

根因：旧 `Reservation.spend()` 暂时释放整笔预留，但没有局部分配上限；区间内可以借用根账本余额，退出时还会重新预留已经消费的份额。

`rsi_core/budget.py` 现在按真实子调用消耗扣减分配余额，仅恢复未使用部分；超额消费明确失败且保留实际成本。`reserve_group()` 在进入调用方之前登记全部阶段额度，任一阶段无法预留则释放已登记额度，不启动采样。各阶段顺序执行；区间内嵌套评价沿用同一账本，不能另开预留。省略的资源额度为零。

新增的状态检查分别约束已关闭、重复进入、超额后重用及区间内另开预留；非有限消耗拒绝入账。这些是预算契约检查，没有添加自动重试、兼容回退或默认成功。

实际检查：新增预算测试 8 项；与 Core、评价、原生 Adapter、训练记录及原生 Runtime 合计 **46 项通过，10.50 秒**；`git diff --check` 通过。

本次完成的是可调用的预算原语及边界验证。G 条根轨迹采样器、完整组 Controller、持续奖励包抽样和真实训练器尚未接入，不能据此登记 P3/P4 完成。没有在线模型调用或参数更新。
