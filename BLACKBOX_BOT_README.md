# 全境封锁2每日掉落 - GitHub Actions 自动推送

所有任务均由 GitHub Actions 托管 Runner 执行，不需要 VPS、服务器或本地电脑。

## 自动流程

1. 每天北京时间 16:00：`.github/workflows/daily-loot-fetch.yml` 从 AgentHub 下载 JSON，覆盖仓库固定文件 `data/daily_loot.json`。
2. 首次订阅：在黑盒目标房间发送一次已配置的机器人命令（命令 ID：`2124398728264114176`）。机器人把房间 ID 和频道 ID 保存到 `data/blackbox_subscription.json`。
3. 每天北京时间 16:10：`.github/workflows/daily-loot-push.yml` 从 `data/daily_loot.json` 读取最新掉落，生成三列中文 Markdown 表格并发送到订阅频道。

数据文件每天覆盖，不会按日期生成一堆文件。

## GitHub Secrets

进入仓库 Settings → Secrets and variables → Actions，新增：

- `HEYCHAT_BOT_TOKEN`：黑盒机器人 Token。

此前曾在聊天中暴露过的旧 Token 必须先在黑盒后台重置，再把新 Token 放入 Secret。不要将 Token 写入代码或提交记录。

## 首次启用步骤

1. 配置 `HEYCHAT_BOT_TOKEN`。
2. 进入 Actions，手动运行 **Daily Loot Fetch**，确认 `data/daily_loot.json` 已生成并提交。
3. 手动运行 **Blackbox Bot**，启动 WebSocket 监听。
4. 在目标黑盒房间发送一次命令，等待机器人回复“已成功订阅”。订阅信息会保存为 `data/blackbox_subscription.json`。
5. 之后每天 16:00 自动更新数据、16:10 自动推送，不需要再次发送命令。

## 工作流

- `.github/workflows/daily-loot-fetch.yml`：每日 16:00 抓取并覆盖数据文件。
- `.github/workflows/daily-loot-push.yml`：每日 16:10 自动推送。
- `.github/workflows/blackbox-bot.yml`：监听首次订阅命令，订阅数据写入仓库。

## 推送表格格式

| 副本名称 | 掉落装备名称 | 装备类型 |
|---|---|---|
| 读取 JSON 中的 mission | 读取 JSON 中的 loot | 读取 JSON 中的 category |

## 运行限制和注意事项

- GitHub Actions 的定时任务可能排队延迟，16:00 和 16:10 是计划触发时间，不是精确准点保证。
- 机器人监听任务按 350 分钟运行并由后续计划任务接续，切换时可能短暂离线；首次订阅命令需要监听任务处于运行状态。
- 订阅保存需要机器人工作流的 `GITHUB_TOKEN` 具有 `contents: write` 权限。工作流已声明该权限。
- AgentHub JSON 必须包含非空 `current` 数组，且每条记录包含中文 `mission`、`loot` 字段。若源格式发生变化，抓取任务会失败并保留旧数据，不能确认源端实际结构前不应猜测字段。
- 当前尚未用真实黑盒 Token 完成端到端测试。部署后需查看 Actions 日志并实际验证一次订阅和推送。

