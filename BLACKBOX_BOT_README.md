# 全境封锁2每日掉落 - GitHub Actions 自动推送

所有任务由 GitHub Actions 托管 Runner 执行，无需 VPS、本地电脑或常驻服务器。

## 自动流程

1. 每天北京时间 16:00：从 AgentHub 下载 JSON，覆盖仓库固定文件 `全境封锁2恶化掉落/每日掉落.json`。
2. 首次订阅：在黑盒目标房间发送一次命令（命令 ID：`2124398728264114176`）。机器人将房间 ID 和频道 ID 保存到 `data/blackbox_subscription.json`。
3. 每天北京时间 16:10：读取固定掉落文件，生成三列中文 Markdown 表格并发送到订阅频道。

每日数据文件只保留一个，不按日期创建新文件。

## GitHub Secrets

进入仓库 Settings → Secrets and variables → Actions，新增：

- `HEYCHAT_BOT_TOKEN`：黑盒机器人 Token。

如果旧 Token 曾经暴露，请先在黑盒后台重置，再把新 Token 放入 Secret。不要把 Token 写入源码或提交记录。

## 首次启用步骤

1. 配置 `HEYCHAT_BOT_TOKEN`。
2. 手动运行 **Daily Loot Fetch**，确认 `全境封锁2恶化掉落/每日掉落.json` 已生成并提交。
3. 手动运行 **Blackbox Bot**，启动 WebSocket 监听。
4. 在目标房间发送一次命令，确认机器人回复订阅成功，且仓库生成 `data/blackbox_subscription.json`。
5. 手动运行 **Daily Loot Push**，确认目标频道实际收到表格。

## 工作流

- `.github/workflows/daily-loot-fetch.yml`：每天北京时间 16:00 获取并覆盖固定文件。
- `.github/workflows/daily-loot-push.yml`：每天北京时间 16:10 推送。
- `.github/workflows/blackbox-bot.yml`：监听订阅命令，保存频道信息。

三个工作流已更新至支持 Node.js 24 的 actions/checkout 与 actions/setup-python 新版本。

## 推送格式

| 副本名称 | 掉落装备名称 | 装备类型 |
|---|---|---|
| 数据源副本字段 | 数据源装备字段 | 数据源类型字段 |

## 运行限制

- GitHub Actions schedule 可能排队延迟，计划时间不等于精确准点保证。
- 机器人监听任务每次最长运行 350 分钟，后续由 schedule 接续；任务交接时可能短暂离线。
- 订阅写入需要工作流的 `GITHUB_TOKEN` 具有 `contents: write` 权限，工作流已声明该权限。
- 抓取脚本对返回 JSON 做结构和字段校验；抓取失败时不会覆盖上一次有效文件。
- AgentHub 实际数据字段和黑盒接口需要首次 Actions 运行及真实房间消息进行端到端验证。任何静态修改都不能替代这一步。
