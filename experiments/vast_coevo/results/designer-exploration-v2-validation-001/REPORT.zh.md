# Designer 第一轮优化：实现已完成，真实出题验证 BLOCKED

四项接口修改已经实现，但**尚未证明真实 Designer 能自主提交一项可执行任务**。本轮做了五次独立登记，合计 42 次真实模型调用、34 次只读查询，收到 16 份完整提案；全部未获原生 Reference 证明。因此业务任务仍为 **0/3**，没有 Customer/Service 对话、Reflection 或 Skill 更新。不能把工程测试通过解释为自主出题或共进化成功。

## 实现了什么

1. **按需探索。** 对话领域的 `designer_view()` 默认只返回冻结登记、时间、身份及集合数量。`inspect_frozen_world` 支持分页列出画像、查询具体画像及相关记录、读取具体对象、查询公开规则及原生字段枚举。画像查询除可修改对象外，也补充有界的只读订单、产品、证据等关联记录。它不调用 Reference、不返回见证或预期判决，也不修改世界。
2. **高层提案。** 新 `DialogueDesignerProposal` 不接受 `frames`、`selector_field` 等字段。模型选择顾客、挑战、目标及可选的交互要求；编译器先用原生 `load_profiles` 验证同一身份，再合并原生 `_contract` 范围。模型指定的目标、偏好和事件不会被自动改成其他答案。原有世界、业务规则、Engine、Oracle、任务评分和正式 Service Gate 均未修改。
3. **有界纠错。** 每项挑战最多 5 次探索调用、20 次只读查询、初次提交加 3 次修正。当前真实入口首次提交前最多用 4 次探索，保留剩余预算用于补查。失败反馈包括真实编译错误、剩余预算及重复提案提示；`search_unproven` 只表示预算内未证明，不声称任务不可能。传输失败不自动重试。
4. **明确提交阶段。** 探索时允许自由选择查询工具，提交时强制 `submit_frozen_world_task`。Qwen 可在探索时显式启用思考；提交时单独设为 `enable_thinking=false`。这是 API 兼容处理，实际请求均留档，没有用程序替模型填写提案。

