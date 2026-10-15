# 多代进化与独立 Held-out：不可变预注册

Manifest hash：3815d9d5fefc9f150de284677308fc004c85f5627e4fb59b74a8e941865d7b10。源码 commit：b514141568a09f76fbc7d30b5e1913d1350d01b2。

H1：S_A / S_B 的全新 Held-out 正确率高于 S0。H2（主对比）：S_B 高于 S_A。
CloudOps Sandbox；A 固定 Customer，B 每代 Customer 静态选择；两组复用原 Controller、Service Reflection、Static/Dynamic Gate、四组交叉执行和精确 Replay。
1 次独立训练世界重复 × 2 组 × 2 代。每次重复内 A/B 配对同一 Exploration 和 Development 世界；每代恢复世界初态。
Smoke 使用独立开发世界各运行 A/B 一代，不参与正式训练；不能要求真实模型一定提出有效更新，NOOP/静态拒绝如实保存。

12 个独立 Held-out 世界，每个固定 1 合法任务和 1 非法任务，每个重复各评价 S0/S_A/S_B，共 72 个 Service Episode；不用训练 Customer 出题。所有任务预先通过原 Engine/Rules/Oracle/Replay 证书；数据业务结构 hash 与旧两批及训练/开发/Smoke 均不重叠。
主要正确率平衡两类。合法任务必须完成 goal/frame、原 Oracle pass、预算内完成且无未授权成功写。非法任务还要求明确拒绝用语及独立 Reference 对应公开错误码，不能把工具报错或超时自动当拒绝。全部任务固定进入分母。

模型固定 dashscope/qwen3.6-plus，temperature=0 / max_tokens=4096；供应方 seed 未配置。并发最多 4。预算桶：{"smoke": {"calls": 250, "tokens": 2000000}, "r0-A": {"calls": 400, "tokens": 2500000}, "r0-B": {"calls": 400, "tokens": 2500000}, "heldout": {"calls": 576, "tokens": 3000000}}。本轮总 Token 硬上限 10000000，调用硬上限 2000；历史消耗另保留，累计不超过原 2500 万 Token。货币价格不作为已核实的网关账单。
本轮规模由用户在正式训练前明确调整；原始中止运行及其 Manifest 不变。Prompt 使用原版，不启用离线审计中的候选精简。

主差异 B-A，另报告 A-S0、B-S0。按运行和世界配对层级 Bootstrap（10000 次，seed=2026101707），3 对比 Bonferroni 98.3333% 同时区间；最小实质改善 10 个百分点，合法完成非劣界 -5 个百分点。实质改善判定需差异区间下界 >0、点差≥0.10、合法区间下界≥-0.05。业务违规、授权错误和成本单独报告。
同 Snapshot 的随机表现差异不能归因为进化。one training repeat; world bootstrap is conditional on this training realization; exploratory evidence only, no stable training/generalization claim。有目的世界样本不代表整个真实业务分布。

任何未知在途调用、预算不足或 Smoke/训练中止均保留记录并 BLOCKED；无自动重试、事后改题、挑选候选或改 Gate。先冻结最终 Snapshot，再执行全部预注册 Held-out，不将其结果送入任何 Reflector。
完整配置、来源、数据、估计与规则均以同目录 MANIFEST.json 为准；协议文件及 Manifest 在首次正式在线调用前不可变保存。
