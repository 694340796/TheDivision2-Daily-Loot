# -*- coding: utf-8 -*-
"""Fetch the daily loot snapshot and overwrite one stable repository file."""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SOURCE_URL = "https://agenthub.fans/assets/loot/target_loot.json"
OUTPUT = Path("全境封锁2恶化掉落/每日掉落.json")
TZ = ZoneInfo("Asia/Shanghai")
RETRIES = max(1, int(os.getenv("LOOT_RETRIES", "5")))
RETRY_SECONDS = max(1, int(os.getenv("LOOT_RETRY_SECONDS", "60")))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("daily-loot-fetch")


def get_records(payload: dict) -> list:
    """Accept the known current-list layouts without silently accepting empty data."""
    candidates = [payload]
    for key in ("data", "result"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            candidates.append(nested)
    for item in candidates:
        for key in ("current", "missions", "items"):
            rows = item.get(key)
            if isinstance(rows, list) and rows:
                return rows
    raise ValueError("未在数据源 JSON 中找到非空 current/missions/items 数组；旧数据未覆盖")


def field_value(record: dict, *names: str):
    for name in names:
        value = record.get(name)
        if value not in (None, "", [], {}):
            return value
    return None


def validate_records(rows: list) -> None:
    valid = 0
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError(f"第 {index} 条掉落记录不是对象")
        mission = field_value(row, "mission", "mission_name", "name", "副本", "副本名称")
        loot = field_value(row, "loot", "target_loot", "targetLoot", "item", "装备", "掉落装备")
        if mission is None or loot is None:
            raise ValueError(
                f"第 {index} 条记录缺少副本或装备字段；实际字段：{', '.join(map(str, row.keys()))}"
            )
        valid += 1
    if not valid:
        raise ValueError("数据源没有有效掉落记录")


def fetch() -> dict:
    url = SOURCE_URL + ("&" if "?" in SOURCE_URL else "?") + "_=" + str(int(time.time() * 1000))
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "TheDivision2-DailyLoot-GitHubActions/1.0",
            "Accept": "application/json",
            "Cache-Control": "no-cache, no-store, max-age=0",
            "Pragma": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
    payload = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("数据源 JSON 根节点必须是对象")
    rows = get_records(payload)
    validate_records(rows)
    payload["_github_fetched_at"] = datetime.now(TZ).isoformat(timespec="seconds")
    payload["_github_source_url"] = SOURCE_URL
    return payload


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    last_error = None
    for attempt in range(1, RETRIES + 1):
        try:
            payload = fetch()
            content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
            old = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else None
            if old == content:
                log.info("数据内容未变化；固定文件无需更新")
                return
            temporary = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
            temporary.write_text(content, encoding="utf-8")
            json.loads(temporary.read_text(encoding="utf-8"))
            temporary.replace(OUTPUT)
            log.info("已覆盖 %s（%d 条记录）", OUTPUT, len(get_records(payload)))
            return
        except Exception as exc:
            last_error = exc
            log.warning("第 %d/%d 次获取失败：%s", attempt, RETRIES, exc)
            if attempt < RETRIES:
                time.sleep(RETRY_SECONDS)
    raise RuntimeError(f"连续 {RETRIES} 次获取失败，未覆盖旧数据：{last_error}")


if __name__ == "__main__":
    main()
