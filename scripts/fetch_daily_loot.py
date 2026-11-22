# -*- coding: utf-8 -*-
"""每天从 AgentHub 获取最新掉落 JSON，覆盖固定数据文件。"""
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
OUTPUT = Path("data/daily_loot.json")
TZ = ZoneInfo("Asia/Shanghai")
RETRIES = int(os.getenv("LOOT_RETRIES", "5"))
RETRY_SECONDS = int(os.getenv("LOOT_RETRY_SECONDS", "60"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("daily-loot-fetch")


def get_records(payload):
    candidates = [payload]
    if isinstance(payload.get("data"), dict):
        candidates.append(payload["data"])
    for item in candidates:
        rows = item.get("current")
        if isinstance(rows, list) and rows:
            return rows
    raise ValueError("JSON 中没有找到非空 current 数组")


def fetch():
    url = SOURCE_URL + ("&" if "?" in SOURCE_URL else "?") + "_=" + str(int(time.time() * 1000))
    req = urllib.request.Request(url, headers={
        "User-Agent": "TheDivision2-DailyLoot-GitHubActions/1.0",
        "Cache-Control": "no-cache, no-store, max-age=0",
        "Pragma": "no-cache",
    })
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("数据源 JSON 根节点必须是对象")
    rows = get_records(payload)
    for row in rows:
        if not isinstance(row, dict) or not row.get("mission") or not row.get("loot"):
            raise ValueError("掉落记录缺少 mission 或 loot 中文字段")
    payload["_github_fetched_at"] = datetime.now(TZ).isoformat(timespec="seconds")
    payload["_github_source_url"] = SOURCE_URL
    return payload


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    last_error = None
    for attempt in range(1, RETRIES + 1):
        try:
            payload = fetch()
            content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
            old = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else None
            if old == content:
                log.info("数据没有变化，无需写入")
                return
            OUTPUT.write_text(content, encoding="utf-8")
            log.info("已覆盖 %s，共 %s 条记录", OUTPUT, len(get_records(payload)))
            return
        except Exception as exc:
            last_error = exc
            log.warning("第 %s/%s 次获取失败：%s", attempt, RETRIES, exc)
            if attempt < RETRIES:
                time.sleep(RETRY_SECONDS)
    raise RuntimeError(f"多次获取失败，保留旧文件：{last_error}")


if __name__ == "__main__":
    main()
