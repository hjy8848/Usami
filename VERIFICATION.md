# Usami v0.1 实际验收记录

执行日期：2026-10-12（Asia/Shanghai）。项目目录：`/Users/spring/RSI/Usami`。

运行环境：Python 3.9.6、Pydantic 2.13.5、pytest 8.4.2。已实际安装 `pip install -e '.[dev]'`；`constraints-tested.txt` 记录本次直接依赖版本。以下结果来自真实代码运行，未连接任何模型或外部业务系统。

## 自动化测试

```bash
.venv/bin/python -m pytest -q
```

实际结果：**87 passed in 14.52s**。

覆盖生成一致性及版本固定样例、450 个 seed/profile 世界各两次生成、多 seed 多种业务组合、配置顺序不敏感、自定义规则、全部五个写操作与四个查询、退款第 14 天边界、权限与组织边界、授权顺序及精确参数、重复退款、错误拒绝、错误结果、额外修改、查询数据、未知判定、事件完整性、重放、clone/reset、snapshot、组合外推、私有 Manifest 加载、跨 split 重叠和 CLI 全流程。

`tests/test_oracle.py` 中的违规样例均为人为评分器测试，**不代表 AI 发现了任何漏洞**。

## 命令行和业务流程

| 实际执行 | 真实结果 |
| --- | --- |
| `python -m usami generate --seed 42 --count 10 --out outputs/worlds` | 生成 10 个合法世界 |
| `python -m usami inspect outputs/worlds/world_0001.json` | 显示 3 个组织、成员身份/角色、订阅/席位/周期、账单/支付渠道及规则 |
| `python -m usami scenarios --world outputs/worlds/world_0001.json --out outputs/scenarios` | 生成 74 个场景，覆盖 11 类，包括多实体和多步依赖 |
| `python -m usami simulate --world examples/world.json --scenario examples/scenario.json --out outputs/trace.json` | 五步套餐/席位依赖，Oracle `pass`：4 个合法请求完成、1 个非法请求正确拒绝 |
| `python -m usami evaluate outputs/trace.json --out outputs/report.json` | 独立重新计算，同样 `pass` |
| `python -m usami replay outputs/trace.json --out outputs/final-state.json` | 13 个事件确定性重放，最终 hash 相同 |
| `python -m usami simulate --world examples/world.json --scenario examples/multi-entity-scenario.json --out outputs/multi-entity-trace.json` | 角色降级 → 权限拒绝 → 提升权限 → 关闭续费 → 退款，Oracle `pass` |
| `python examples/demo.py` | 实际验证原始世界、组合执行、Oracle、重放、reset、另一序列及 Validation Manifest |
| `python -m usami validate` | 300 个世界、3 个 Manifest、72 个严格场景及重放全部合法 |
| `python -m usami run-manifest configs/validation-manifest.json --out outputs/validation` | 24 / 24 场景通过，预算固定为每场景 20 次操作 |

以上命令均通过 `.venv/bin/python` 实际运行。README 使用激活后的 `python` 表达等价功能。

seed=42 默认世界：

```text
world_id: world_d7b758c82586402e848a
initial_state_hash: cbdc43984d682555281707a7431c7ed702f0c9bc4a3ebb3346b614f10936e0ec
generator_version: saas-generator-0.1.0
rules_version: saas-rules-0.1.0
config_hash: 47f34c4a7c19d4ea8ddac5c81d2d79a927b0322f76c1d42419d099267705753a
frozen_clock: 2026-01-15T12:00:00Z
```

五步演示的合法性序列由 ReferenceRules 实际计算：`[true, true, false, true, true]`。末步恢复了原套餐与席位，所以该示例最终 hash 等于初始 hash；中间状态改变和非法降级的拒绝都记录在完整事件中。多实体示例产生另一个实际最终状态：`07cb35d13d32b6ac9257f8994ef3cf0a4eca1cc41fb9674727f938a87d2047ea`。

## Oracle 故意错误记录的真实审查

额外用真实 WorldEngine 执行了两个仅验证评分器的人工例子，保存至 `outputs/oracle-checks/`，summary 明确标记 `synthetic_oracle_tests_not_ai_discoveries`：

| 人工输入 | 实际执行 | 独立 Oracle |
| --- | --- | --- |
| Starter 组织改成 6 个席位 | sandbox 实际写入 6 席位 | `valid_request=false`, `operation_correct=false`, `SEAT_LIMIT_EXCEEDED`, 证据 `event_000002` |
| active 订阅的合法取消续费请求 | refuse 模式实际记录拒绝，不修改状态 | `valid_request=true`, `operation_correct=false`, `FALSE_REJECTION`, 证据 `event_000002` |

这两个 report 的 `status=fail` 是预期且已断言的评分器检测结果。它们没有冒充模型轨迹或真实漏洞发现。

## 冻结 Validation

公开文件：`configs/validation-manifest.json`。

```text
split: validation
visibility: public
world seeds: [1000000, 1000001]
world count: 2
scenario count: 24
operation budget: 20 per scenario
manifest hash: 810a668b341815cc5d23000c076b513e9ba3d08acb99e5458ce771fa1bc864f5
```

每个场景从所属世界的独立初始副本开始。运行输出的 summary 记录相同 Manifest hash。当前只是环境和评分基础设施验收，不是任何 Agent 的能力得分。仓库没有提交真正需要保密的最终 Test Manifest；正式 Test 应在方法冻结后由独立托管方生成和保管。

## 交付边界

支持独立 Python API、CLI、版本化配置、完整事件证据、合法快照往返和私人 Manifest 加载。只实现冻结时钟下的 SaaS 业务规则；未实现时钟自动推进、现实计费、部分退款、自然语言授权、LLM 或 Agent/进化/搜索。完整 hash chain 是完整性校验，不是敌手环境的认证签名。授权权威仍由外部受信 harness/Manifest 提供。

还实际使用独立 Validation Manifest 重新审查已保存场景轨迹（CLI `evaluate --manifest --scenario-id`），结果 `pass`。执行 `python -m build` 成功生成 sdist 和 wheel；源码分发包含配置、JSON 示例及测试 fixture，运行产物与私有目录不纳入分发。
