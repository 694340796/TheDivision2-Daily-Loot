# The Division 2 Daily Loot

全境封锁2每日掉落自动获取与黑盒机器人推送项目。GitHub Actions 执行数据获取和消息推送；Cloudflare Worker 负责按北京时间定时触发 GitHub Actions。

## Cloudflare Worker 一键连接部署

仓库根目录已提供 Cloudflare Workers Builds 可识别的配置文件：

- `wrangler.jsonc)：Worker 名称、入口文件和 Cron 配置。
- `package.json)：Wrangler 依赖及部署脚本。
- Worker 源码：`cloudflare-worker/src/index.ts`。

在 Cloudflare Dashboard 创建 Worker 并连接本 GitHub 仓库时，使用以下构建设置：

| 设置 | 值 |
|---|---|
| Production branch | `main` |
| Root directory | 仓库根目录（留空或 `/`，不要填写 `cloudflare-worker`） |
| Build command | `npm install` |
| Deploy command | `npm run deploy` |

根目录的 `wrangler.jsonc` 会指向 `cloudflare-worker/src/index.ts`，因此无需在 Cloudflare 构建命令中手动 `cd` 子目录。

部署后，在 Worker → Settings → Variables and Secrets 中新增 Secret：

- Name：`GITHUB_TOKEN`
- Value：GitHub Fine-grained Personal Access Token
- Token 仅授权仓库 `TheDivision2-Daily-Loot` 的 `Actions: Read and write`；`Metadata: Read-only` 按 GitHub 要求保留。无需授予 Contents 或 Workflows 权限。

不要把 Token 写入仓库文件、普通 Text 变量或日志。

### Cron 调度

`wrangler.jsonc` 已配置：

- `1 8 * * *`：UTC 08:01，即北京时间每天 16:01，触发 `Daily Loot Fetch`。
- `2 8 * * *`：UTC 08:02，即北京时间每天 16:02，触发 `Daily Loot Push`。

Push 工作流会等待当天 Fetch 成功完成，再 checkout 最新数据并发送订阅消息。Cron 使用 UTC，Cloudflare 触发时间可能有少量延迟，不保证秒级准点。

### 本地开发（可选）

在仓库根目录执行：

```bash
npm install
npx wrangler dev
```

部署：

```bash
npm run deploy
```

## 自动流程（北京时间）

- **16:01**：Cloudflare Worker 触发 GitHub Actions 的 Daily Loot Fetch，从 AgentHub 获取每日掉落 JSON。
- **16:02**：Cloudflare Worker 触发 Daily Loot Push；该工作流等待 Fetch 成功后，读取最新 JSON 并推送订阅消息。
- GitHub Actions 页面仍保留手动运行入口。

## GitHub Actions 密钥

在仓库 Settings → Secrets and variables → Actions 中配置：

- `HEYCHAT_BOT_TOKEN`：黑盒机器人 Token。该 Token 继续由 GitHub Actions 使用，不需要放进 Cloudflare。

## 固定文件

- `全境封锁2恶化掉落/每日掉落.json`：每日覆盖，不按日期拆分。
- `data/blackbox_subscription.json`：保存订阅房间和频道信息。

详细说明见 [BLACKBOX_BOT_README.md](BLACKBOX_BOT_README.md)。

## 安全说明

- Cloudflare 的 `GITHUB_TOKEN` 必须保存为 Secret。
- 不要提交或公开任何机器人 Token。
- 如果 Token 泄露，立即在对应平台撤销并重新创建。


## 官方服务器维护公告（无 X API Token 模式）

- `scripts/fetch_server_maintenance.py` 随每日掉落获取工作流运行，尝试从公开 X/Nitter RSS 镜像读取官方账号 `@TheDivisionGame` 的维护公告。
- 不需要新增 GitHub Secret。若有可用 RSS 地址，可通过 Actions 环境变量 `X_PROFILE_FEED_URL` 覆盖默认 Feed。
- 公告数据保存到 `data/server_maintenance.json`，并随每日 Fetch 工作流提交。
- 黑盒原生卡片展示发帖日期、北京时间维护开始时间、官方预计维护时长；仅在开始时间和时长都解析成功时添加 `mode: default` 倒计时，结束时间为维护开始时间 + 官方预计维护时长。
- 未公布或无法解析的字段显示“官方未公布”，不猜测；抓取失败时保留旧公告且不阻断每日掉落任务。
- **稳定性说明：** 这是无令牌的公开镜像方案，不是 X 官方 API。公开 Nitter/RSS 镜像可能限流、变更或停止服务，因此不能保证每次都能取到最新动态。X API 或可靠的第三方数据 API 才能提供更稳定的自动化读取。
