# -*- coding: utf-8 -*-
"""北京时间每日掉落更新器：抓取最新 JSON，更新 history Python 数据文件。"""

from __future__ import annotations

import json
import logging
import os
import pprint
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SOURCE_URL = "https://agenthub.fans/assets/loot/target_loot.json"
OUTPUT = Path("history/全境封锁2每日掉落.py")
TZ = ZoneInfo("Asia/Shanghai")
RETRIES = int(os.getenv("LOOT_RETRIES", "6"))
RETRY_SECONDS = int(os.getenv("LOOT_RETRY_SECONDS", "90"))

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("loot-updater")


def get_today() -> str:
    return datetime.now(TZ).date().isoformat()


def request_source() -> dict:
    cache_buster = int(time.time() * 1000)
    url = SOURCE_URL + ("&" if "?" in SOURCE_URL else "?") + f"_={cache_buster}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "TheDivision2-DailyLoot-Updater/1.0",
            "Cache-Control": "no-cache, no-store, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read().decode("utf-8-sig")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("数据源 JSON 根节点不是对象")
    return data


def locate_records(data: dict) -> list:
    """兼容根节点或 data 子节点中包含 current 的常见结构。"""
    candidates = [data]
    if isinstance(data.get("data"), dict):
        candidates.append(data["data"])

    for item in candidates:
        records = item.get("current")
        if isinstance(records, list) and records:
            return records

    raise ValueError("数据源中找不到非空 current 数组")


def locate_date(data: dict) -> str | None:
    candidates = [data]
    if isinstance(data.get("data"), dict):
        candidates.append(data["data"])

    date_keys = ("snapshot_date", "date", "day", "update_date", "updated_at")
    for item in candidates:
        for key in date_keys:
            value = item.get(key)
            if value:
                match = re.search(r"\d{4}-\d{2}-\d{2}", str(value))
                if match:
                    return match.group(0)
    return None


def normalize(data: dict) -> tuple[str, list]:
    date_value = locate_date(data)
    if not date_value:
        raise ValueError(
            "数据源没有可识别的日期字段（snapshot_date/date/day/updated_at），"
            "为防止把旧数据误当成今天数据，停止更新"
        )

    records = locate_records(data)
    clean = []
    for row in records:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        # 这三个字段是机器人表格所需的核心中文字段。
        if not item.get("mission") or not item.get("loot"):
            raise ValueError(f"记录缺少 mission 或 loot：{item!r}")
        if not item.get("category"):
            item["category"] = item.get("loot_type") or item.get("type") or "未分类"
        clean.append(item)

    if not clean:
        raise ValueError("清洗后没有有效掉落记录")
    return date_value, clean


def render_python(snapshot_date: str, records: list) -> str:
    total = len(records)
    return (
        '# -*- coding: utf-8 -*-\n'
        '"""全境封锁2每日目标掉落数据，自动更新，请勿手动修改。"""\n\n'
        f"SOURCE_URL = {SOURCE_URL!r}\n\n"
        f"SNAPSHOT_DATE = {snapshot_date!r}\n\n"
        "TIMEZONE = 'Asia/Shanghai'\n\n"
        f"TOTAL = {total}\n\n"
        "CURRENT = "
        + pprint.pformat(records, width=100, sort_dicts=False, ensure_ascii=False)
        + "\n"
    )


def main() -> int:
    today = get_today()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, RETRIES + 1):
        try:
            source = request_source()
            snapshot_date, records = normalize(source)

            if snapshot_date != today:
                raise ValueError(
                    f"数据源日期仍为 {snapshot_date}，北京时间今天是 {today}"
                )

            content = render_python(snapshot_date, records)
            old = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else None

            if old == content:
                log.info("数据日期和内容均未变化，无需提交")
                return 0

            OUTPUT.write_text(content, encoding="utf-8", newline="\n")
            log.info(
                "已更新 %s：日期=%s，记录数=%s",
                OUTPUT,
                snapshot_date,
                len(records),
            )
            return 0

        except Exception as exc:
            log.warning("第 %s/%s 次检查未完成：%s", attempt, RETRIES, exc)
            if attempt < RETRIES:
                time.sleep(RETRY_SECONDS)

    log.error("多次重试后仍未取得今天的数据，任务失败，不覆盖旧数据")
    return 1


if __name__ == "__main__":
    sys.exit(main())
