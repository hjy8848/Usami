# VAST-CoEvo 多代与独立 Held-out：首次预注册执行

**C2C：BLOCKED。首次研究 001 在开发 Smoke 的固定子预算处中止。正式训练与 Held-out 均未开始，不存在 H1/H2 的新结论。**

源码提交：`161802f8f4c199230cc0f0c4a1f666dfef332adb`。
Manifest：`ca5aaf66332335cff6e962b691a4003686c9ca55669df6cfe850b69c29f03e58`。

## 为什么中止

我把两组独立 Smoke 的 Token 子预算估低了。预注册 Smoke 上限是 1,000,000 Token；实际完成 144 次模型调用、消耗 961,452 Token 后，剩余额度不足以作下一次请求的保守预留。保护器在发送新请求前中止，未擅自扩充限额，未归咎为模型服务故障。

整体 25,000,000 Token 尚未用尽。加入此前一次连通性检查（128 Token），实际累计 **145 次调用、961,580 Token**。不虚构美元金额：网关没有已核实单价。

## 实际完成了什么

- 用户明确允许本地 RSI 身份确认后继续；专用连接失败的原始检查与授权回复保持原记录。
- 新运行实现通过 **931 项全量测试（252.14 秒）**；新增 13 项，包括真实 Controller 的完整离线流程与 Reflection / Static / Dynamic Gate 重建。
- 预先冻结 2 次独立重复、A/B 各 3 代、配对训练/开发世界、24 个 Held-out 世界及 48 道固定任务，共计划 288 场最终 Service 评价。包括 Smoke 在内共 30 个业务结构 hash 互异的初态，排除原有两批测试世界。
- Smoke A 固定 C0，Customer Reflection 为 0。Smoke B 真实提交 ADD（新增 customer.permission_boundary_probe v1），通过原 Static Gate，选中新的 Snapshot；未调用 Customer 性能 Gate。新经验已核实注入 2 次真实 Customer 请求（CUSTOMER_INJECTION_AUDIT.json）。
- Smoke A 的 Service 候选真实通过原 Static + Dynamic Gate，已经在该 Smoke 内选中。Smoke B 的 Service 候选静态通过，但 Dynamic Gate 未执行完，**没有验收判定且继续选中 S0**。
- 两组各已发生实际 Snapshot 推进，但都没有完成整代 checkpoint；A 在交叉执行中止，B 在 Service 验证中止。不能把它们算作已完成的正式训练代际。

| 类型 | 实际调用 | 实际 Token |
| --- | ---: | ---: |
| Customer | 14 | 85118 |
| Service | 127 | 781272 |
| Customer Reflection | 1 | 15999 |
| Service Reflection | 2 | 79063 |

上述表格仅计实际返回并有 usage 的请求；Controller 的 pending Episode 预算预留不是实际模型消耗，不与本表混算。

## 回放与完整性

实际启动 20 个 Smoke Episode：18 个拥有完整原生业务轨迹并通过精确离线 Replay；2 个中止 Episode 保留模型请求/响应前缀，但未发布最终 World trace，**不能声称具有完整 Episode Replay**。

已有 EvolutionRecord 中的 2 次 Reflection、全部对应 Static Gate、1 次完整 Service Dynamic Gate 均重建一致。B 的第三次真实 Reflection 因后续 Gate 中止而未写入 EvolutionRecord；已从持久化真实请求/响应和原始开发证据重建，逐项匹配原请求及响应，候选 hash 一致。该恢复记录不冒充新调用或已接受更新，见 RECOVERED_SERVICE_B_REFLECTION.json。

REPLAY_AUDIT.json 的 PASS 仅覆盖已完成原件；整体范围与缺失明确见 REPLAY_COMPLETENESS.json（PARTIAL）。API 调用没有未知在途响应，用量均可核实；两条 pending 状态表示业务 Episode 未结束，不代表额外已计费模型调用。

全部失败、原始请求、真实回复、业务工具返回、已完成 Oracle 轨迹和部分执行前缀保留。World、Engine、Reference Rules、Oracle、Service Reflection、Service Evolver、Service Gate 和 Skill Schema 未改动。

## H1/H2 与下一步

Q1–Q5 暂无正式证据。Smoke A 的局部 Gate 接受不表示泛化改善，也不用于挑选正式实验的初始 Service；所有正式运行仍须从同一 C0/S0 开始。

Held-out 只完成离线数据构造和规则可行性证书，没有执行模型、没有查看模型表现或模型运行后的 Oracle 汇总。没有生成空的 HELDOUT_RESULTS.json / STATISTICAL_ANALYSIS.json 来冒充结果。

已向用户提出一次有边界的预算重新预注册申请；尚未执行。提案保留全部旧记录、最多增加一次独立 Smoke，模型、A/B 算法、2 重复×3 代、24 个 Held-out 世界及评分/统计不变。连同此次消耗仍在原 4700 次 / 2500 万 Token 内；初稿见前置目录 AMENDMENT_PROPOSAL.json。进一步用 8 个开发固定任务核算得到均值 32,715 Token，288 场点估计约 942 万 Token，因此初稿 Held-out 604 万子额度也偏低。最新待审建议为新 Smoke 200 万、正式训练每组统一 300 万、Held-out 10,038,420 Token，连同既有消耗仍不超过原总上限；见 AMENDMENT_COST_ESTIMATE.json。这是成本预测而非 Held-out 结果，未执行、未更改现有 Manifest。

本次原始工件位于本目录的 work/、wire-ledger/、source-snapshot/、worlds/，另附压缩归档及 checksum（若已生成）。运行方法见 experiments/vast_coevo/examples/MULTIGEN_HELDOUT.md。
