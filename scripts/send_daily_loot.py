# -*- coding: utf-8 -*-
"""从仓库固定数据文件读取每日掉落，并发送到已订阅频道。"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from blackbox_bot.heychat_client import HeychatBot
from blackbox_bot.loot_reader import build_markdown

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("daily-loot-push")

SUBSCRIPTION = Path("data/blackbox_subscription.json")


def main():
    token = os.getenv("HEYCHAT_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("缺少 HEYCHAT_BOT_TOKEN Secret")
    if not SUBSCRIPTION.exists():
        log.info("尚未订阅任何频道，跳过每日推送")
        return

    config = json.loads(SUBSCRIPTION.read_text(encoding="utf-8"))
    room_id = str(config.get("room_id", ""))
    channel_info = config.get("channel_info") or {}
    if not room_id or not channel_info.get("channel_id"):
        raise ValueError("订阅记录缺少 room_id 或 channel_id")

    message = build_markdown()
    bot = HeychatBot(token)
    bot.send_message(room_id, channel_info, message)
    log.info("每日掉落已发送到订阅频道 room_id=%s channel_id=%s",
             room_id, channel_info.get("channel_id"))


if __name__ == "__main__":
    main()
