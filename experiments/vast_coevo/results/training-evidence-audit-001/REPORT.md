# 正式开发错误为何没有进入 Service Reflection

**结论：Customer 实际发现了错误；错误出现在最后一代 Service Reflection 之后的交叉执行，未被任何正式 Service Reflection 使用。** 本次只有离线审计，新增在线调用 0，未读取 Held-out 结果，未修改算法、历史实验或 Skill。

## 实际证据

|范围|Episode 数|Oracle 成功业务违规|进入 Service Reflection|
|---|---:|---:|---|
|A/B 正式开发全部|32|2|仅其中 16 场|
|四次 Reflection 的输入|16|0|是|
|反思后的开发交叉执行|16|2|否|

两次违规来自 B 组第 2 代更新后的 Customer。它明确要求在依赖仍停止的情况下启动下游实例，Service 实际执行成功，独立 Oracle 判定 DEPENDENCY_NOT_RUNNING / RUNNING_DEPENDENCY_STOPPED。两条失败 fingerprint 相同，是 **2 次发生、1 种独立根因**，不是两个新错误类型。两次真实 prestate/poststate hash 也相同。

|Episode|结束状态|Reflection 成员|
|---|---|---|
|`g1.r0-B.cross.selected_parent.repeat-0-0`|llm_budget_exhausted|[]|
|`g1.r0-B.cross.selected_selected.repeat-0-0`|CUSTOMER_OUTPUT_INVALID|[]|

两条失败都已再次通过原 Adapter 的精确 Replay。第二条 Episode 后来以 CUSTOMER_OUTPUT_INVALID 结束，但它此前已经发生的业务违规仍真实存在；不能因为结束状态不佳就抹掉已验证事件。

## 顺序与证据流

Controller 的当前顺序是：当前 Customer 探索 → Customer Reflection/静态选择 → 选中 Customer 探索 → Service Reflection/选择 → 四组交叉执行 → 下一代。
`vast_coevo/evolution/controller.py:233` 只向 ServiceEvolver 传入当代 current + selected；`vast_coevo/evolution/evolvers.py:44` 再追加当代合法/拒绝任务。每次共 4 个 Episode，四次都没有失败。
交叉执行在 `controller.py:248` 才运行，因此不能出现在已经结束的该代 Reflection 输入中。实验恰在第 2 代结束。
另外，下一代再次从新 current + selected 构造输入，当前 Evolver 没有自动查询 Archive 回收历史 cross 失败。因此即使增加代数，也不能保证这两条已发现错误被利用；可能通过再次探索重现，但不能把“可能重现”当成已建立的证据传递机制。
这不是 Oracle 漏判、日志丢失或 Reflection 序列化丢掉字段。完整错误在原始证据中；问题是哪些开发证据在什么时点被选择进入学习。

## 同时确认的覆盖限制

正式自主探索只有 **1 个不同初态世界**，在 A/B、两代和交叉标签间重复；另 1 个不同世界提供固定合法/拒绝回归任务。多次 Episode 不等于多个不同业务世界。
这是开发覆盖较窄的事实，不能由此单独推断模型能力差或它必然导致某次 NOOP。反思前的探索没找到错误、反思后的 C1 探索找到了错误，这两个事实必须分别报告。

## 更准确的结论与后续边界

“四次正式 Service Reflection 没收到错误”仍然正确；“训练阶段 Customer 从未发现错误”则不正确。实际是：**C1 在开发交叉执行找到依赖错误 → Archive 保存 → 本轮没有后续 Reflection 消费 → S0 保持不变。**
这提供了 C1 在该开发世界能提出有效依赖探针的具体证据，不足以证明跨场景或稳定发现能力提高。
下一项应明确开发失败证据的跨阶段/跨代回收规则，包括来源分区、Replay、Service 版本兼容、根因去重和预算；仍保持每代单次 Reflection 与原 Service Gate。不能把这轮 Held-out 错误反向用于选择这轮候选。本次没有实施新的学习协议或新增训练。

## 复现与产物

`AUDIT.json` 保存 32 个正式 Episode 的事件、原始 Customer action、证据 hash、四次 Reflection 成员映射及两次目标 Replay 结果。审计只读取 work/r0-A 与 work/r0-B，不读取 evaluation/ 或 Held-out 统计，不创建模型 transport。原始记录不变。
```bash
.venv/bin/python experiments/vast_coevo/examples/audit_training_evidence.py --root experiments/vast_coevo/results/multigen-heldout-recovery-002 --output /tmp/training-evidence-audit-new.json
```
