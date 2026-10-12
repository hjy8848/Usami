# World Explorer 实际验收

日期：2026-10-12。环境：macOS，Python 3.9.6，Node 26.8.2，npm 11.19.1，Google Chrome。桌面验收视口 1440 × 1000；按照用户后续要求，不继续验收手机端。

## 运行结果

| 检查 | 实际结果 |
| --- | --- |
| `.venv/bin/python -m pytest -q` | **106 passed**，16.05s；原有 87 项 + Web API 19 项 |
| `cd web/frontend && npm run build` | TypeScript 检查及 Vite 生产构建成功；1743 modules |
| `cd web/frontend && npm run test:e2e` | **7 passed**，7.4s；真实 Chrome、实际 FastAPI 调用 |
| `web/run.py` 启动与停止 | 自定义 API 8012 / 前端 5174 的 `/api/health` 成功；SIGTERM 后两项子进程退出且端口均释放 |

Python Web 依赖验收版本：FastAPI 0.128.8、Uvicorn 0.39.0、HTTPX 0.28.1、Starlette 0.49.3。核心约束仍为 Pydantic 2.13.5、pytest 8.4.2。前端使用提交的 package-lock.json（Vite 6.4.4）。

## 实际覆盖

- Seed 42 的 WorldState 与 `generate_world(42)` 完全一致。默认 world_id 为 `world_d7b758c82586402e848a`，初始 hash 为 `cbdc43984d682555281707a7431c7ed702f0c9bc4a3ebb3346b614f10936e0ec`。
- 默认统计为 3 个组织、8 个用户、1 个 active 订阅、12 张账单。页面切换组织，成员和账单与 API 的真实实体一致。
- 全世界图有 26 个真实实体节点；节点、Membership 角色与边均逐项对照 WorldState。组织筛选、节点拖动、点击检查、缩放和 Fit View 在浏览器中实际操作。
- Workspace 1 Owner 的 `change_plan → Team` 修改真实套餐字段，Oracle 判正确；Starter 的 `change_seats → 6` 在 Reference 中拒绝、hash 不变。
- 同一个请求在 Sandbox 中实际改变 seats，Oracle 判错误并提供 `SEAT_LIMIT_EXCEEDED` 证据。Before / After 展示引擎原始快照；Reset 恢复初始 hash。
- 先由 Owner 将有效 Billing Admin 改为 Member，再以该 Member 关闭续费：Reference 拒绝且状态不变；Sandbox 执行成功、auto_renew 变化，Oracle 独立检测 `PERMISSION_DENIED`。
- 默认五步套餐场景实际运行，第三步正确拒绝、第五步合法完成，最终 5 / 5 请求正确；API 另验多实体及组合退款场景，前后快照连续且终态与规则派生 hash 一致。
- 退款表单的账单、金额和原始渠道来自实际世界，合法全额退款生成真实 Refund 历史。
- Event Timeline 原始事件与数量匹配；浏览器实际下载含 final 事件的完整 Trace。Replay 调用核心重放、终态 hash 一致；导出及重放之后仍可继续操作。
- 同 Seed / 配置重生成完全一致；换 Seed 改变世界。两个独立浏览器 context 和两个 HTTP Session 的操作、生成和历史互不影响。
- 浏览器不能提交伪造 RequestContext / Oracle，额外字段返回 422；陈旧 hash 返回 409 且不创建事件；预算检查不写入多余请求；未知事件、资源和配置返回明确错误。
- 六个桌面页面无横向溢出。保存并实际查看了首页、关系图、Sandbox、场景与时间线截图；修正了筛选图的状态刷新、图标导航的可访问名称和说明文字对比度。

截图由测试保存到忽略提交的 `outputs/web/`。它们来自运行中的真实应用，不是设计稿。基准核心目录 `usami/` 未修改。

## 已知边界

场景 Run 从生成时的初始状态替换当前历史；Replay 只重放当前受信会话的完整 Trace，外部文件可使用核心 CLI。内存会话要求一个 Uvicorn worker，后端重启会清空世界。Sandbox 不支持核心未实现的技术操作，非法 pre-state 的 Unknown / 已知违规遵循已有 Oracle 语义。手机端保留基础响应式样式，未作为最终验收目标。
