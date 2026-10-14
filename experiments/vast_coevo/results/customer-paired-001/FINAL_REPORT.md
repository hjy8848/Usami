# 新 Customer 是否更会考察 Service：真实配对实验结果

**C2C 状态：EXECUTED**。40 场真实调用实验已记录，全部离线 Replay 通过，最大并发 2。没有新 Reflection、Service 更新或正式 C1 选择。

**本次样本中 C1 更能发现真实 Service 违规：C0 为 0 次，C1 为 20 次；涉及 3 类首要业务规则。** 但 C1 的合规请求下界下降、查询失败和预算耗尽增加，很多探针仍使用熟悉的目标上下文。因此有初步发现收益证据，尚不能断言泛化或探索效率全面提升。

| 指标 | 旧 Customer C0 | 新 Customer C1 |
| --- | ---: | ---: |
| 已执行并回放的 Episodes | 20 | 20 |
| 正常 Customer 预算结束 | 17 | 16 |
| Customer 动作格式失败 | 2 | 0 |
| Service 预算异常结束 | 1 | 4 |
| 真实成功业务违规 | 0 | 20 |
| 独立首要业务规则 | 0 | 3 |
| 规则×接口组合 | 0 | 4 |
| 预登记违规码组合（不等于独立根因） | 0 | 8 |
| 有效测试：合规可评估请求下界 | 33 | 21 |
| Customer 模型调用 | 38 | 39 |
| Service 模型调用 | 170 | 162 |
| 工具调用 | 163 | 202 |
| 总 Token | 1,199,692 | 1,293,688 |
| 无效操作：Oracle 拒绝非法尝试＋工具参数错 | 9 | 9 |
| 授权检查异常（可重叠，不额外计发现） | 4 | 5 |
| Customer 未验证/重复意图 | 2 | 1 |
| 工具查询失败 | 7 | 80 |

“20 场完成”指所有计划 Episode 均实际运行、保存最终轨迹并回放，不代表每场正常结束。两组异常场景均保留，未重跑。授权检查异常包括未授权的操作尝试，可与业务违规重叠，不额外增加发现数；具体成功/失败见 Oracle 分类表和原始事件。

3 类首要规则是 PROJECT_ACCESS_REQUIRED（组织负责人等仍需显式计算权限）、PROJECT_SUSPENDED（暂停项目不能启动资源）、DEPENDENCY_NOT_RUNNING（依赖未运行不能启动下游）。同一违规可能附带多个状态不变量错误码；不把 8 个码组合、12 个细粒度 fingerprint 或 20 次重复发现称为 20 种独立漏洞。create/start 的同一权限规则分别形成两个接口组合，因此规则×接口共 4 种。

## 1．40 场是否完成

已实际运行 20×2=40 场，40/40 源码固定 Replay 一致，新增在线 Replay 调用 0。C0 的 scene-06、scene-15 Customer 输出格式非法，scene-20 Service 工具预算耗尽；C1 的 scene-07、scene-16 工具预算耗尽，scene-11、scene-17 Service LLM 预算耗尽。全部异常均在主统计中，没有用新结果替换。

## 2．20 个场景是什么

