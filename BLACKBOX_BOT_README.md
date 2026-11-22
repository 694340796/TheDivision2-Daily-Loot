# 全境封锁2每日掉落 - 黑盒语音机器人

## 功能

- 收到黑盒命令 ID `2124398728264114176` 时，读取 GitHub 仓库最新的 `history/全境封锁2每日掉落.py`。
- 仅输出三列中文 Markdown 表格：副本名称、掉落装备名称、装备类型。
- 不执行仓库 Python 文件，而是用 AST 安全读取 `CURRENT` 字面量。
- WebSocket 断线自动重连，心跳维持连接。
- 每日掉落更新由 GitHub Actions 单独执行。

## 1. 先处理令牌

此前令牌已被发送到聊天中，请先在黑盒机器人管理后台重置令牌。只把新令牌配置为运行主机环境变量 `HEYCHAT_BOT_TOKEN`，不要写入源码、`.env.example` 或 GitHub 仓库。

## 2. 安装机器人

建议使用长期运行的 Linux VPS / Windows 主机。GitHub Actions 不是常驻服务，不适合承担 WebSocket 在线监听。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r blackbox_bot/requirements.txt
```

在项目根目录设置环境变量：

```bash
export HEYCHAT_BOT_TOKEN='你的重置后令牌'
export HEYCHAT_COMMAND_ID='2124398728264114176'
```

启动：

```bash
python -m blackbox_bot.main
```

Windows PowerShell：

```powershell
$env:HEYCHAT_BOT_TOKEN="你的重置后令牌"
$env:HEYCHAT_COMMAND_ID="2124398728264114176"
python -m blackbox_bot.main
```

确保机器人已被邀请到目标房间，并具有查看频道、发送消息权限。命令 ID 必须与黑盒机器人管理后台中配置的命令 ID 完全一致。

## 3. Linux systemd 常驻运行示例

将项目放在 `/opt/TheDivision2-BlackboxBot`，创建 `/etc/systemd/system/division2-blackbox-bot.service`：

```ini
[Unit]
Description=The Division 2 Heychat Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/TheDivision2-BlackboxBot
Environment=HEYCHAT_BOT_TOKEN=替换为重置后的令牌
Environment=HEYCHAT_COMMAND_ID=2124398728264114176
Environment=LOOT_REPOSITORY=694340796/TheDivision2-Daily-Loot
Environment=LOOT_BRANCH=main
Environment=LOOT_DATA_PATH=history/全境封锁2每日掉落.py
ExecStart=/opt/TheDivision2-BlackboxBot/.venv/bin/python -m blackbox_bot.main
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now division2-blackbox-bot
sudo systemctl status division2-blackbox-bot
journalctl -u division2-blackbox-bot -f
```

生产环境建议使用专用低权限用户，并用 systemd `EnvironmentFile` 或主机密钥管理功能保存令牌，不要把真实令牌写进服务文件。

## 4. 每日掉落自动更新

新增的 `.github/workflows/refresh-daily-loot.yml` 会在北京时间：

- 16:07 检查一次；
- 16:37 再检查一次；
- 每次最多重试 6 次，每次间隔 90 秒；
- 只有数据源日期等于北京时间当天，才会覆盖仓库数据；
- 数据没变化就不产生提交；
- 数据源未更新时任务会失败并保留旧数据，不会把昨天的数据冒充今天数据。

GitHub Actions 的 schedule 使用 UTC：`7,37 8 * * *`。GitHub 定时任务可能有排队延迟，不能保证精确到分钟；双时段检查和重试用于降低漏更新概率。

请在仓库 Settings → Actions → General → Workflow permissions 中允许工作流写入仓库内容（Read and write permissions）。

## 5. 部署注意事项

1. 将本项目文件合并到 `694340796/TheDivision2-Daily-Loot`，保留原有 `history/全境封锁2每日掉落.py`。
2. 确保新 workflow 位于默认分支的 `.github/workflows/` 目录。
3. 检查仓库中是否有旧的每日掉落定时 workflow；确认新 workflow 成功后，再停用旧的重复任务，避免两套更新程序同时写同一个文件。
4. 在 Actions 页面手动运行 `Refresh The Division 2 Daily Loot`，检查日志与提交结果。
5. 在黑盒房间触发对应命令，预期回复格式如下：

| 副本名称 | 掉落装备名称 | 装备类型 |
|---|---|---|
| 艺术博物馆 | 核心力量 | 装备组 |
| 国会大厦 | 霰弹枪 | 武器类型 |

示例仅用于展示格式，实际内容以仓库当天数据为准。

## 6. 目录

```text
.
├── .github/workflows/refresh-daily-loot.yml
├── blackbox_bot/
│   ├── __init__.py
│   ├── main.py
│   ├── heychat_client.py
│   ├── loot_reader.py
│   └── requirements.txt
├── history/
│   └── 全境封锁2每日掉落.py  # 使用原仓库文件，不要用示例覆盖
├── update_loot.py
├── .env.example
└── BLACKBOX_BOT_README.md
```
