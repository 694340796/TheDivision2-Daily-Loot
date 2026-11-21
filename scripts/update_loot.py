
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The Division 2 Daily Loot
每天获取官方数据源中的当前副本掉落，并生成 JSON 和 Markdown。
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


# ==============================
# 配置
# ==============================

SOURCE_URL = (
    "https://agenthub.fans/assets/loot/target_loot.json"
)

TIMEZONE = ZoneInfo("Asia/Shanghai")

ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data"
HISTORY_DIR = ROOT / "history"

LATEST_FILE = DATA_DIR / "latest.json"

MAX_RETRIES = 3
TIMEOUT = 30


# ==============================
# HTTP 获取
# ==============================

def fetch_json():

    headers = {
        "User-Agent": "TheDivision2-DailyLoot/1.0",
        "Accept": "application/json",
        "Cache-Control": "no-cache",
    }

    request = urllib.request.Request(
        SOURCE_URL,
        headers=headers,
        method="GET",
    )

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            print(
                f"Fetching source: "
                f"{attempt}/{MAX_RETRIES}"
            )

            with urllib.request.urlopen(
                request,
                timeout=TIMEOUT
            ) as response:

                if response.status != 200:
                    raise RuntimeError(
                        f"HTTP status: {response.status}"
                    )

                raw = response.read()

            # 兼容 UTF-8 BOM
            text = raw.decode("utf-8-sig")

            data = json.loads(text)

            if not isinstance(data, dict):
                raise ValueError("JSON root must be an object")

            return data

        except Exception as error:

            last_error = error

            print(f"Fetch failed: {error}")

            if attempt < MAX_RETRIES:
                time.sleep(attempt * 5)

    raise RuntimeError(
        f"Unable to fetch source: {last_error}"
    )


# ==============================
# 数据解析
# ==============================

def parse_data(data):

    today = datetime.now(TIMEZONE).date()

    snapshot_date = data.get("snapshot_date")

    if not snapshot_date:
        raise ValueError("Missing snapshot_date")

    try:
        source_date = datetime.strptime(
            snapshot_date,
            "%Y-%m-%d"
        ).date()
    except ValueError:
        raise ValueError(
            f"Invalid snapshot_date: {snapshot_date}"
        )

    # 防止读取到旧缓存或错误日期
    if source_date != today:
        raise ValueError(
            f"Source date mismatch: "
            f"source={source_date}, Beijing={today}"
        )

    current = data.get("current")

    if not isinstance(current, list) or not current:
        raise ValueError("Current loot list is empty or invalid")

    missions = []

    for item in current:

        if not isinstance(item, dict):
            continue

        mission = str(
            item.get("mission", "")
        ).strip()

        loot = str(
            item.get("loot", "")
        ).strip()

        if not mission or not loot:
            continue

        entry = {
            "mission": mission,
            "mission_en": item.get("mission_en", ""),
            "loot": loot,
            "loot_en": item.get("loot_en", ""),
            "category": item.get("category", ""),
        }

        # 保留可用的原始附加数据
        for key in (
            "mission_code",
            "loot_code",
            "loot_uid",
            "loot_mitem",
            "loot_alias",
        ):
            if key in item:
                entry[key] = item[key]

        missions.append(entry)

    if not missions:
        raise ValueError("No valid mission records found")

    result = {
        "source": SOURCE_URL,
        "snapshot_date": snapshot_date,
        "timezone": "Asia/Shanghai",
        "reset_hour_utc": data.get("reset_hour_utc"),
        "current_playlist": data.get("current_playlist"),
        "total": len(missions),
        "current": missions,
    }

    return result


# ==============================
# Markdown 生成
# ==============================

def escape_markdown(value):

    return str(value).replace("|", r"\|").replace("\n", " ")


def generate_markdown(data):

    date = data["snapshot_date"]

    lines = [
        f"# 全境封锁2 每日目标掉落 - {date}",
        "",
        f"> 更新时间：北京时间 {date} 16:00",
        "",
        f"> 数据来源：[AgentHub 每日掉落数据]({SOURCE_URL})",
        "",
        f"**当前副本数量：{data['total']}**",
        "",
        "| 副本名称 | 掉落装备 | 掉落分类 |",
        "|---|---|---|",
    ]

    for item in data["current"]:

        mission = escape_markdown(item["mission"])
        loot = escape_markdown(item["loot"])
        category = escape_markdown(item["category"] or "未分类")

        lines.append(
            f"| {mission} | {loot} | {category} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## English",
        "",
        "| Mission | Target Loot | Category |",
        "|---|---|---|",
    ])

    for item in data["current"]:

        mission = escape_markdown(
            item.get("mission_en") or item["mission"]
        )

        loot = escape_markdown(
            item.get("loot_en") or item["loot"]
        )

        category = escape_markdown(
            item.get("category") or "Unknown"
        )

        lines.append(
            f"| {mission} | {loot} | {category} |"
        )

    lines.extend([
        "",
        "## 原始数据",
        "",
        f"[查看数据源]({SOURCE_URL})",
        "",
    ])

    return "\n".join(lines)


# ==============================
# 文件安全写入
# ==============================

def write_json(path, content):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    temporary.write_text(
        json.dumps(
            content,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )

    os.replace(temporary, path)


def write_text(path, content):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    temporary.write_text(
        content,
        encoding="utf-8"
    )

    os.replace(temporary, path)


# ==============================
# 主程序
# ==============================

def main():

    print("=" * 50)
    print("The Division 2 Daily Loot")
    print("=" * 50)

    now = datetime.now(TIMEZONE)

    print(
        "Beijing time:",
        now.strftime("%Y-%m-%d %H:%M:%S")
    )

    # 获取数据
    raw_data = fetch_json()

    # 解析数据
    result = parse_data(raw_data)

    date = result["snapshot_date"]

    # 生成当日 Markdown
    markdown = generate_markdown(result)

    # 历史归档路径
    year = date[:4]
    month = date[5:7]

    history_file = (
        HISTORY_DIR
        / year
        / month
        / f"{date}.md"
    )

    # 写入最新数据
    write_json(
        LATEST_FILE,
        result
    )

    # 写入历史数据
    write_text(
        history_file,
        markdown
    )

    print()
    print("Updated successfully!")
    print("Date:", date)
    print("Total missions:", result["total"])
    print()

    for item in result["current"]:

        print(
            f"{item['mission']} -> {item['loot']}"
        )

    print()
    print("Latest:", LATEST_FILE)
    print("History:", history_file)


if __name__ == "__main__":

    try:
        main()

    except Exception as error:

        print()
        print("ERROR:", error)

        sys.exit(1)
