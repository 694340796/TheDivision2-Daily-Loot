# -*- coding: utf-8 -*-
"""从仓库固定数据文件读取每日掉落，并发送到已订阅频道。"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

# 直接执行 scripts/send_daily_loot.py 时，Python 默认只把 scripts/ 放入
# sys.path；显式加入仓库根目录，确保可以导入 blackbox_bot 包。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from blackbox_bot.heychat_client import HeychatBot
from blackbox_bot.loot_reader import build_markdown

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("daily-loot-push")

SUBSCRIPTION = PROJECT_ROOT / "data" / "blackbox_subscription.json"


def main() -> None:
    token = os.getenv("HEYCHAT_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("缺少 HEYCHAT_BOT_TOKEN Secret")

    if not SUBSCRIPTION.is_file():
        log.info("尚未订阅任何频道，跳过每日推送")
        return

    try:
        config = json.loads(SUBSCRIPTION.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"订阅文件 JSON 格式错误：{SUBSCRIPTION}") from exc

    if not isinstance(config, dict):
        raise ValueError("订阅文件根节点必须是 JSON 对象")

    room_id = str(config.get("room_id") or "").strip()
    channel_info = config.get("channel_info")
    if not isinstance(channel_info, dict):
        raise ValueError("订阅记录缺少有效的 channel_info")
    channel_id = str(channel_info.get("channel_id") or "").strip()
    if not room_id or not channel_id:
        raise ValueError("订阅记录缺少 room_id 或 channel_id")

    message = build_markdown()
    bot = HeychatBot(token)
    bot.send_message(room_id, channel_info, message)
    log.info(
        "每日掉落已发送到订阅频道 room_id=%s channel_id=%s",
        room_id,
        channel_id,
    )


if __name__ == "__main__":
    main()
