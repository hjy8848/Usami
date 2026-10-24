# 开放式 RSI 的 World–Challenge 关系可见性缺口

**记录日期：** 2026-10-25

**范围：** 仅记录真实模型运行中，Challenge Designer 看不到冻结 World 的匿名订单关系、因而提出无法 Ground 的挑战这一问题。

## 结论

这是一个 **Designer 输入契约与可观测信息设计问题**，不是 Grounder 错误，也不只是模型输出格式错误。

当前 Challenge Designer 能看到某个训练 World 分布里有哪些商品 family、issue、数量和退货属性，但看不到这些商品行如何分属顾客和订单。它可以提出 `same_order`、`different_order` 这类结构关系，却无法据当前输入判断关系是否在目标 World 中成立。Grounder 随后按真实冻结 World 检查并正确拒绝无法绑定的挑战。

模型仍需对自己提出的约束负责；但若输入没有提供关系结构，不能把这次失败只归咎于模型“不会出题”。

## 一次真实运行的证据

运行使用真实 `dashscope/qwen3.7-plus` 模型，共完成两次模型调用：一次 World proposal，一次 Challenge proposal。没有使用预写的 World 或退款题模板。

| 运行证据 | 标识 |
| --- | --- |
| World period | `ca3954368f74fd45c2e26447ca9c82d758a1ffb98d2579bf9926775e53bd14ac` |
| 构造后的 World hash | `92fe29549eb51c23acb974d0c578ad720fc3fb16acf5d01dd93d9943a0cc5747` |
| Challenge hash | `7b572fae85b87f12808851f496e39bf0d21a5b4df9693823a21853587152bf97` |
| RSI Host run | `0b260cb2c66c42b984ca456d0a8b5d68` |

### World proposal

World Designer 提交了三位顾客、三笔订单、四条商品行、三种 SKU、两个仓库及相应问题和业务范围。原生 Usami Builder 对提案完成实例化，并以 `SAT` 通过冻结 World 的构造约束。

生成的关系结构为：

- Alice 的 `order-1` 同时包含一条 `damaged laptop` 和两件 `wrong_item mouse`。
- Bob 的 `order-2` 包含一条 `missing_parts monitor`。
- Carol 的 `order-3` 包含另一条 `damaged laptop`。

Builder 负责在模型给出的 ScenarioDraft 范围内选取具体合法数值并创建内部运行时 ID；World 的顾客、订单及商品行组合来自实际模型提交。

### Challenge proposal

Challenge Designer 提出一个含三个业务目标的抽象挑战：

1. 退款一条损坏笔记本商品行。
2. 换货一条缺少零件的显示器商品行，并要求它与笔记本在同一订单。
3. 补发两件错发鼠标，并要求鼠标与笔记本位于不同订单。

### Grounding 结果

原生 Grounder 检查了一个冻结训练 World，结果为：

| 字段 | 结果 |
| --- | --- |
| 认证回执 | `UNVERIFIED / NO_MATCH` |
| 考察 World 数 | 1 |
| Grounder 绑定组合数 | 0 |
| 搜索是否截断 | 否 |
| Grounded candidates | 0 |

失败原因是关系约束与实际 World 冲突：Alice 的笔记本和鼠标在同一订单；显示器属于另一位顾客 Bob。没有同一位顾客同时拥有挑战要求的笔记本和显示器，更不可能同时满足两个订单关系。

这不是 `REFERENCE_UNSAT`：挑战还未 Ground 成具体任务，故尚未进入 Compiler 或 Reference 可达性证明。

## 代码路径与问题所在

