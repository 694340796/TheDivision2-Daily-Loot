# The Division 2 Daily Loot

全境封锁2每日掉落自动获取与黑盒机器人推送项目。全部任务由 GitHub Actions 托管 Runner 执行，无需 VPS。

## 自动流程（北京时间）

- **16:00**：从 AgentHub 获取每日掉落 JSON，覆盖固定文件 `data/daily_loot.json`。
- **16:10**：读取该固定文件，将三列中文 Markdown 表格推送到已订阅的黑盒房间。
- 首次只需在黑盒目标房间发送一次订阅命令，订阅目标保存在 `data/blackbox_subscription.json`。

## 初始化

1. 在仓库 Settings → Secrets and variables → Actions 添加 `HEYCHAT_BOT_TOKEN`（必须使用已重置的新 Token）。
2. Actions → **Daily Loot Fetch** → Run workflow，先生成 `data/daily_loot.json`。
3. Actions → **Blackbox Bot** → Run workflow，启动机器人监听。
4. 在目标黑盒房间发送命令 ID `2124398728264114176` 对应的命令，收到订阅成功回复即可。
5. 以后每天自动更新和推送。

详细说明见 [BLACKBOX_BOT_README.md](BLACKBOX_BOT_README.md)。

## 固定数据文件

- `data/daily_loot.json`：每日覆盖更新，机器人唯一读取的数据源。
- `data/blackbox_subscription.json`：保存一次性订阅的房间和频道信息。

旧版 `refresh-daily-loot.yml` 已改为手动工作流，避免再更新旧格式数据文件。
