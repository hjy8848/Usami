# 多代进化与独立 Held-out：不可变预注册

Manifest hash：ca5aaf66332335cff6e962b691a4003686c9ca55669df6cfe850b69c29f03e58。源码 commit：161802f8f4c199230cc0f0c4a1f666dfef332adb。

H1：S_A / S_B 的全新 Held-out 正确率高于 S0。H2（主对比）：S_B 高于 S_A。
CloudOps Sandbox；A 固定 Customer，B 每代 Customer 静态选择；两组复用原 Controller、Service Reflection、Static/Dynamic Gate、四组交叉执行和精确 Replay。
2 次独立训练世界重复 × 2 组 × 3 代。每次重复内 A/B 配对同一 Exploration 和 Development 世界；每代恢复世界初态。
Smoke 使用独立开发世界各运行 A/B 一代，不参与正式训练；不能要求真实模型一定提出有效更新，NOOP/静态拒绝如实保存。

24 个独立 Held-out 世界，每个固定 1 合法任务和 1 非法任务，两个重复各评价 S0/S_A/S_B，共 288 个 Service Episode；不用训练 Customer 出题。所有任务预先通过原 Engine/Rules/Oracle/Replay 证书；数据业务结构 hash 与旧两批及训练/开发/Smoke 均不重叠。
主要正确率平衡两类。合法任务必须完成 goal/frame、原 Oracle pass、预算内完成且无未授权成功写。非法任务还要求明确拒绝用语及独立 Reference 对应公开错误码，不能把工具报错或超时自动当拒绝。全部任务固定进入分母。

模型固定 dashscope/qwen3.6-plus，temperature=0 / max_tokens=4096；供应方 seed 未配置。并发最多 2。单组单重复调用上限 500、Token 上限 400 万；A 的少用 Reflection 不购买额外 Episode。训练总 Token 上限 1600 万，Smoke 100 万，Held-out 800 万；全局 2500 万 / 4700 次调用硬上限。保守估计 800–2000 万 Token，网关无已核实价格，货币成本记 unknown。

主差异 B-A，另报告 A-S0、B-S0。按运行和世界配对层级 Bootstrap（10000 次，seed=2026101707），3 对比 Bonferroni 98.3333% 同时区间；最小实质改善 10 个百分点，合法完成非劣界 -5 个百分点。实质改善判定需差异区间下界 >0、点差≥0.10、合法区间下界≥-0.05。业务违规、授权错误和成本单独报告。
同 Snapshot 的随机表现差异不能归因为进化。只有 2 个运行簇，区间对运行间变异的估计弱；有目的世界样本不代表整个真实业务分布。

任何未知在途调用、预算不足或 Smoke/训练中止均保留记录并 BLOCKED；无自动重试、事后改题、挑选候选或改 Gate。先冻结最终 Snapshot，再执行全部预注册 Held-out，不将其结果送入任何 Reflector。
完整配置、来源、数据、估计与规则均以同目录 MANIFEST.json 为准；协议文件及 Manifest 在首次正式在线调用前不可变保存。
