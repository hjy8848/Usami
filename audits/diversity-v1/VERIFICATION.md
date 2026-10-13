# Diversity Audit Verification

执行日期：2026-10-13（Asia/Shanghai）。审计基线为 main 的
`a4f8fa836d095111ffc5e536b1a7e8681136cad8`。运行未使用 LLM、API Key 或网页。

## 实际运行

```bash
.venv/bin/python -m usami.audit \
  --start-seed 0 --count 1000 --config configs/standard.json \
  --split-worlds 100 --engine-checks 32 \
  --output audits/diversity-v1
.venv/bin/python -m pytest tests/test_audit.py -q
.venv/bin/python -m pytest -q
```

- 新增测试：**25 passed in 4.27s**。
- 完整测试集：**225 passed in 23.56s**（原有 200 项 + 新增 25 项）。
- 主样本：固定 Seed 0–999；1,000 个 Standard 世界；82,699 个原始构造器候选，
  116,503 个步骤。每一步的判定与状态 hash 都经真实 Reference Rules 重算核对。
- Split 分析：使用原有 `create_manifest` 创建各 100 个世界的公开 Demo，Train
  Seed 0–99、Validation 1000000–1000099、Test 2000000–2000099，各 1,200 条任务。
  Config 仅使用已有三个 profile；原有 Split Validator 通过。完整 Config、Seed
  列表和 Manifest hash 在 JSON 内；没有修改已有 Manifest 或发布私有 Test。
- 独立检查实际发布的 Validation：Seed 1000000/1000001，2 世界、24 任务。
- Engine/Oracle/Replay：上限参数为 32，但主样本只有 24 种模板，因此实际检查
  **24 个不同模板的代表**，全部 Oracle pass，真实事件回放与最终状态一致。
  使用外部可信 RequestContext 映射核对授权。没有声称全量候选都执行了 Engine。
- 审计前后以及对照基线 Git blob，10 个核心源文件逐字节一致；其 SHA256 与
  JSON 记录一致。Generator Seed 42 的既有 golden hash 保持不变。

核心比对文件：world/models、generator、rules、engine，protocol，evaluation/
scenario、splits、oracle，events、randomness。新分析代码、测试和文档独立新增。

## 独立进程可重复性

```bash
.venv/bin/python -m usami.audit --count 10 --split-worlds 3 --engine-checks 8 --output outputs/audit-repro-a
.venv/bin/python -m usami.audit --count 10 --split-worlds 3 --engine-checks 8 --output outputs/audit-repro-b
```

两个独立进程生成的 `results.json` 和 `REPORT.md` **逐字节相同**。每次有 871
场景、22 模板、108 决策结构。除此之外，自动测试对固定输入统计、报告、Split
重叠重复计算并检查一致；代表性 1,000 Seed 审计实际运行两次；报告行序修复后重跑，除审计报告模块源码哈希外，全部统计、例子、世界 hash、执行与回放证据完全一致。另已验证从排序 JSON 重新加载可逐字节重建 Markdown。

提交的主要产物：

| 文件 | SHA256 |
| --- | --- |
| results.json | ba8eb6fb443e779d19beabddd277882a24235c7948ff28c46813bccb9983559c |
| REPORT.md | 75d0acdafbe51c8978c78f46e86f6ae596bb67ea416f1a3b3e1c92a40d4cda20 |

## 明确回答 Q1–Q6

**Q1：当前实际观测到多少种场景结构？**

82,699 条候选中有 **24 种匿名关系模板、293 种业务决策结构**。两层签名的
规范与完整例子在结果中，不能仅从操作名序列推导这些数。50 世界时模板已经
达到 24；决策结构从 231 增至 1,000 世界的 293。不能据此证明理论上限。

**Q2：多少是 Seed／ID／参数变化下的重复？**

按模板等价有 **82,675 次重复（99.971%）**，按更严格的决策签名等价有
**82,406 次重复（99.646%）**。相同签名表示本方法保留的业务决策相同，不
表示所有绝对参数都相同。默认 Generator 的实体 ID 与显示名称在不同 Seed
间本身固定，因此不能把这些重复都归因于“替换 ID”；主要是同一构造器在
不同前态、关系和数值参数上重复实例化。重命名干预测试证明签名确实忽略 ID。

世界层面有 985 种角色关系图、1,000 种规范化业务状态关系图；世界多样性高于
局部场景多样性。语义签名 Top 10 占 38.53%，有效多样性为 78.13（不同于
293 个独立类）；模板 Top 10 占 80.81%。重复可用于估计稳定性，但不能计为
新的业务能力覆盖。

**Q3：多少真正的依赖与规则组合？**

**9,951 条场景**具有移除前置状态变更后改变后续合法性／拒绝原因的依赖，
占所有场景 12.03%、多步场景 76.84%；共 **19,922 条观测依赖边、6 种操作对**。
最大测得依赖图深度 2，仅 649 条场景达到；它是包含间接效应的前缀移除图
深度，不是已识别的直接因果深度。实际无依赖多步场景
为 **3,000 条**，均属于过期账单的重复退款链。

