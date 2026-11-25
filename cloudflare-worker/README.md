# Cloudflare Worker 定时触发 GitHub Actions

本目录负责每天北京时间 16:01 触发 Daily Loot Fetch，并在 16:02 触发 Daily Loot Push。

## 调度逻辑

- `1 8 * * *`：UTC 08:01，即北京时间 16:01，触发 `daily-loot-fetch.yml`。
- `2 8 * * *`：UTC 08:02，即北京时间 16:02，触发 `daily-loot-push.yml`。
- Push 工作流会等待当天 Fetch 工作流成功结束，再 checkout 最新仓库数据并发送订阅消息。
- GitHub Actions 页面仍保留手动运行入口。

## 1. 创建 GitHub Fine-grained PAT

在 GitHub 进入 Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token。

设置：
- Resource owner：`694340796`
- Repository access：Only select repositories → `TheDivision2-Daily-Loot`
- Repository permissions：Actions → Read and write
- 生成后复制 Token。不要把 Token 写入代码或提交到仓库。

## 2. 安装依赖

在本目录执行：

```bash
npm install
```

## 3. 登录 Cloudflare

```bash
npx wrangler login
```

## 4. 设置 GitHub Token Secret

在本目录执行：

```bash
npx wrangler secret put GITHUB_TOKEN
```

粘贴刚才生成的 Fine-grained PAT。

Worker 的 GitHub 仓库、所有者和分支已固定在代码中，不需要配置 `GITHUB_OWNER`、`GITHUB_REPO` 或 `GITHUB_REF` 普通变量。

Cloudflare Worker 只需要以下密钥：
- 必需 Secret：`GITHUB_TOKEN`，用于调用 GitHub Actions。
- 可选 Secret：`TRIGGER_SECRET`，用于网页手动触发测试。

这些密钥只在 Cloudflare Dashboard → Workers & Pages → Worker → Settings → Variables and Secrets 中设置，不要放入 GitHub 仓库文件。GitHub Actions 使用的 `HEYCHAT_BOT_TOKEN` 是另一项独立密钥，仍需保留在 GitHub 仓库 Secrets 中。

## 5. 部署

```bash
npm run deploy
```

部署后打开 Cloudflare Dashboard → Workers & Pages → thedivision2-daily-loot-scheduler → Settings → Triggers，确认有两个 Cron：
- `1 8 * * *`
- `2 8 * * *`

Cloudflare Cron 使用 UTC 时间。北京时间为 UTC+8。

## 6. 验证

打开 Worker 的 `workers.dev` 地址，应返回 JSON 健康状态。

再进入 Worker → Logs / Observability 查看 Cron 执行日志；进入 GitHub 仓库 Actions 查看两个 workflow 是否被触发。

注意：Cron 是定时触发，不是秒级 SLA；Cloudflare 的触发也可能有少量延迟。Push 最多等待 Fetch 15 分钟，Fetch 失败或超时则不会发送旧数据。

## 7. 安全

- 不要公开、提交或截图暴露 `GITHUB_TOKEN`。
- 如果 Token 泄露，立即在 GitHub 撤销并重新创建。
- 保留仓库的 `HEYCHAT_BOT_TOKEN` Secret；它仍由 GitHub Actions 使用，不需要放进 Cloudflare。
