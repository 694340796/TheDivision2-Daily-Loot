# -*- coding: utf-8 -*-
"""从公开 X 镜像 RSS 获取 @TheDivisionGame 最新服务器维护公告。"""
from __future__ import annotations

import html
import json
import logging
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "server_maintenance.json"
BEIJING = ZoneInfo("Asia/Shanghai")
PROFILE = "TheDivisionGame"
FEEDS = [
    os.getenv("X_PROFILE_FEED_URL", "").strip(),
    f"https://twiiit.com/{PROFILE}/rss",
    f"https://nitter.mie.foundation/{PROFILE}/rss",
    f"https://nitter.mizuki.st/{PROFILE}/rss",
]
FEEDS = list(dict.fromkeys(url for url in FEEDS if url))
TIMEZONES = {
    "CET": "Europe/Paris", "CEST": "Europe/Paris",
    "ET": "America/New_York", "EST": "America/New_York", "EDT": "America/New_York",
    "PT": "America/Los_Angeles", "PST": "America/Los_Angeles", "PDT": "America/Los_Angeles",
    "UTC": "UTC", "GMT": "UTC",
}
MONTHS = "January February March April May June July August September October November December".split()
log = logging.getLogger("server-maintenance-fetch")


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def text(self):
        return " ".join(" ".join(self.parts).split())


def plain(value: str) -> str:
    parser = TextExtractor()
    parser.feed(html.unescape(value or ""))
    return parser.text()


def parse_post_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(BEIJING)
    except (TypeError, ValueError, OverflowError):
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            return datetime.strptime(value, fmt).astimezone(BEIJING)
        except ValueError:
            continue
    return None


def parse_duration(text: str) -> int | None:
    patterns = [
        r"(?:estimated|expected|approx(?:imately)?|around)?\s*(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b",
        r"(?:estimated|expected|approx(?:imately)?|around)?\s*(\d+)\s*(?:minutes?|mins?|m)\b",
    ]
    for index, pattern in enumerate(patterns):
        match = re.search(pattern, text, re.I)
        if match:
            amount = float(match.group(1))
            return int(amount * (3600 if index == 0 else 60))
    match = re.search(r"(?:downtime|maintenance|maintenance window)[^.\n]{0,50}?(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|m)\b", text, re.I)
    if match:
        unit = match.group(2).lower()
        return int(float(match.group(1)) * (3600 if unit.startswith("h") else 60))
    return None


def parse_start(text: str, posted_at: datetime | None) -> tuple[datetime | None, str | None]:
    month_pattern = "|".join(MONTHS)
    date_match = re.search(
        rf"\b({month_pattern})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(\d{{4}}))?\b",
        text, re.I
    )
    if not date_match:
        return None, None

    month = MONTHS.index(date_match.group(1).title()) + 1
    day = int(date_match.group(2))
    year = int(date_match.group(3)) if date_match.group(3) else (posted_at.year if posted_at else datetime.now(BEIJING).year)

    time_match = re.search(
        r"\b(\d{1,2})(?::(\d{2}))?\s*(AM|PM)\s*(CET|CEST|ET|EST|EDT|PT|PST|PDT|UTC|GMT)\b",
        text, re.I
    )
    if not time_match:
        time_match = re.search(
            r"\b([01]?\d|2[0-3]):([0-5]\d)\s*(CET|CEST|ET|EST|EDT|PT|PST|PDT|UTC|GMT)\b",
            text, re.I
        )
        if not time_match:
            return None, None
        hour, minute = int(time_match.group(1)), int(time_match.group(2))
        zone_name = time_match.group(3).upper()
    else:
        hour = int(time_match.group(1)) % 12
        if time_match.group(3).upper() == "PM":
            hour += 12
        minute = int(time_match.group(2) or 0)
        zone_name = time_match.group(4).upper()

    try:
        local = datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(TIMEZONES[zone_name]))
        return local.astimezone(BEIJING), zone_name
    except (ValueError, KeyError):
        return None, zone_name