1. [`WorldPopulation.catalogue()`](../../integrations/rsi_usami/open_world.py) 聚合并公开 `families`、`issues`、`observed_line_kinds` 等词汇和计数。实现注释明确表示它不公开逐 World 的实体关系、alias 或答案。
2. [`OpenChallengeBridge.public_view()`](../../integrations/rsi_usami/open_world.py) 将该聚合目录和认证能力清单提供给 RSI Host。
3. Challenge 的模型输入因此不含匿名的“哪个顾客的哪个订单包含哪些商品行”关系，却允许 Challenge 提交多个 selector 和订单关系。
4. [`ground_challenge()`](../../usami_v2/scenarios/grounding.py) 按每个顾客的真实订单逐项匹配 selector，再检查 `same_order` / `different_order` 关系。它返回 `NO_MATCH`，且 `search_truncated=false`，符合当前 World 的事实。

本次诊断将 Grounder 的 `max_worlds` 设为 1，因此模型提出的挑战只在该冻结 World 上检查，没有第二个 World 可供匹配。这是本次最小运行的预算配置；它不是造成该 World 中关系冲突的根因，但意味着本次没有跨 World 找到另一个可 Ground 实例的机会。

就本次实际提供的目录而言，模型可见 `world_count=1`、商品 family / issue / quantity / return requirement 的汇总列表，以及任务认证能力；它看不到 Alice、Bob、Carol 各自拥有哪些订单行，也看不到上述商品行的订单共现关系。

## 对研究流程的影响

本次执行在 `PROPOSE_CHALLENGE` 后停止。没有产生认证任务，所以没有运行 `RUN_BASELINE`、`PROBE`、Service Episode、Oracle、Episode Replay 或 Skill 更新。此次结果证明了真实 World proposal/build 与真实 Challenge proposal/grounding 接口已被触发；**它没有证明完整 RSI 执行闭环已跑通**。

## 针对此问题的修改目标

让 Challenge Designer 得到足以设计可 Ground 关系任务的、**匿名且只来自获准训练 World 的拓扑视图**，例如：

- 使用稳定的符号别名表达顾客、订单和商品行之间的从属关系；
- 商品行只公开 Grounding 所需的业务属性，如 family、issue、quantity、return requirement；
- 不公开真实运行时 ID、Reference witness、隐藏 Oracle 判断或独立测试数据；
- 挑战仍须经过现有 Grounder、原生 Compiler、Reference / Task Certification；无法匹配的挑战仍应被拒绝。

World 在一次任务执行期间继续冻结。公开匿名拓扑只帮助 Designer 对目标训练 World 提出有根据的挑战，不改变 World、业务权限或认证规则。

## 验收标准

1. 给定本次这类具有跨顾客、跨订单关系的 World，Challenge 模型上下文能区分“同一订单”和“不同订单”的可用结构，但看不到内部运行时 ID 或 Reference 答案。
2. 与公开拓扑一致的抽象挑战可以 Ground；不一致的挑战仍返回 `NO_MATCH`，不能通过放宽 Grounder 规则被接受。
3. Grounded 任务继续由现有 Compiler 和独立 Reference 认证，并沿 RSI 原有流程执行；训练与 validation / held-out 数据隔离不变。
4. 真实模型测试逐项记录其输入视图、挑战 proposal、Grounder 回执和后续阶段是否启动，且不把确定性提案夹具当成模型自主出题证据。

## 可复查的运行记录

- World 生成记录：`outputs/rsi-open-real-designer-min-20261025-001/world-period.json`
- Challenge 认证记录：`outputs/rsi-open-real-designer-continue-20261025-001/native-certificates/cd35cae011702cd65e06c8504b10cd86af1306d782ce6e0eadaf3e3fe33dc292.json`
- RSI Host 事件链：`outputs/rsi-open-real-designer-continue-20261025-001/rsi-core-archive/19fe04d78e8311aa272e590c460ffebacd01866c36fce8d564b338abdf9cd576.json`
- 本次诊断摘要：`outputs/rsi-open-real-designer-continue-20261025-001/run-summary.json`

上述运行产物位于本地 `outputs/`，由仓库 ignore 规则排除，不随本文件提交。记录的模型用量为 2 次调用、5,334 输入 Token、4,385 输出 Token。
