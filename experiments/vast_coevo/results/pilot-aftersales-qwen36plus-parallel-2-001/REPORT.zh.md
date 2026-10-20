# Qwen3.6 Plus After-sales Pilot · 并发双运行报告

**C2C 状态：BLOCKED**  
运行日期：2026-10-20  
代码提交：`515784086ef9437c96ee512a2522606a04862d1f`  
协议：`aftersales-real-model-coevolution-v2`

## 结果

按用户要求同时启动两个互相隔离的 After-sales Pilot（seed 1、seed 2），每个运行的在线模型调用上限为 65，整体并发上限为 2。两条链都使用 `dashscope/qwen3.6-plus`、温度 0、120 秒单请求超时；未设置显式输出 Token 上限，不自动重试。每条进化链内部保持 Task 1 → Task 2 → Reflection → Task 3 的因果顺序。

两个运行都在相同阶段停止：Designer 各完成 4 次只读探索调用、进行 1 次提案尝试；随后对强制 `submit_frozen_world_task` 工具调用等待 120 秒超时。seed 1 探索 9 次，seed 2 探索 8 次。提案请求没有返回，因此无法进入编译、Reference 证明或 Service 执行。

| 指标 | seed 1 | seed 2 | 合计 |
| --- | ---: | ---: | ---: |
| Service 任务完成 | 0/3 | 0/3 | 0/6 |
| 已发送模型请求 | 5 | 5 | 10 |
| 成功返回请求 | 4 | 4 | 8 |
| 提案请求超时 | 1 | 1 | 2 |
| 已返回 Token | 22,190 | 24,068 | 46,258 |
| Token 用量完整 | 否 | 否 | 否 |
| Reflection / Skill Patch | 0 / 0 | 0 / 0 | 0 / 0 |
| Service 工具调用 / Oracle 结果 | 0 / 无 | 0 / 无 | 0 / 无 |
| Designer 失败日志 Replay | 通过 | 通过 | 通过 |

超时请求没有返回计费 Token，因此 46,258 是已知用量下界，最终费用可能更高。

## 这次定位到了什么

单独的基础接口 Smoke 曾通过：小型强制 Function Calling 返回了合法的 `inspect_order(ORD-1042)` 调用；约 60,038 Token 的合成上下文检索也准确找回埋点。因此，基础聊天、简单工具调用和该长度下的文本检索可用。

但真实 Designer 的提交请求更复杂：seed 1、2 的强制提案请求序列化体分别约 47 KB、53 KB，包含约 26,000、30,700 个字符的消息和完整提案 Schema。两次并发请求都在 120 秒后超时。现有证据不能区分是复杂 Schema/提示词推理耗时，还是并发下网关或后端延迟；不能据此说模型不支持 Function Calling。它也没有证明全链路模型不可用，只说明真实 Designer 提案阶段尚未跑通。

## 证据与复现

原始模型请求、已返回内容、超时错误、冻结世界、Skill Snapshot 和 Designer journal 分别保存在本机忽略目录：

- `outputs/pilot-aftersales-qwen36plus-seed1-001/`
- `outputs/pilot-aftersales-qwen36plus-seed2-001/`

两份冻结世界哈希均已校验；每份 failed-journal 都通过 `verify_failed_journal()` 精确重放 5 个请求/反馈步骤。因为没有产生 Task 记录，本轮没有业务 Episode Replay。

本报告目录的 `summary.json` 记录机器可读汇总，`evidence-index.json` 保存全部本地原始文件的逐文件 SHA-256 和树摘要。原始请求与模型回复仅保留在本机，不包含于 Git 提交。

相关离线测试：`tests/test_aftersales_coevo_live.py`，`4 passed`（Pilot 代码未变）。

## 结论边界

本轮两次真实尝试均未执行 Service，未进行 Skill Reflection，也没有成功或失败的业务 Oracle 结果。它不是进化闭环结果，更不是能力提升证据。下一步应先针对实际 Designer 提案请求检查超时边界，再决定是否单并发进行新一轮；本报告不自动发起下一次在线请求。
