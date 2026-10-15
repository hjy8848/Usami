# Prompt Audit：先测量，不改变运行协议

状态：离线审计完成；新增在线调用 0；没有启动正式进化或压缩 A/B。
本次不改变 Prompt、Retriever、Renderer、Adapter、Customer/Service、Engine、Oracle、进化与评分逻辑。

## 数据与单位

逐条读取 service-repair 原始完成日志（948 次 Agent 调用）以及独立 Service Reflection 原始请求/回复（1 次），合计 949 次；另外独立审计 multigen 首次 Smoke 的 144 次调用，两批不混合比较效果。
输入/输出/推理 Token 使用原始供应商 usage，所有调用 usage 完整。推理 Token 已包含在输出中，不再重复相加。
各组成部分采用 UTF-8 canonical JSON 字节分账，合计等于每条完整请求大小。当前没有模型对应 tokenizer，字节比例不能视作 Token 比例，更不是实际计费拆分。工具 Schema 是对象；将 HTTP JSON 空格变少不代表 provider Token 会减少。
逐调用表保存来源路径/文件哈希/请求哈希、Token、消息数量、组件大小、注入 Skill；原始正文留在历史记录中，不复制另一套。

## 历史实验实际成本

|角色|调用|输入 Token|输出 Token|合计 Token|输入 P90|
|---|---:|---:|---:|---:|---:|
|customer|170|821,034|290,592|1,111,626|5,397.6|
|reflection_service|1|77,109|3,935|81,044|77,109.0|
|service|778|4,778,681|246,223|5,024,904|8,015.5|

总计 6,217,574 Token。Service 输入占自身 Token 的 95.1%。

## Service 请求组成（字节，不是 Token）

|组成|字节|比例|
|---|---:|---:|
|tool_definitions|6,413,131|34.50%|
|conversation_history|3,991,570|21.48%|
|tool_results|3,694,858|19.88%|
|system|2,123,940|11.43%|
|skill|1,970,570|10.60%|
|latest_user|280,886|1.51%|
|request_framing_and_options|111,696|0.60%|

同一请求内完全重复的工具正文累计 44,362 字节，占总请求 0.24%。这是重复暴露量，不能将它直接视为安全可删除量：不同 call_id 必须有匹配结果，相同 JSON 也不证明状态来源/时点相同。
工具正文仅去 JSON 空白的离线候选空间为 289,110 字节，占总请求 1.56%，不是已证实 Token 节省。

## 每轮输入增长（历史 Service，按角色调用序号分层）

|序号|样本数|平均输入 Token|输入 P90|
|---|---:|---:|---:|
|1|104|3,796.3|3,890.7|
|2|104|5,265.5|5,888.0|
|3|103|5,970.3|6,809.2|
|4|100|6,172.9|7,024.7|
|5|95|6,399.6|7,387.4|
|6|76|6,625.5|7,846.5|
|7|63|7,140.0|9,257.8|
|8|45|7,382.1|9,573.2|
|9|38|7,677.9|9,676.0|
|10|24|7,767.6|9,696.6|
|11|17|8,669.0|10,741.2|
|12|9|9,437.2|11,052.0|

各层样本会因终止而变化，不能把跨层均值差当作同一批 Episode 的严格因果增长；逐调用原始表仍可作配对分析。

## 代码核查与候选处理

- Skill：Retriever 已按角色、领域、工具子集、触发词/意图筛选，上限 4 条、6000 字符；Runtime 每次只在 wire request 插入一次，不写回原生历史。历史 Service 778 次只注入 service.state_contract；未发现把四领域 Skill 库整体塞入的现象。通用 Skill 声明多领域不等于注入其他领域专属内容，也不证明每一步均相关。
- Retriever 的关键词扫描包含全部 user/tool 历史；旧话题可能继续触发 Skill。这是相关性风险，尚不能从触发命中直接判定哪些 Skill 可安全移除。
- Service 原生 messages 保留所有历史工具结果和回复；Runtime 没有再附完整 WorldState。get_customer_context 返回身份允许的观察，仍可能较大，但其目录对自主发现未知项目有用途。不能只提供人工预选项目。
- Customer 保留上一轮 action/reply 历史，并在新 user 消息附 last_exchange；存在语义重叠，但不是可以不经验证删除的逐字重复。当前合法观察和独立精确写意图不得自由文本重写。
- 工具定义是目前最大的单项；17 个工具每轮发送是常规无状态接口行为，不能仅因为跨调用重复就省略。未来可验证 JSON Schema 的 title 注释是否必要，但 required/enum/范围/参数结构/工具描述保持；本次没有修改。
- 工具结果 JSON 空白可作为最小 B 组候选：先严格 JSON 解析（重复 key、NaN 等不处理），保留全部字段、原始日志及 call_id，再验证真实输入 Token 和任务结果。本次仅量测，不启用。
- 历史裁剪需要状态版本和依赖失效机制才能避免过期事实；这不是简单去重，当前没有实施。
- Reflection 单次输入达到 77,109 Token，应单列观察；不因为它调用次数少就忽略，也不在本任务修改学习证据。

## 下一步开发验证边界

先用开发集合法/拒绝/多步权限与依赖场景测试 A 原版与 B 工具 JSON 空白版。C 相关性版待逐项证明候选来源后再注册；不为了凑三组强行删历史。冻结相同模型、Snapshot、世界、预算、授权、工具和评分。保存实际输入/输出 Token 与任务成功、正确拒绝、Oracle 违规、授权异常；输入缩短不能代替质量非劣证据。
本次没有新增在线 A/B、没有证明任何删减能提升准确率，也没有将压缩用于正式 A/B 共进化。正式实验前再统一冻结是否采用的 Prompt 组装版本，两训练组完全一致。

## 验证与复现

67 个相关测试通过（新增审计测试 8 个，Runtime/Skill 回归 59 个）。未跑全量回归：本次仅增加独立离线脚本，生产路径无改动。
测试覆盖组件字节守恒、不修改请求、工具配对不删除、歧义 JSON 不压缩、字段值保留、推理不重复计费和缺失 usage 明示。
审计脚本拒绝覆盖已有输出；重跑请指定新输出路径。输入文件需来自原始实验完整目录或对应归档，JSON 统计本身不是原始请求的替代品。

```bash
.venv/bin/python experiments/vast_coevo/examples/audit_prompt_context.py --root outputs/vast-coevo/service-repair-20261015-r1 --kind native --output /tmp/usami-prompt-audit-repair-new.json
.venv/bin/python experiments/vast_coevo/examples/audit_prompt_context.py --root experiments/vast_coevo/results/multigen-heldout-001 --kind ledger --output /tmp/usami-prompt-audit-smoke-new.json
.venv/bin/python -m pytest -q tests/test_prompt_context_audit.py tests/test_vast_runtime.py tests/test_vast_skills.py
```
