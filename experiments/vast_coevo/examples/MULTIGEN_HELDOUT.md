# 多代 Skill 进化与独立 Held-out

实现入口：`multigen_heldout.py`；确定性新环境与任务证书：`multigen_worlds.py`；预算与真实调用日志：`multigen_budget.py`。

只复用现有 Customer/Service Reflector、Evolver、Static Gate、Service DynamicGate、Controller、Snapshot 和 Replay。新增的 `RunConfig.customer_updates=false` 是固定 Customer 对照：不调用 Customer Reflector，记录 `outcome=fixed`、`reflection=null`，不伪造 NOOP 或成本。默认 true 仍采用原 Static-Only Selection；旧记录/配置 hash 不补写默认字段。Service 不能省略 Reflection。

冻结世界中的合法任务现在也可通过 `ServiceTaskProfile.frozen_task` 加载。原 Engine、Reference、Oracle 和 Replay 必须执行并重建每条证书，同时核验目标、frame 和精确可选授权。该扩展只负责加载可复现数据，不改变原评分或业务规则。

## 顺序

```bash
# 离线生成、校验证书、冻结全部配置/世界/分析规则和源码。
.venv/bin/python experiments/vast_coevo/examples/multigen_heldout.py prepare \
  --root experiments/vast_coevo/results/multigen-heldout-001

# 真实模型：独立 A/B Smoke -> 2 重复 × 2 组 × 3 代 -> 固定最终 Service -> Held-out。
# 默认使用既有 macOS Keychain；不把凭证写入 Manifest 或日志。
.venv/bin/python experiments/vast_coevo/examples/multigen_heldout.py execute \
  --root experiments/vast_coevo/results/multigen-heldout-001

# 原始响应、请求/注入、Engine/Oracle、Reflection/Patch、Service Gate、评分/统计的离线核验。
.venv/bin/python experiments/vast_coevo/examples/multigen_heldout.py replay \
  --root experiments/vast_coevo/results/multigen-heldout-001
```

只对全新的结果目录执行 prepare，不能覆盖。execute ID 不重跑，不自动重试未知或失败调用，不替换不利任务。部分完成必须报告 BLOCKED。离线 replay 不创建模型客户端，不访问 Keychain 或网络。精确回放要求冻结源码版本和原始轨迹路径；目录里的 source-snapshot 保留执行所用代码。

## 默认预注册设计

- CloudOps Sandbox。两次独立训练世界重复，每次 A/B 使用完全配对的初态、身份、工具与预算；每组 3 代。
- A 固定 C0；B 每代 Customer 反思后只经过静态校验。Service 使用原有完整 Gate，未接受候选绝不进入最终评价。
- 每次重复固定 1 Exploration 世界、1 Development 世界（含合法与拒绝任务），代际恢复初态；另有完全独立的 Smoke 世界。
- 24 个新 Held-out 世界，每世界 1 合法、1 非法任务；每重复分别评价 S0/S_A/S_B，总共 288 场，不用训练 Customer 出题。
- 不仅修改 ID/seed：四个项目的归属、ACL、状态、账单、节点数、规格、运行状态、依赖拓扑和配额均由固定程序变化。按去 ID 的业务结构 hash 排除旧世界及跨分区重复。
- 模型固定上一轮 `dashscope/qwen3.6-plus` 及同样采样配置，无权重训练、模型回退或额外 Agent。
- 最大并发 2。训练每组/重复 500 次调用、400 万 Token；Smoke 共 100 万、Held-out 共 800 万；总 4700 次 / 2500 万 Token 硬上限。每次请求之前作保守输入/输出预留，完成后按 provider usage 结算；未知 usage/在途结果立即阻断，原始请求与响应保存。
- 匹配的是相同训练机会和资源上限，A 的未使用 Reflection 预算不重新分配。Service Gate 因实际错误或候选产生的额外执行量如实计费，不能宣称两组实际成本完全相同。
- Held-out 主要正确率平衡合法完成和非法拒绝。必须满足原 goal/frame、Oracle、预算和精确授权；拒绝还需明确拒绝措辞与对应公开规则码。错误/预算耗尽不自动算正确。
- 主比较 B-A，另列 A-S0、B-S0。按运行与世界配对 Bootstrap，3 个比较采用 Bonferroni 同时区间。阈值、种子、样本和判定全部在调用模型前写入 Manifest。
- 相同最终 Snapshot 的随机差异不归因为进化。只有 2 个训练重复，不能把多个任务当成独立训练样本，也不能把有目的世界样本的区间夸大为广泛泛化。

实际版本、详细预算、数据、阈值与失败处理，以每次不可变 `MANIFEST.json` / `EXPERIMENT_PROTOCOL.md` 为准。

## 工件

`EVOLUTION_SUMMARY.json` 保存每代实际选择及原因，`FINAL_SNAPSHOTS.json` 在评价前冻结最终版本。`HELDOUT_RESULTS.json` 保存逐任务、总体及规则/场景类别结果；`STATISTICAL_ANALYSIS.json` 保存预注册比较。`REPLAY_AUDIT.json` 核验 Episode、真实请求/返回、Reflection、Static Gate、Service Dynamic Gate 与统计。`wire-ledger/` 保存每次真实请求和返回、未知状态及成本；`work/` 与 `evaluation/` 保存全部原生轨迹。

正式结果未完成时，不生成看似成功的空统计。`STATUS.json` / 中文 `FINAL_REPORT.md` 明确报告实际完成数和阻塞。


## 用户授权的小规模运行 v2

`prepare --small` 冻结 1 次独立重复、A/B 各 2 代、12 个 Held-out 世界（每个合法/拒绝各一题），共 72 场评估，最大并发 4。两条训练链各自顺序执行，评估池最多 4 个 Episode。

本轮上限 1000 万 Token：Smoke 200 万、A/B 各 250 万、Held-out 300 万；调用总上限 2000。保留旧 Smoke 的 145 次调用 / 961580 Token（含原连通检查），累计上限 10961580，低于原 2500 万。最多额外一次 Smoke，不重试线上失败，不将 Smoke 候选带入正式训练。Prompt 保持原版，Service Gate 不变。单次训练重复只报告探索性、条件于此次训练的世界配对区间，不能宣称训练稳定性得到证明。

```bash
.venv/bin/python experiments/vast_coevo/examples/multigen_heldout.py prepare --small --root experiments/vast_coevo/results/multigen-heldout-small-001
.venv/bin/python experiments/vast_coevo/examples/multigen_heldout.py execute --root experiments/vast_coevo/results/multigen-heldout-small-001
```


## 已记录 Customer 输出错误的故障隔离与恢复

`episode_resilience.py` 仅在 discovery / CUSTOMER_OUTPUT_INVALID / Replay verified / 最后一个 Customer 调用已有完整 response 且无 transport error 时，将影响限制为 Episode 失败。它不修改任何 Evidence、输出解析或 Service Gate。未知调用、证据异常、Service 错误保持阻断。新 small Manifest 显式选择此策略；历史 Manifest 缺省继续原严格语义。

`recover_multigen.py prepare --parent ... --root ...` 复制日志到新目录、保留父 Manifest/状态/完整归档、核验原生源码未变，并注册恢复策略。`execute` 复用全部已完成操作（包括失败 Episode），不会重试，也不再运行 Smoke。原 A 组完成结果只回放，B 从未执行操作继续；再冻结最终 Snapshot 并进行原 72 场 Held-out。预算沿用累计账本，总上限不增加。该结果应称为修订协议续跑，不能改写父实验 BLOCKED 状态。