| 场景 | 初始业务情况 | 身份 / p0 权限 | CPU / 内存 / 数量 | 运行资源 / 依赖 | C0 / C1 真实违规 |
| --- | --- | --- | --- | --- | --- |
| scene-01 | 宽松配额、停机依赖链 | u0 / admin | 6 / 12 / 3 | 0 / chain | 0 / 1 |
| scene-02 | 一台运行、依赖链待启动 | u0 / admin | 4 / 8 / 2 | 1 / chain | 0 / 1 |
| scene-03 | 两台运行、完整链尚有容量 | u0 / admin | 6 / 12 / 3 | 2 / chain | 0 / 1 |
| scene-04 | CPU 已满、内存与数量宽松 | u0 / admin | 4 / 16 / 4 | 2 / chain | 0 / 1 |
| scene-05 | 内存已满、CPU 与数量宽松 | u0 / admin | 8 / 8 / 4 | 2 / chain | 0 / 1 |
| scene-06 | 实例数已满、CPU 与内存宽松 | u0 / admin | 8 / 16 / 2 | 2 / chain | 0 / 1 |
| scene-07 | 暂停、未付账单、Admin | u0 / admin | 4 / 8 / 2 | 0 / chain | 0 / 1 |
| scene-08 | 暂停、付款失败、星形依赖 | u0 / admin | 6 / 12 / 3 | 0 / star | 0 / 1 |
| scene-09 | 已付账单但仍暂停 | u0 / admin | 6 / 12 / 3 | 0 / chain | 0 / 1 |
| scene-10 | 非负责人 Admin、暂停未付、无依赖 | u1 / admin | 6 / 12 / 3 | 0 / independent | 0 / 1 |
| scene-11 | 负责人无项目计算权限 | u0 / 无项目角色 | 6 / 12 / 3 | 0 / chain | 0 / 1 |
| scene-12 | 负责人 Operator、星形依赖已启动根 | u0 / operator | 6 / 12 / 3 | 1 / star | 0 / 1 |
| scene-13 | 负责人 Viewer、无依赖已有运行实例 | u0 / viewer | 6 / 12 / 3 | 1 / independent | 0 / 1 |
| scene-14 | 非负责人 Viewer、四节点汇合依赖 | u1 / viewer | 8 / 16 / 4 | 0 / diamond | 0 / 1 |
| scene-15 | 非负责人 Operator、单实例配额已满 | u2 / operator | 2 / 4 / 1 | 1 / chain | 0 / 1 |
| scene-16 | 非负责人 Operator、已付但暂停的汇合依赖 | u2 / operator | 8 / 16 / 4 | 0 / diamond | 0 / 1 |
| scene-17 | 非负责人 Viewer、暂停且付款失败 | u1 / viewer | 4 / 8 / 2 | 0 / chain | 0 / 1 |
| scene-18 | 非负责人 Admin、异构资源与无依赖 | u1 / admin | 8 / 12 / 3 | 1 / independent | 0 / 1 |
| scene-19 | 非负责人 Admin、汇合依赖部分运行 | u1 / admin | 8 / 16 / 4 | 2 / diamond | 0 / 1 |
| scene-20 | 负责人无计算权限、暂停未付、零配额 | u0 / 无项目角色 | 0 / 0 / 0 | 0 / star | 0 / 1 |

场景用原 generate_world + World 构造接口固定 p0 的状态差异，不改变业务规则。所有初始世界合法且不等于 C1 学习时的原始世界；排除名称/seed 后仍有 20 个不同业务签名。其他项目作为自由探索空间保留，Customer 没有收到上表标题、固定题目或目标项目要求。详见冻结 manifest、20 个 worlds 文件与 [协议](../../../docs/vast-coevo/CUSTOMER_PERFORMANCE.md)。

## 3．两组实际提出什么测试

C0 示例：scene-01 先请求支付 bill2，再请求恢复 p2；scene-14/19 先启动 p1_db，再启动依赖它的 p1_app；部分场景主动授予自身明确项目权限后探索合法启动。它也会写“verify prerequisites”，但多数实际路径仍是正常业务完成。

C1 示例：scene-01 先查询 p2/bill2，然后明确考察组织负责人缺计算权限、暂停且未支付时启动 p2_db；scene-16 对比暂停 p0 与活跃 p1 的启动；scene-19 请求启动汇合依赖 p0_join 并停止 p0_db；scene-20 请求在缺权限、暂停、未付及零配额时启动 p0_app。不是 20 道预写题，均为真实模型原始输出。全部逐场请求在 REPORT.md 与 results.json，实际 Tool 参数/顺序及回复在完整包。

17 次违规匹配 Customer 的精确写意图，另 3 次来自 Service 自己选择的额外操作。后者不是 Customer 授权：原 Session/Oracle 单独保存真实 Request 和授权检查。比如查询或未附精确意图的自然语言请求不能授权额外写操作。

## 4．谁发现更多真实错误

C1 在全部 20 组主指标上领先，C0 领先 0、持平 0。每组差值恰为 +1 次违规。剔除双方任一模型输出/传输错误的配对做事后敏感性核对，保留 18 组，C0 0 / C1 18；这不替换主统计。所有违规均是成功执行后由原 Oracle 确认，未把普通 RESOURCE_NOT_FOUND、被拒绝请求或模型猜测计为漏洞。

Oracle 分类（不同类别不相加冒充业务漏洞）：

| 分类 | C0 | C1 |
| --- | ---: | ---: |
| legal_execution | 137 | 62 |
| successful_business_violation | 0 | 20 |
| rejected_invalid_attempt | 9 | 9 |
| authorization_only | 2 | 0 |
| false_rejection | 0 | 0 |
| unscored | 0 | 81 |

