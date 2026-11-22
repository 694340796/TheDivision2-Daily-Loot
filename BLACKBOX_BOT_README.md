# 全境封锁2每日掉落 - GitHub Actions 黑盒机器人

本项目采用 GitHub-hosted Actions Runner 运行机器人，不需要 VPS、云服务器或本地电脑。

## 功能

- 监听黑盒机器人命令 ID：`2124398728264114176`
- 读取仓库的 `history/全境封锁2每日掉落.py`
- 只回复三列中文 Markdown 表格：副本名称、掉落装备名称、装备类型
- WebSocket 断线自动重连
- GitHub Actions 每 5 分钟调度一次；每次任务最长运行 350 分钟，随后由下一次排队的计划任务接续

## 必须配置的 Secret

先在黑盒机器人后台重置此前暴露过的旧令牌。然后进入：

GitHub 仓库 → Settings → Secrets and variables → Actions → New repository secret

新增：

- Name：`HEYCHAT_BOT_TOKEN`
- Secret：粘贴重置后的黑盒机器人 Token

不要把 Token 写入任何代码、提交记录或普通变量。

## 启动方式

工作流文件：

`.github/workflows/blackbox-bot.yml`

配置 Secret 后，进入 GitHub 仓库 → Actions → Blackbox Bot → Run workflow，手动启动一次。之后工作流会按 `*/5 * * * *` 计划自动启动。

## 重要说明

1. GitHub Actions 的 schedule 最短计划间隔为 5 分钟，不是 1 分钟；GitHub 可能延迟调度，因此不能保证命令在 1～2 分钟内必定响应。
2. 机器人使用 WebSocket 长连接监听命令。每个 GitHub-hosted job 最长运行 6 小时，本工作流设置为 350 分钟并由后续计划任务接续。任务切换期间可能短暂离线。
3. GitHub Actions 并非 7×24 小时常驻服务。若必须保证实时响应，需要常驻运行环境；这与“完全只使用 GitHub Actions”不同。
4. 机器人必须已加入目标黑盒房间，并拥有查看频道和发送消息权限。
5. 当前 WebSocket 事件和消息发送实现尚未使用实际 Token 完成端到端验证。第一次运行后，请查看 Actions 日志并在黑盒房间实际触发命令确认。
6. 每日掉落数据更新由独立的更新工作流负责；机器人从仓库最新数据文件读取内容。

## 数据文件

`history/全境封锁2每日掉落.py`

机器人使用 AST 读取文件中的字面量数据，不会执行这个 Python 文件。
