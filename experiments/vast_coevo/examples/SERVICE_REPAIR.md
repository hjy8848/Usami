# 单次 Service 修复与陌生场景交叉研究

`continue_coevolution.py` 复用 Usami 原 Session、Sandbox、Reference Rules、Oracle、Replay、ServiceEvolver、StaticSkillGate 与 DynamicGate。`max_workers=2` 只改变原 Gate 案例的调度；最终判定仍由原 Gate 计算。没有 Reflection 重试或在线结果替换。

上一轮 `customer-paired-001` 的实际分区为 heldout，因此它只用于只读历史审计，不进入新 Gate 或 Reflection。本轮新建三个自主 Discovery 开发世界，以及三个合法完成和三个经 Reference 认证的正确拒绝回归任务。固定任务仅用于 Service Regression，Customer Discovery 没有固定题目。

在第一次模型调用之前冻结全部 20 个陌生测试世界。四个可见项目的状态、角色、账单、容量、实例规格、运行状态和依赖都发生真实变化，之后一致重映射 ID。测试初态与此前学习/测试、此次开发集的结构哈希对比；测试世界不进入 Reflection、Gate、禁止 ID 提取或候选调整。

## 运行

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python experiments/vast_coevo/examples/continue_coevolution.py \
  --root outputs/vast-coevo/service-repair-NEW prepare --run-id service-repair-NEW

# 凭据只从运行环境或本机钥匙串读取，不记录 Key。
export USAMI_LLM_KEYCHAIN_SERVICE=litellm
export USAMI_LLM_KEYCHAIN_ACCOUNT=litellm-api-key

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python experiments/vast_coevo/examples/continue_coevolution.py \
  --root outputs/vast-coevo/service-repair-NEW customer-gate
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python experiments/vast_coevo/examples/continue_coevolution.py \
  --root outputs/vast-coevo/service-repair-NEW service
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python experiments/vast_coevo/examples/continue_coevolution.py \
  --root outputs/vast-coevo/service-repair-NEW cross
```

同一 Episode ID 有原始证据时仅核验并复用；已经开始但没有完整结果时不能重新调用。Reflection 只有一次真实提交，保留请求、响应或错误。静态合法但动态拒绝的候选只进入隔离诊断四组；没有有效 S1 时仅运行已有两组，报告 BLOCKED，不能编造四组结果。

## 离线核验与归档

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python experiments/vast_coevo/examples/continue_coevolution.py \
  --root outputs/vast-coevo/service-repair-NEW replay
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python experiments/vast_coevo/examples/continue_coevolution.py \
  --root outputs/vast-coevo/service-repair-NEW report
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python experiments/vast_coevo/examples/continue_coevolution.py \
  --root outputs/vast-coevo/service-repair-NEW bundle --output /tmp/service-repair-NEW.tar.gz
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python experiments/vast_coevo/examples/replay_service_repair.py \
  --bundle /tmp/service-repair-NEW.tar.gz
```

便携回放验证所有文件 SHA256，加载归档的运行时代码与实验脚本，用只读路径重定位保留原始签名，不修改证据中的绝对路径和哈希。全部 Episode、实际 Skill 注入、原 Reflection 请求/响应解析、原 DynamicGate 判定和统计均需完全一致。离线回放缺少记录时直接失败，不访问模型服务。

## 实验局限

模型采样参数固定，但网关没有承诺完全确定性，未伪造模型随机种子。只能复现真实响应驱动的状态机与验收，不能保证再次在线调用得到相同文本。20 个预先构造世界是小规模目的性样本；固定基础模型的一次 Skill 更新不能证明权重训练、整个共进化算法或所有业务领域有效。查询失败、引擎拒绝、授权异常和未评分状态分别保留，不冒充真实业务漏洞。
