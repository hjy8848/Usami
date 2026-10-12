# Usami World Explorer

本地交互式 SaaS 业务世界探索器。FastAPI 调用已有 Usami Python API，React 页面展示真实 WorldState、操作事件和独立 Oracle；前端不实现业务规则。桌面端优先。

## 安装与启动

从仓库根目录运行，需要 Python 3.9+、Node.js 20.19+（或 22.12+）与 npm：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[web,dev]' -c constraints-tested.txt
cd web/frontend
npm ci
cd ../..
python web/run.py
```

打开 <http://127.0.0.1:5173>。一键启动默认使用 API 8001、前端 5173；Ctrl+C 停止两项子进程。端口被占用时脚本会明确报错，可以设置 `USAMI_BACKEND_PORT` / `USAMI_FRONTEND_PORT`。

也可以在两个终端分别运行，支持后端热重载：

```bash
# Terminal 1: 仓库根目录，激活 .venv 后
uvicorn web.backend.app:app --reload --host 127.0.0.1 --port 8000

# Terminal 2
cd web/frontend
npm run dev
```

Vite 默认将 `/api` 代理至 8000。使用其他 API 端口时，例如：

```bash
USAMI_BACKEND_URL=http://127.0.0.1:8001 npm run dev
```

静态构建后也可以只运行一个 Python 服务（启动时检测 `dist`）：

```bash
cd web/frontend
npm run build
cd ../..
uvicorn web.backend.app:app --host 127.0.0.1 --port 8001
```

此时打开 <http://127.0.0.1:8001>。页面内部导航不依赖 URL 路由。停止再启动后端会清空所有内存会话。

## 五分钟探索

1. **World Overview** 默认生成真实 Seed 42 世界：3 个组织、8 个用户、1 个 active 订阅、12 张账单。组织卡片可进入详情；点击成员、账单和规则可查看原始实体。
2. **World Graph** 从当前世界生成节点与 Membership 角色边。可以筛选组织、拖动、缩放、适应画布，以及点击节点或成员关系查看数据。
3. **Operation Playground** 选择 Workspace 1 / Owner，执行 `change_plan → Team`。查看修改的字段、Before / After 和独立 Oracle。Reset 后执行 `change_seats → 6`，Reference 应拒绝；在 Sandbox 中重复，席位会改变，Oracle 报告违规。也可尝试退款、角色修改和关闭续费。
4. **Scenarios** 默认显示五步套餐组合：升级 → 增席 → 降级被拒 → 减席 → 再次降级。Run 后点选每一步，比较真实连续状态与由 Reference Rules 推导的预期结果。
5. **Event Timeline** 查看请求、操作、评分及其完整 JSON；Export Trace JSON 导出完整轨迹，Replay Trace 调用 Python 确定性重放并核对当前状态。

生成器支持 Seed、用户数、组织数和已有 profile。相同 Seed、配置及版本产生相同初始 hash。Generate 会创建新的初始状态并清除操作历史；Reset 恢复本次生成的初始快照。模拟业务时间来自 WorldState 的冻结 UTC 时钟。

## 结果与边界

- Executed / Rejected 表示实际执行结果。`valid_request`、`operation_correct`、`violations` 和 `evidence_event_ids` 全部来自现有独立 Oracle；执行成功不等于业务正确。
- Sandbox 只复用核心实验执行器：可执行技术上支持但业务上违规的操作。它不是 Agent、攻击发现或真实支付系统。
- 违规状态可能使后续请求合法性为 Unknown；已证明的不变量违规仍可使 `operation_correct=False`。页面保留所有原始证据。
- 场景从本次生成的合法初始世界派生，Run 会替换当前历史，以保持场景边界和连续状态。不是追加到任意实验状态；界面对此有明确说明。
- Replay 使用当前会话导出的完整 Trace，通过 `replay_trace()` 实际执行；不接受浏览器上传授权或 Oracle。导出的 Trace 也可通过核心 CLI `python -m usami replay path/to/trace.json` 重放。
- 导出及重放使用引擎副本收尾，当前探索会话仍可继续操作。核心 ReferenceRules、Generator、Engine、Oracle 与 Replay 的业务语义均未修改。

## 会话与 API

每个浏览器 cookie 对应独立内存世界、事件链和后端权威请求表。后端根据用户明确选择构建 RequestContext，拒绝浏览器额外提交 context 或 Oracle 字段。cookie 为随机能力标识、HttpOnly、SameSite Strict，有效期六小时；服务端回收闲置六小时的会话，最多保留 64 个。当前会话过期后重新加载页面会创建默认新世界。

操作使用当前 state hash 检查陈旧状态；冲突返回 409 并刷新界面。错误返回 401 / 404 / 409 / 422 / 503，不注入示例数据。数据只存在单个 Python 进程内，因此使用一个 Uvicorn worker；不提供数据库、账号或公网部署。

| API | 用途 |
| --- | --- |
| `POST /api/sessions` | 建立独立会话，默认 Seed 42 |
| `GET /api/world` | 状态、组织关系、摘要、事件和 Oracle |
| `POST /api/world/generate`, `/api/world/reset` | 生成与恢复初始世界 |
| `GET /api/world/graph?org_id=...` | 真实实体与关系 |
| `POST /api/operations` | 五种业务写操作，reference / sandbox |
| `GET /api/scenarios`, `POST /api/scenarios/run` | 派生和执行已有组合场景 |
| `GET /api/events/{event_id}` | 事件与完整前后快照 |
| `GET /api/export/world`, `/api/export/trace` | 下载 JSON |
| `POST /api/replay` | 确定性执行与 hash 核对 |

交互式 API schema 见后端 `/docs`。

## 测试

```bash
# 仓库根目录，安装 .[web,dev] 后
python -m pytest -q

cd web/frontend
npm run build
npm run test:e2e
```

端到端测试默认使用已安装的 Google Chrome，在独立浏览器 context 中实际操作；测试自动启动 8001 / 5173，或复用这两个地址的现有 Usami 服务。没有 Chrome 时可安装 Playwright Chromium：`npx playwright install chromium`，然后 `USAMI_BROWSER_CHANNEL=chromium npm run test:e2e`。测试启动的后端使用仓库根目录 `.venv/bin/python`。

验收覆盖真实实体、图筛选/拖动/缩放、合法转换、非法拒绝、Sandbox 检出、组织权限、多步组合、原始事件、下载与重放、Seed 一致性和浏览器会话隔离。实际测试结果与版本见 [VERIFICATION.md](VERIFICATION.md)。
