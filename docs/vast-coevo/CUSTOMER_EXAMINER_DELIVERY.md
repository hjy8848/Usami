# Customer Examiner v1 交付记录

## 已实现

四个领域均支持全局考官构造：完整模板世界和经 Replay 核验的开发轨迹 → 一次 `submit_exam` → 原生不变量 / Reference 证明检查 → 写入不可变冻结记录 → 原 Service 执行 → 原 Oracle 与精确 Replay。考官可以新增实体、修改状态和关系、选择执行身份及组合授权和目标；不能修改业务规则。Service 不接收完整世界、考官分析、历史 Oracle 或 witness。

递归训练第一代先运行配置的原生 Service Task。双方 Reflection 消费初始任务和本代正常探索证据；下一代加载上一代真实选中 Snapshot 与已验证轨迹。Customer 仍只用 Static Gate 选择版本，Service 保持原 Static + Dynamic Gate。已知错误回归使用原冻结题目，不重新出题。未启用新协议的旧配置保持旧行为。没有修改四领域 World、Engine、Reference、Oracle、原生 Service 模块或历史实验文件。

## 文件

- `integrations/usami/examiner.py`：构造协议、原生证明、隔离执行、评分与 SaaS 冻结世界加载适配。
- `integrations/usami/adapter.py`、`domains.py`、`evidence.py`：协议分派、开发轨迹来源核验、不可变冻结、精确授权投影、Replay 与原题回归。
- `vast_coevo/evolution/controller.py`：初始任务及跨代考官上下文接入。
- `vast_coevo/evolution/gates.py`：拒绝使用重新出题的场景做 Service 配对验收；评分条件不变。
- `vast_coevo/models.py`：明确区分模板与实际执行世界 / 身份，缺省不改变旧 Hash。
- `vast_coevo/reflection/reflector.py`：仅在新考官协议下说明 Customer 的构造职责；Service Reflection 不变。
- `experiments/vast_coevo/examples/examiner.py`、`examiner-plan.json`、两份 `examiner-*-library.json`：小闭环 CLI、递归训练配置、按原算法生成的 Library Snapshot。
- `tests/test_examiner.py`：四领域真实 Engine / Oracle / Replay、构造失败、模型异常、预算、授权、历史隔离、两代递归及冻结边界测试。
- `CUSTOMER_EXAMINER.md`：运行说明和协议边界。

## 验证

- 全量回归：973 passed，292.76 秒。
- 全量之后补充冻结记录篡改、固定 Service 验收场景、single-use witness 边界测试，并运行相关回归：53 passed，32.32 秒。
- JSON Schema、随附 plan 和两份 Snapshot Hash 校验通过。
- 旧网页发布样例 Replay 保持通过，没有重写历史 source pins。

## 真实联调：仍有外部阻塞

用户明确授权后，以 `dashscope/qwen3.7-plus` 完成一次限定联调。目录：`outputs/vast-coevo/examiner-v1-smoke-001/`，保留在本地，不公开原始网关记录。

- 初始 CloudOps Service Task 完成，6 次模型调用、8 次业务工具调用。
- 考官请求调用 1 次，网关返回 HTTP 400，没有模型回复和有效提案；未调用后续 Service，未自动重试。
- 两场记录均完成证据保存及离线 Replay，失败请求可精确重放。
- Service：input 25,818 / output 1,556 / total 27,374 Token。
- Customer：provider usage 缺失，费用与 Token 未知，不按 0 记账。
- Reflection 0；Held-out 0。

因此，代码接通与离线验证已经完成，不能宣称真实模型已成功自主构造并执行新题，也不能据此宣称进化收益。HTTP 400 的具体原因尚未确认；原客户端不保存原始 HTTP 错误体，本次没有放松其脱敏策略或猜测根因。

该次联调目录包含 `manifest.json`、`summary.json`、`replay.json`、原始请求 / 回复 / 工具 / Oracle、预执行 `exam-frozen.json`，以及包含 161 个 pinned 模块的 `source.tar.gz`。后续修补 witness 的单次授权边界后，已从该源码包单独解包再次完成两场 Replay。复现该次历史记录须使用其源码包中的 CLI；不能拿新源码绕过旧 pins。

下一步是单独核对网关对本次构造请求的支持情况，再明确登记新一次联调；本次失败记录不覆盖、不删除。