出现 **14 种非空实际业务条件共检路径**，其中 13 种包含多个条件；另有
空路径代表在一般性条件处提前拒绝。共检不等于每个规则都独立影响结果。
JSON 另列 9 种潜在多约束违反组合，包括短路遮蔽的条件，它们不计为已执行
拒绝或成功违规。精确的直接跨规则因果交互总数仍无法从这些统计准确识别。
没有跨组织多步状态依赖链；跨组织资源拒绝均为单步。

**Q4：哪些规则与状态组合未充分覆盖？**

23 条参考拒绝条件全部被检查过，但有 **8 条未曾导致拒绝**：规则版本、
非法世界、未知 actor、缺失组织、缺失资源、非 Owner 修改角色、无效套餐、
inactive 目标成员。前两条属于完整性轨道，本来不应靠破坏正常世界制造覆盖；
其余六条是当前候选缺口，已有核心单元测试覆盖不能替代 Benchmark 数据覆盖。
OWNER_IMMUTABLE 虽然有拒绝样本，但构造器没有请求把普通成员改成 Owner，
只覆盖了修改现有 Owner 的拒绝；一个复合条件被检查过不等于各子分支均覆盖。

get_organization、get_invoice、list_members 的候选出现次数为 0。本次样本也
没有退款时间恰好等于窗口的前态观测（可从语义签名频率和例子重算），虽然
生成器允许这个边界。inactive 成员在世界存在，但 role-change 只选择 active
目标。订阅 expired→active、unpaid→paid、成员数量变化和账单—周期关联未实现，
不能通过现有合法写操作到达。拒绝中最多的是 REFUND_WINDOW_EXPIRED（15,000），
PERMISSION_DENIED 为 9,301；不存在“多数拒绝都是同一权限条件”的证据。

**Q5：现有 Train/Test 有多少结构泛化价值？**

世界级留出条件是真实的，不只是 Seed 分离，但候选任务没有结构级隔离保证。
本次 Demo Train 23 模板／175 决策结构；Test 24 模板／168 决策结构。共有
23 模板／132 决策结构，Test-only 为 1 模板／36 决策结构，Train-only 为
0 模板／43 决策结构。Test 样本的 **99.75% 模板、94.25% 决策结构**已在
Train 见过。Test 没有新增共检业务规则集合或依赖操作对。它可以评测实例变化
下的稳定性，尚不足以证明强任务结构组合泛化；这些公开 Demo 数字不能代替
真实私有 Test 测量。当前也没有冻结的标准 Task Train/Test 集。

唯一 Test-only 模板在主样本 Seed 2 已存在：
`scenario_69a185dccfcafc75f7bf`，单步跨组织资源请求；actor 在请求组织为
active Owner，在资源所属组织为 inactive billing_admin，无状态依赖边。
这个例子说明有限 Demo 的 Test-only 类不等同于强制留出的复杂因果组合。

**Q6：下一阶段优先扩展什么？**

先冻结正常 Service Goal 与开放 Customer Discovery 两条独立轨道；按匿名
任务关系、决策分支和真实依赖图划分，而非只换 Seed。先用已有操作补齐查询、
权限/边界分支和目标式角色—账单、席位—套餐组合。业务扩展按优先级为：
**P1 成员生命周期 → 席位/套餐依赖；P2 支付 → 订阅激活/续期；P3 余额/贷项
与跨账单退款资金链**。新状态与依赖须有独立 Reference、状态不变量及程序化
目标验证；完整成本、不可由现有操作组合的原因和验收方案见 ROADMAP。

## 已知局限

- 当前统计对象是原有固定构造器候选；不代表自然语言业务目标或真实 LLM
  对话的多样性，也不估计开放攻击产出。没有使用历史 LLM 轨迹凑结构数量。
- `multi_entity` 候选在 Owner 与目标成员之间切换 actor，Engine 的逐步可信
  请求可以验证它；现有 Service/Interaction 则冻结一个 Customer 身份并拒绝
  身份切换。此类链不等于当前单会话 Service 可直接执行的任务；未来目标式
  基准需明确区分固定身份任务与 Harness 独立认证的多会话权限传递。
- 绝对值被策略关系归一化，数字推理难度与不同组织规模的任务难度可能被
  合并；改变粒度必须升级签名版本。全局状态图精确规范化只支持 ≤6 组织，
  超出明确 Unknown。此处默认 3 组织不受限制。
- 依赖分析识别合法性/拒绝原因变化；信息获取、顾客策略及直接因果深度为
  Unknown。顺序分析只检查整体逆序，没有穷举所有排列。
- 实际共检路径、实际第一拒绝、派生潜在遮蔽条件分开统计；不能以共检数声称
  完整跨规则交互。所有实际样本是合法初始世界和 Reference 状态迁移。
- 只运行当前代码与固定样本；增长趋缓不证明所有可生成结构已经枚举完。
  未读取任何私有测试集，因此私有测试的重叠和泛化结论为 Unknown。
