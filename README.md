
# The Division 2 Daily Loot

全境封锁2每日目标掉落自动同步项目。

## 数据来源

https://agenthub.fans/assets/loot/target_loot.json

## 更新计划

每天北京时间 16:00 自动更新。

## 数据说明

- snapshot_date：数据日期
- current：当前副本列表
- mission：副本名称
- loot：对应掉落装备
- category：掉落分类

## 文件说明

- data/latest.json：最新每日掉落数据
- history/YYYY/MM/：历史每日掉落归档
- scripts/update_loot.py：数据获取程序
- .github/workflows/daily-loot.yml：定时执行任务

## 手动执行

进入 GitHub 仓库：

Actions → The Division 2 Daily Loot → Run workflow

## 通知

关注本仓库并开启 Pushes 通知，
即可接收每日数据更新的 GitHub 通知。

数据版权及归属以原始数据来源为准。