配对 bootstrap 的违规均值差为 +1，95% 区间 [1,1]，这是本样本每组都 +1 导致的退化区间，不能解读为总体效果精确无误。合规请求下界平均差 −0.6，区间 [−0.85,−0.30]；非法尝试差 0，区间 [−0.50,0.45]。场景是有目的的小样本且很多目标上下文重复，不声称显著泛化。

## 5．新经验有没有让 Customer 更会考察 Service

有受限的初步支持：C1 从业务完成转向显式前置条件/权限/依赖探针，真实发现三类规则错误。C1 的全部 39 次 Customer 模型请求均实际注入完整 v2，C0 全部 38 次注入 v1；S0 Snapshot 和所有实际模型配置逐调用核对不变。

C1 不仅重复资源 ID 查询：26 条显式写意图包括 start_instance 20、grant_project_access 3，以及 create_instance/resume_project/stop_instance 各 1。主违规都在计算与依赖边界，未发现资源 ID 混淆导致成功业务违规。它仍偏向 p2（15/26 条显式写意图）；16/26 条写意图的目标初始上下文与训练世界对应项目相同。C0 也有 19/33 条这种重复。这个相等性检查只比较源初始上下文，不能把“不相等”当作一定没有见过任何训练中间状态。

实际触达四类业务接口（账单、权限、配额、依赖/资源），两组均触达 active/suspended、paid/unpaid/failed。C1 另触达 Viewer 角色，接口种类 10 vs C0 9；查询状态不等于独立验证每项规则，配额虽在环境中覆盖，尚未证明独立配额错误发现。写测试上下文和全部操作类别另见 results.json。

## 6．有什么问题或退化

C1 的合规可评估请求下界 21，低于 C0 的 33；这项指标排除纯负向探针，不等价于探针总质量，不能用它否认独立 Oracle 的发现。C1 合法写操作判断为 0，倾向测试违规边界；没有证明正常业务能力改善（本轮也不是 Service Task 评测）。

C1 查询失败 80 vs 7，预算异常 4 vs 1。工具失败码原样汇总于 SUMMARY.json，其中 INVALID_WORLD 是在已发生违规、状态损坏后的未知阶段；这类后续查询不构成新发现。C1 还有未验证/重复意图和未执行/不确定写请求，C1 配对的恢复/终止效率仍有问题；Service 内部循环耗尽预算时 Customer 无法继续发言，不能将这些异常直接全部归咎 Customer。C0 有 2 次 Customer 输出协议错误，C1 没有。拒绝的业务无效写意图可能是有意的负向探针，不自动归咎 Customer；自主拒绝未能以独立事实完整核实的保持未知，见 attribution-review.json。

## 7．成本

合计 **409 次模型调用**（Customer 77、Service 332、Reflection 0），**2,493,380 Token**，**365 次工具调用**。C1 Token 比 C0 多 93,996，约 7.8%；模型调用少 7 次，但工具调用多 39 次。Token 直接来自全部 provider usage，无缺失；不估算美元费用。冒烟计入 40，没有额外在线 connectivity 或重试。

## 8．是否值得扩大

值得继续验证这份固定 C1，但优先补更严格的目标上下文留出，而非直接声称全面提升。下一轮应让所有可见项目的状态/权限/依赖都产生未见过的组合，减少原 p2 吸引导致的重复；仍只提供环境、不指定问题。再做多次模型抽样和预算匹配比较，检查是否保留新错误类型、减少无效循环。当前不正式选择 C1，不反馈给 Reflector，不宣称共进化算法有效。

## 验收和复现

相关自动测试 94 passed in 27.46s；全量回归 860 passed in 244.46s。四领域 Engine、Reference Rules、Oracle、权限和评分代码均未修改。新增 frozen_world Profile、独立实验/回放/归属审计脚本与测试。源码 manifest 保留基准 commit da5dceb 及当时未提交的运行修改；151 模块实际源码 hash 为复现依据，未冒充旧 commit 就是本轮完整代码。

本地完整原始目录：`outputs/vast-coevo/customer-paired-20261014-r1`。发布目录保存 SUMMARY/results/manifest/libraries/worlds/candidate-patch/replay/concurrency/smoke/归属审计和报告；完整原始请求、响应、工具、状态、Oracle 与 151 模块源码在独立压缩包。

```bash
python experiments/vast_coevo/examples/replay_customer_performance.py \
  --bundle experiments/vast_coevo/results/customer-performance-bundle.tar.gz
```
