# -*- coding: utf-8 -*-
"""由 Cloudflare Worker 每小时触发：检查 @TheDivisionGame 最近一小时维护公告并推送。"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackbox_bot.heychat_client import HeychatBot
from blackbox_bot.loot_reader import build_maintenance_card
from scripts.fetch_server_maintenance import BEIJING, FEEDS, fetch_feed, parse_duration, parse_start

STATE = ROOT / "data" / "hourly_x_maintenance_state.json"
SUBSCRIPTION = ROOT / "data" / "blackbox_subscription.json"
MAX_KEYS = 500
log = logging.getLogger("hourly-x-maintenance")


def load_json(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as stream:
        return json.load(stream)


def key_for(post: dict) -> str:
    value = str(post.get("url") or "").strip()
    if not value:
        value = f"{post.get('posted_at')}|{post.get('text', '')}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "未知"
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours and minutes:
        return f"{hours}小时{minutes}分钟"
    if hours:
        return f"{hours}小时"
    return f"{minutes}分钟"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    token = os.getenv("HEYCHAT_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("缺少 GitHub Secret：HEYCHAT_BOT_TOKEN")

    subscription = load_json(SUBSCRIPTION, {})
    room_id = str(subscription.get("room_id") or "").strip()
    channel_info = subscription.get("channel_info")
    if not room_id or not isinstance(channel_info, dict) or not channel_info.get("channel_id"):
        log.info("尚未配置有效黑盒订阅频道，跳过推送")
        return

    now = datetime.now(timezone.utc)
    if os.getenv("SIMULATE_MAINTENANCE", "").strip().lower() in {"1", "true", "yes", "on"}:
        start_at = datetime.now(BEIJING) + timedelta(minutes=30)
        duration = 3 * 3600 + 30 * 60
        end_at = start_at + timedelta(seconds=duration)
        maintenance = {
            "source_account": "@TheDivisionGame（模拟测试）",
            "post_date_beijing": datetime.now(BEIJING).strftime("%Y-%m-%d %H:%M:%S"),
            "post_timestamp": int(now.timestamp()),
            "maintenance_start_beijing": start_at.strftime("%Y-%m-%d %H:%M"),
            "maintenance_start_timestamp": int(start_at.timestamp()),
            "source_timezone": "Asia/Shanghai",
            "duration_seconds": duration,
            "duration_text": "3小时30分钟",
            "countdown_end_time": int(end_at.timestamp()),
            "maintenance_end_beijing": end_at.strftime("%Y-%m-%d %H:%M"),
            "announcement": "【模拟测试】服务器将进行维护。本消息为测试卡片，不代表真实维护安排。",
            "post_url": "",
            "fetched_at_beijing": datetime.now(BEIJING).isoformat(timespec="seconds"),
        }
        card = build_maintenance_card(maintenance, int(now.timestamp()))
        message = json.dumps({"data": [card]}, ensure_ascii=False, separators=(",", ":"))
        bot.send_card(room_id, channel_info, message)
        log.info("模拟维护公告测试卡片已发送；未读取 X、未修改真实维护数据及去重记录。")
        return

    cutoff = now - timedelta(hours=1)
    state = load_json(STATE, {"sent_post_keys": []})
    sent = set(state.get("sent_post_keys", []))
    posts = []
    errors = []

    for feed in FEEDS:
        try:
            found = fetch_feed(feed)
            if found:
                posts = found
                log.info("读取到 %d 条维护相关推文，来源：%s", len(found), feed)
                break
        except Exception as exc:
            errors.append(f"{feed}: {exc}")
            log.warning("RSS 镜像读取失败：%s：%s", feed, exc)

    if not posts:
        if errors:
            raise RuntimeError("所有 X RSS 镜像均读取失败：" + " | ".join(errors))
        log.info("没有发现维护关键词推文")
        return

    posts.sort(key=lambda item: item.get("posted_at") or datetime.min.replace(tzinfo=timezone.utc))
    bot = HeychatBot(token)
    sent_keys = list(state.get("sent_post_keys", []))
    sent_count = 0
    failures = 0

    for post in posts:
        posted = post.get("posted_at")
        if posted is None:
            continue
        if posted.tzinfo is None:
            posted = posted.replace(tzinfo=timezone.utc)
        posted = posted.astimezone(timezone.utc)
        if posted < cutoff or posted > now + timedelta(minutes=2):
            continue

        post_key = key_for(post)
        if post_key in sent:
            continue

        posted_beijing = posted.astimezone(BEIJING)
        start_at, source_zone = parse_start(post.get("text", ""), posted_beijing)
        duration = parse_duration(post.get("text", ""))
        end_ts = int(start_at.timestamp() + duration) if start_at and duration is not None else None
        maintenance = {
            "source_account": "@TheDivisionGame",
            "post_date_beijing": posted_beijing.strftime("%Y-%m-%d %H:%M:%S"),
            "post_timestamp": int(posted.timestamp()),
            "maintenance_start_beijing": start_at.strftime("%Y-%m-%d %H:%M") if start_at else None,
            "maintenance_start_timestamp": int(start_at.timestamp()) if start_at else None,
            "source_timezone": source_zone,
            "duration_seconds": duration,
            "duration_text": format_duration(duration),
            "countdown_end_time": end_ts,
            "maintenance_end_beijing": datetime.fromtimestamp(end_ts, BEIJING).strftime("%Y-%m-%d %H:%M") if end_ts else None,
            "announcement": post.get("text", ""),
            "post_url": post.get("url", ""),
            "fetched_at_beijing": datetime.now(BEIJING).isoformat(timespec="seconds"),
        }
        card = build_maintenance_card(maintenance, int(now.timestamp()))
        message = json.dumps({"data": [card]}, ensure_ascii=False, separators=(",", ":"))

        try:
            bot.send_card(room_id, channel_info, message)
            sent.add(post_key)
            sent_keys.append(post_key)
            sent_count += 1
            log.info(
                "已推送维护公告：posted=%s start=%s duration=%s end=%s url=%s",
                maintenance["post_date_beijing"], maintenance["maintenance_start_beijing"],
                maintenance["duration_text"], maintenance["maintenance_end_beijing"], maintenance["post_url"],
            )
        except Exception:
            failures += 1
            log.exception("推送维护公告失败：%s", post.get("url", ""))

    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({
        "sent_post_keys": sent_keys[-MAX_KEYS:],
        "updated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    log.info("本轮检查完成：发送 %d 条，失败 %d 条", sent_count, failures)
    if failures:
        raise RuntimeError(f"有 {failures} 条维护公告推送失败")


if __name__ == "__main__":
    main()