Qwen 官方说明思考模式不支持强制工具选择：[Function Calling 文档](https://docs.modelstudio.console.alibabacloud.com/en/model-studio/qwen-function-calling)。首轮登记保留了对应 400 失败；其后配置均单独登记。未知的 HTTP 错误响应正文没有被保存，故不把官方限制冒充为已读取的网关原始报错。

## 真实验证记录

所有登记都使用同一 seed=1 冻结世界、同一 Qwen 基础模型，均未注入固定题目或修复答案。接口与配置在工程诊断中逐次调整，因此这些记录**不是模型能力的对照实验**，也不能据此估算泛化提升。

| 登记 | 实际调用 | 完整提案 | 已知 Token | 结果 |
| --- | ---: | ---: | ---: | --- |
| [v2-001](../aftersales-coevo-exploration-v2-001/manifest.json) | 6 | 0 | 23,260，下界 | 只读探索成功；强制提交请求 HTTP 400 |
| [v2-002](../aftersales-coevo-exploration-v2-002/manifest.json) | 9 | 4 | 43,789 | 已关闭思考；提案重复且未证明可达 |
| [v2-003](../aftersales-coevo-exploration-v2-003/manifest.json) | 9 | 4 | 44,853 | 为纠错预留查询预算；目标仍未证明可达 |
| [v2-004](../aftersales-coevo-exploration-v2-004/manifest.json) | 9 | 4 | 49,259 | 查询补充不可修改的订单/证据；仍未获证 |
| [v2-005](../aftersales-coevo-exploration-v2-005/manifest.json) | 9 | 4 | 71,685 | 探索时保留思考、提交时关闭；仍未获证 |

五次登记分别设置剩余调用上限 65、59、50、41、32，跨登记总上限始终为 65。实际只消耗 42 次后停止。失败没有被覆盖，每次真实请求都有独立记录，不存在同一请求中的隐式重试。

已知输入 **223,164** Token，已知输出 **9,682** Token，合计至少 **232,846** Token。001 的失败 HTTP 请求无 usage，因此不能把这个数写成完整准确的计费总量。全部真实调用都属于 Designer；Customer、Service、Reflector 调用均为 0。

首次模型请求的输入从旧版本记录的 33,826 Token 降至本轮最后一次登记的 2,207 Token。这只比较首次请求，不代表整场总成本降低或质量非劣；后续查询、历史和纠错的实际成本另行计入。

## 分开看四项指标

| 指标 | 实际结果 | 可以得出的结论 |
| --- | --- | --- |
| 合法出题率 | 0/16 完整提案；另有 1 次提交 HTTP 失败 | 交付流程能运转，尚不能自主产生可证明的任务 |
| 题目多样性 | 获证任务 0 | 无法评价有效题目的多样性，候选对象变化不能替代获证覆盖 |
| 任务难度 | 无获证 AI 任务 | 无法评价真实题目难度；Reference 路径长度也不等于最短路径难度 |
| 真实执行率 | Service 业务任务 0/3 | 没有获证题目供执行；不能算作已完成交互、反思或学习 |

## 离线归因：不能只说模型不行

16 份提案都已通过对象、字段及原生作用范围检查，失败发生在可达性证明阶段。独立检查这些目标对应的原生 `eligibility()`，14 次选择已过售后窗口的商品，另 2 次初始可开启售后。后两次仍需核验偏好、事件及完整路径，不能因为初始可开启售后就宣布整个目标可达。

全部冻结画像中，初始售后资格检查有 11 项通过、19 项过期、1 项未交付。**初始资格通过不是完整任务可达证书**，也不作为推荐题目反馈给模型。详见 [离线候选审计](offline-candidate-audit.json)。该审计在全部在线尝试结束后才运行，没有回流到 Designer 或 Reflector。

另以已有离线回归中的退款声明做了一个明确标记的正向控制：相同冻结世界、相同新编译接口，显式声明原生允许的退款偏好后，独立证明并 Replay 了 **5 个业务步骤**。这说明底座并非完全不能表达和证明合法任务，但它是程序化回归输入，**不计为 AI 自主出题，不计为 Service 主任务，不计为学习收益**。初次控制漏掉偏好声明而未获证的记录也单独保留，并未隐藏。

现有证据支持的判断是：机械字段和权限声明的负担已移出模型；但模型仍未把观察到的事实、目标、偏好及事件组成获证挑战。不能把剩余问题全部归因于模型能力，也不能宣称第一轮自主出题目标已经达成。本轮没有扩大世界、题库或实现第二轮的新对象 Goal。

## Replay 与复现

每次登记保存冻结世界、初始 Library Snapshot、模型配置、全部请求/回复、查询返回、编译反馈、失败原因和源码快照。五份 `verification/designer-failure-replay.json` 均已通过：重新运行同一确定性探索/纠错程序，逐项比对请求、查询结果、反馈和失败，无在线模型调用。

独立重放失败日志的最小方式：

```python
import json
from pathlib import Path
from usami_benchmark.worlds import FrozenWorld
from usami_benchmark.designer_exploration import verify_failed_journal

p = Path("experiments/vast_coevo/results/aftersales-coevo-exploration-v2-005")
frozen = FrozenWorld.model_validate_json((p / "world/frozen_world.json").read_text())
journal = json.loads((p / "designer/task-1-journal.json").read_text())
print(verify_failed_journal(frozen, journal))
```

这些是失败提案的完整回放，不是不存在的三条 Service Episode Replay。正向控制的证书另存于本目录，初次失败和最终成功均明确标记为离线控制。

历史 v1 请求格式与提示保留，旧夹具显式选择 v1；对话 API 和真实入口默认使用 v2。历史 v2 配置中缺省的新增选项不改变旧请求，本轮各次不同配置可按各自日志重放。原有数据、正式 Gate 和选中 Snapshot 未被改写。

## 测试与修改范围

定向命令：

```sh
.venv/bin/python -m pytest -q tests/test_designer_exploration.py tests/test_vnext_open_compositions.py tests/test_aftersales_coevo_live.py
```

测试覆盖只读/有界查询、四领域查询、自动范围、跨身份拒绝、目标不被程序替换、最多三次修正、错误预算、截断恢复、传输不重试、Qwen 阶段选项、原生证书及查询/反馈篡改检测。最终结果见 [tests.log](tests.log)。这是定向回归，没有把全量测试或离线脚本化执行冒充真实在线实验。

修改集中于 `usami_benchmark/designer.py`、新的 `designer_exploration.py`、真实运行器、旧 smoke 的显式协议选择、相关测试与运行说明。另补齐运行器交给既有 Designer Reflector 的反馈 `id`，但本轮并未在线走到该阶段。没有修改世界模型、Engine、Reference Rules、Oracle、Goal 语法或 Service 的正式进化验收。

**最终状态：工程接口已实现；真实自主合法出题仍 BLOCKED；Service 共同进化尚未发生。**
