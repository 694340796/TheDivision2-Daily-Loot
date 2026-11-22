# The Division 2 Daily Loot

全境封锁2每日掉落自动获取与黑盒机器人推送项目。所有任务由 GitHub Actions 托管执行，无需 VPS。

## 自动流程（北京时间）

- **16:00**：从 AgentHub 获取每日掉落 JSON，覆盖仓库固定文件 `全境封锁2恶化掉落/每日掉落.json`。
- **16:10**：读取该文件，将中文 Markdown 表格推送到已订阅的黑盒房间。
- 首次只需在目标黑盒房间发送一次订阅命令，订阅信息保存在 `data/blackbox_subscription.json`。

## 首次启用

1. 在仓库 Settings → Secrets and variables → Actions 添加 `HEYCHAT_BOT_TOKEN`（使用已重置的新 Token）。
2. Actions → **Daily Loot Fetch** → Run workflow，确认固定 JSON 文件生成并提交。
3. Actions → **Blackbox Bot** → Run workflow，启动监听。
4. 在目标黑盒房间发送命令 ID `2124398728264114176` 对应的命令，确认订阅成功回复。
5. 手动运行 **Daily Loot Push** 测试消息推送。

## 固定文件

- `全境封锁2恶化掉落/每日掉落.json`：每日覆盖，不按日期拆分。
- `data/blackbox_subscription.json`：保存订阅房间和频道信息。

详细说明见 [BLACKBOX_BOT_README.md](BLACKBOX_BOT_README.md)。

## 注意

GitHub Actions 定时任务可能延迟；16:00 和 16:10 是计划触发时间，不保证精确准点。机器人监听任务最长运行 350 分钟，由后续 schedule 接续，交接时可能短暂离线。真实黑盒接口和 AgentHub 数据格式仍须以首次运行日志及实际消息验证。