def is_maintenance(text: str) -> bool:
    lower = text.lower()
    keywords = ("maintenance", "downtime", "servers will be offline", "servers going offline",
                "server maintenance", "servers are going back offline")
    return any(word in lower for word in keywords)


def fetch_feed(url: str) -> list[dict]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; TheDivision2MaintenanceBot/1.0)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        raw = response.read()
    root = ET.fromstring(raw)
    items = root.findall(".//item") or root.findall(".//{*}entry")
    posts = []
    for item in items:
        def get(tag):
            node = item.find(tag)
            if node is None:
                node = item.find("{*}" + tag)
            return (node.text or "").strip() if node is not None else ""

        title = plain(get("title"))
        description = plain(get("description") or get("summary") or get("content"))
        content = " ".join(part for part in (title, description) if part)
        link = get("link")
        if not link:
            link_node = item.find("{*}link")
            if link_node is not None:
                link = link_node.attrib.get("href", "")
        published = get("pubDate") or get("published") or get("updated")
        posted_at = parse_post_date(published)
        if content and is_maintenance(content):
            posts.append({"text": content, "url": link, "posted_at": posted_at})
    return posts


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    all_posts = []
    errors = []
    for feed in FEEDS:
        try:
            found = fetch_feed(feed)
            if found:
                all_posts.extend(found)
                log.info("从公开镜像获取到 %d 条维护相关动态：%s", len(found), feed)
                break
        except Exception as exc:
            errors.append(f"{feed}: {exc}")
            log.warning("公开 X Feed 不可用：%s：%s", feed, exc)

    if not all_posts:
        log.warning("未能从公开镜像读取维护公告；保留已有数据。%s", " | ".join(errors))
        return

    all_posts.sort(key=lambda item: item["posted_at"] or datetime.min.replace(tzinfo=BEIJING), reverse=True)
    post = all_posts[0]
    start_at, source_timezone = parse_start(post["text"], post["posted_at"])
    duration_seconds = parse_duration(post["text"])
    end_at = start_at.timestamp() + duration_seconds if start_at and duration_seconds else None
    posted_at = post["posted_at"]

    result = {
        "source_account": "@TheDivisionGame",
        "post_date_beijing": posted_at.strftime("%Y-%m-%d %H:%M:%S") if posted_at else "未知",
        "post_timestamp": int(posted_at.timestamp()) if posted_at else None,
        "maintenance_start_beijing": start_at.strftime("%Y-%m-%d %H:%M") if start_at else None,
        "maintenance_start_timestamp": int(start_at.timestamp()) if start_at else None,
        "source_timezone": source_timezone,
        "duration_seconds": duration_seconds,
        "duration_text": (
            f"{duration_seconds // 3600}小时" if duration_seconds and duration_seconds % 3600 == 0
            else f"{duration_seconds // 3600}小时{(duration_seconds % 3600) // 60}分钟" if duration_seconds and duration_seconds >= 3600
            else f"{duration_seconds // 60}分钟" if duration_seconds else "未知"
        ),
        "countdown_end_time": int(end_at) if end_at else None,
        "maintenance_end_beijing": datetime.fromtimestamp(end_at, BEIJING).strftime("%Y-%m-%d %H:%M") if end_at else None,
        "announcement": post["text"],
        "post_url": post["url"],
        "fetched_at_beijing": datetime.now(BEIJING).isoformat(timespec="seconds"),
        "parser_note": "仅提取公告明确写出的时间和时长；未公布维护时长时显示未知且不生成维护结束倒计时。",
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    old = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else None
    if old == content:
        log.info("维护公告没有变化。")
        return
    OUTPUT.write_text(content, encoding="utf-8")
    log.info("已保存维护公告：发帖=%s，维护开始=%s，时长=%s，预计结束=%s",
             result["post_date_beijing"], result["maintenance_start_beijing"],
             result["duration_text"], result["maintenance_end_beijing"])


if __name__ == "__main__":
    main()
