# Customer Static-Only Selection：实现与验证

状态：**EXECUTED**。基线提交：`7aa3f96cb8a12b708a19a3da26bb570ec8eb9ef6`。

本轮只简化 Customer 的选择机制，没有运行真实 LLM 实验，没有重评或重新选择历史 C1。

## 实际机制

Customer Exploration 的开发证据仍需通过独立 Replay，再进行原有一次 Reflection。SkillPatch 通过原 StaticSkillGate 后，按原 apply_patch 和 LibraryStore 完成内容哈希、版本冲突检查及不可变发布，直接选中候选。静态失败、提案失败、发布完整性错误保留旧版；NOOP 不生成 Snapshot。

Customer 更新记录明确标记 `customer_selection=customer-static-only-v1` 和 `static_gate_passed_snapshot_updated`，`dynamic_validation` 为空。未运行性能比较的领域不标记为已验证。即使候选后续诊断表现更差，或 QGD 为 REJECT / INCONCLUSIVE，也不能撤销其版本选择。

Controller 在保存 Customer 更新记录后加载其 selected_snapshot_hash，Service 阶段、交叉执行及下一代使用实际选中版本。底层预算、证据、协议或未知在途调用出错仍按原机制中止，已持久化的静态选择不作性能回滚。

Service 的一次 Reflection、正常任务预检、Static Gate、Dynamic Gate、已知错误修复、合法任务与正确拒绝、授权检查、Snapshot 接受/回滚均保留。Service 的 accepted 与 Customer 的静态 accepted 含义不同，不能混算为经性能验证的进步。

## 诊断与成本

默认进化不再执行 Customer 的父版/候选性能验收 Episode；原探索、Service 验证与交叉执行仍存在。QGD 和 Probe Evaluator 的原代码与公式不变。

显式 `python -m integrations.usami ... diagnose-customer` 复用原 DynamicGate.customer，固定 C0/C1/S0，只做配对诊断；该命令会调用模型。诊断独立写入 `diagnostics/ID/`，保存协议、配置哈希、源码哈希、Snapshot、结果与成本；Episode 的请求、响应、Token、工具和 Replay 仍在原 Evidence / Native Artifact 中。诊断不能发布候选或更新进化历史，失败保留记录且不重复调用。离线 `replay_customer_quality.py` 可重建已有 QGD 结果，不调用模型。

具体命令及成本口径见 `docs/vast-coevo/CUSTOMER_STATIC_ONLY.md`。本轮 CLI 测试使用明确标注的确定性响应，不是在线研究结果。

## 修改文件与原因

| 文件 | 修改原因 |
| --- | --- |
| `vast_coevo/evolution/evolvers.py` | Customer 静态通过后直接发布/选择，移除其性能前置条件与选择调用；Service 路径保留 |
| `vast_coevo/evolution/models.py` | 版本化 RunConfig v2 与 Customer 选择标记；禁止新静态选择记录携带性能 Gate；旧可选字段不补写 |
| `vast_coevo/evolution/controller.py` | 拒绝用新代码继续执行历史 v1 run，避免混用选择协议 |
| `vast_coevo/evolution/gates.py` | 仅澄清 Customer 方法为显式诊断，未改评价公式或 Service 方法 |
| `integrations/usami/cli.py` | 新运行显式静态选择；新增独立诊断命令，复用原预算日志/Replay；诊断不发布 Library |
| `tests/test_customer_static_selection.py` | 性能退化仍选中、诊断失败隔离、两代传递、历史哈希、CLI 成本/重复调用测试 |
| `tests/test_vast_evolution.py` | 按新 Customer 语义断言；将被拒候选不占版本的测试保留在 Service 未修复错误场景 |
| `tests/test_customer_quality_gate.py` | QGD 配置不阻止静态发布；显式保存 INCONCLUSIVE 后不改变已选版本 |
| `tests/test_vast_controller.py` | 预算耗尽发生在静态选择之后时，保存并恢复实际已选 Customer |
| `tests/test_vast_domain_protocol.py` | 静态接受不冒充执行覆盖；历史原始记录 hash 仍原样核验 |
| `tests/test_vast_real_gates.py` | 四域真实 Engine/Oracle 验证 Service，Customer 改为静态选择 |
| `experiments/vast_coevo/configs/{cloudops-pilot,cloudops-protocol-v2-pilot,cloudops-scoped-pilot,four-domain-development}.json` | 示例显式声明 customer-static-only-v1，未改业务/预算/模型配置 |
| `docs/vast-coevo/CUSTOMER_STATIC_ONLY.md`、`PROTOCOL.md`、`README.md` | 新选择逻辑、诊断命令、兼容性及语义 |
| `docs/vast-coevo/{ARCHITECTURE,CUSTOMER_PERFORMANCE,CUSTOMER_QUALITY_GATE,IMPLEMENTATION,METHOD,PROBE_READINESS_V2,SCHEMAS}.md` | 加当前机制提示，避免把历史 Customer Gate 文档误作当前选中条件 |
| 本目录 `CODE_AUDIT.json`、`REPORT.md`、`pytest.log` | 本次离线实现核验，不覆盖旧实验证据 |

## 测试与一致性

全量命令：`.venv/bin/python -m pytest -q`，结果 **918 passed in 244.14s**；原始输出见 `pytest.log`。

相关回归首批 127 项通过，扩展选择/诊断回归 61 项通过，最终静态选择与历史兼容专项 25 项通过。测试为同一实现的不同覆盖集合，不相加冒充更多独立样本。`git diff --check` 通过。

| 要求 | 覆盖 |
| --- | --- |
| A：性能下降仍更新 | 静态选中后显式诊断出现 valid_actions_decreased，选择和 Snapshot 均不变 |
| B：Static Gate 失败 | 错误版本、安全约束和具体资源标识拒绝，零动态调用 |
| C：NOOP | 旧 Snapshot 保持，无候选或虚假版本 |
| D：诊断隔离 | 负面 legacy 诊断、实际 QGD INCONCLUSIVE、Replay 失败/诊断失败均不能改选择 |
| E：Service Gate 不变 | 未修复已知错误的候选继续拒绝且不占发布版本；修复候选按原检查接受 |
| F：多代推进 | 两次 Customer 更新进入 Service 输入、交叉执行及下一代；预算/缓存恢复/精确 Replay 仍验证 |

`CODE_AUDIT.json` 核验 Service DynamicGate.service、Service 正常任务预检和 Service 动态调用参数 AST 与基线一致。World、Engine、Reference Rules、Oracle、Reflection、Skill Schema/Static Gate、Evidence、Snapshot/Run 存储代码以及所有此前已跟踪的实验结果均未修改。

## 兼容性与限制

RunConfig v1 和旧 EvolutionRecord / StoredEvolution 保持序列化与内容 hash；历史真实记录仍核对原 hash `ea4da0918766221f06d4c294d6ee95da71bef154d70044884130cbf4fed1858b`。精确历史 Replay 仍需要原源码 pin；历史 v1 run 继续执行须用原提交或源码快照，新机制使用新 run ID 和 v2 配置。

本次没有新的性能收益或泛化结论，也没有新的真实 LLM 调用。机制功能上无待解决阻塞；研究者仍需单独分析诊断结果，静态接受本身不保证有效探索或 Service 更强。

代码、测试和本报告属于同一 Git 提交；用 `git log -1 --format=%H -- experiments/vast_coevo/results/customer-static-only-001/REPORT.md` 查询该完整提交 SHA。
