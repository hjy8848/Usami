# After-sales Evolution Pilot · 运行报告

**状态：BLOCKED（未进入 Service 执行）**  
运行日期：2026-10-20  
代码提交：`39b8c58`  
协议：`aftersales-real-model-coevolution-v2`

## 结果

本轮使用 LiteLLM 上的 `GLM-5.2`，seed `1`，冻结训练世界；预算上限为 65 次模型调用，Designer、Customer、Service、Reflector 均配置为同一模型。模型请求未设置显式输出 Token 上限。入口配置的业务执行模式为 **Reference**；本轮没有进入业务执行，因此没有 Sandbox 违规观测。

Designer 完成了 12 次只读查询，发出 1 份提案请求。该请求等待 90 秒后超时，运行器按配置不重试。提案没有返回，无法编译或证明任务，故没有 Service 任务开始。

| 项目 | 实际结果 |
| --- | ---: |
| Designer / Customer / Service 执行任务 | **0 / 3** |
| Designer 提案尝试 | 1（请求超时，未获响应） |
| Skill Reflection / Patch | 0 / 0 |
| 在线模型请求 | 5 次：4 次完成、1 次超时 |
| 已返回用量 | 18,566 Token（16,874 输入 + 1,692 输出） |
| 用量完整性 | 不完整；超时请求没有返回 Token 用量，实际总消耗可能更高 |
| Service 工具调用 / Oracle 结果 | 0 / 无 |
| 业务 Episode Replay | 不适用；没有 Episode |
| Designer 失败日志离线 Replay | **通过**，5 个请求/反馈步骤逐项重现 |

## 可复现证据

原始请求、已返回回复、超时错误、Designer journal、初始 Skill Snapshot 和冻结世界保存在本机忽略目录：`outputs/pilot-aftersales-g1-001/`。共 16 个文件、349,538 字节；逐文件 SHA-256 清单见同目录的 `evidence-index.json`。检查未发现常见 API Key / Bearer 凭据模式。

冻结世界内容哈希：`c5227e1dc9d8b1a49d93b17eaf64018e64ce3c1bf8b00f3e20611c4a581bb3e6`  
冻结登记哈希：`200f77794e7f9c5ee739ec946462621f8167224f5e98de9907b024868b7db0fd`  
初始 Designer Snapshot：`96899a726c2ae468a2a162e5ba97aa0c7d20f69274cfc61c9284f61baf3491bb`  
初始 Service Snapshot：`52de32b10add750883dd988177609a3d9d66f1a82a1181dfb4d9ecf514efebcd`  
固定 Customer Snapshot：`e39daeec262ea94daa6e7836b5c32ca61d4c88b30a5d09a074e2c5c6e469d98f`

验证命令：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q tests/test_aftersales_coevo_live.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m experiments.vast_coevo.examples.aftersales_coevo_live \
  --output outputs/pilot-aftersales-g1-001 --seed 1 --max-model-calls 65 --customer-turns 4
```

入口测试结果：`4 passed`。冻结世界哈希校验通过；失败日志的确定性离线 Replay 返回 `verified=true`、`failure_reproduced=true`。原始记录保存在本机输出目录，不随本报告推送。

## 结论边界

这次只证明运行器能够记录一次真实 Designer 超时并精确重放失败；**没有跑通进化闭环**，没有生成或接受 Skill，也没有 Service 行为改善证据。超时发生在 Designer 提案阶段，根因目前只能定位为该次模型请求未在 90 秒内返回，不能据此断言是模型能力、网关还是题目协议的问题。本报告没有自动重试或追加在线调用。
