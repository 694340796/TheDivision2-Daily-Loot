
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
import time
import urllib.request

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


SOURCE_URL = "https://agenthub.fans/assets/loot/target_loot.json"

TIMEZONE = ZoneInfo("Asia/Shanghai")

ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data"
HISTORY_DIR = ROOT / "history"

LATEST_FILE = DATA_DIR / "latest.json"

# 固定推送文件
OUTPUT_FILE = HISTORY_DIR / "全境封锁2每日掉落.py"

MAX_RETRIES = 3
TIMEOUT = 30


def fetch_json():

    headers = {
        "User-Agent": "TheDivision2-DailyLoot/1.0",
        "Accept": "application/json",
        "Cache-Control": "no-cache",
    }

    request = urllib.request.Request(
        SOURCE_URL,
        headers=headers,
    )

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            print(f"获取数据：{attempt}/{MAX_RETRIES}")

            with urllib.request.urlopen(
                request,
                timeout=TIMEOUT
            ) as response:

                if response.status != 200:
                    raise RuntimeError(
                        f"HTTP {response.status}"
                    )

                raw = response.read()

            data = json.loads(
                raw.decode("utf-8-sig")
            )

            if not isinstance(data, dict):
                raise ValueError("JSON 格式错误")

            return data

        except Exception as error:

            last_error = error

            print("获取失败：", error)

            if attempt < MAX_RETRIES:
                time.sleep(attempt * 5)

    raise RuntimeError(
        f"无法获取数据：{last_error}"
    )


def parse_data(data):

    today = datetime.now(TIMEZONE).date()

    snapshot_date = data.get("snapshot_date")

    if not snapshot_date:
        raise ValueError("缺少 snapshot_date")

    source_date = datetime.strptime(
        snapshot_date,
        "%Y-%m-%d"
    ).date()

    if source_date != today:
        raise ValueError(
            f"数据日期不一致："
            f"数据源={source_date}，北京时间={today}"
        )

    current = data.get("current")

    if not isinstance(current, list) or not current:
        raise ValueError("current 数据为空或格式错误")

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
        raise ValueError("没有有效的副本掉落记录")

    return {
        "source": SOURCE_URL,
        "snapshot_date": snapshot_date,
        "timezone": "Asia/Shanghai",
        "reset_hour_utc": data.get("reset_hour_utc"),
        "current_playlist": data.get("current_playlist"),
        "total": len(missions),
        "current": missions,
    }


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


def generate_python(data):

    content = (
        "# -*- coding: utf-8 -*-\n"
        '"""全境封锁2每日目标掉落数据，自动更新，请勿手动修改。"""\n\n'
        "SOURCE_URL = "
        + repr(data["source"])
        + "\n\n"
        "SNAPSHOT_DATE = "
        + repr(data["snapshot_date"])
        + "\n\n"
        "TIMEZONE = 'Asia/Shanghai'\n\n"
        "TOTAL = "
        + str(data["total"])
        + "\n\n"
        "CURRENT = "
        + json.dumps(
            data["current"],
            ensure_ascii=False,
            indent=4
        )
        + "\n"
    )

    return content


def main():

    print("=" * 50)
    print("全境封锁2每日掉落自动同步")
    print("=" * 50)

    print(
        "北京时间：",
        datetime.now(TIMEZONE).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    raw_data = fetch_json()

    result = parse_data(raw_data)

    # 更新 JSON 数据
    write_json(
        LATEST_FILE,
        result
    )

    # 更新固定 Python 文件
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temporary = OUTPUT_FILE.with_suffix(
        ".py.tmp"
    )

    temporary.write_text(
        generate_python(result),
        encoding="utf-8"
    )

    os.replace(
        temporary,
        OUTPUT_FILE
    )

    print("\n更新成功！")
    print("日期：", result["snapshot_date"])
    print("副本数量：", result["total"])
    print("推送文件：", OUTPUT_FILE)

    for item in result["current"]:
        print(
            f"{item['mission']} → {item['loot']}"
        )


if __name__ == "__main__":

    try:
        main()

    except Exception as error:

        print("\n更新失败：", error)
        sys.exit(1)
