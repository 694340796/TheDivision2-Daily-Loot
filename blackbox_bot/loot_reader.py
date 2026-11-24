# -*- coding: utf-8 -*-
"""构建黑盒 Markdown 消息：SHD 风格每日目标掉落情报。"""
from __future__ import annotations
import json
from pathlib import Path
from urllib.parse import quote

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "全境封锁2恶化掉落" / "每日掉落.json"
ICON_BASE_URL = "https://agenthub.fans/assets/db/img/"


def locate_records(payload: dict) -> list[dict]:
    candidates = [payload]
    for key in ("data", "result"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            candidates.append(nested)
    for item in candidates:
        for key in ("current", "missions", "items"):
            rows = item.get(key)
            if isinstance(rows, list) and rows:
                return [row for row in rows if isinstance(row, dict)]
    raise ValueError(f"{DATA_PATH} 中没有非空掉落记录")


def clean_text(value: object) -> str:
    return " ".join(str(value).replace("\r", " ").replace("\n", " ").split())


def pick(record: dict, *keys: str, default: str = "未知") -> str:
    for key in keys:
        value = record.get(key)
        if value not in (None, "", [], {}):
            if isinstance(value, list):
                return "、".join(str(x) for x in value)
            if isinstance(value, dict):
                return str(value.get("name") or value.get("zh") or default)
            return str(value)
    return default


def build_markdown(subscription: bool = False) -> str:
    """按黑盒 msg_type=4 Markdown 规则生成消息；段落间使用双换行。"""
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"{DATA_PATH} 不存在")
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("每日掉落 JSON 根节点格式错误")
    rows = locate_records(payload)
    icons = payload.get("icons") if isinstance(payload.get("icons"), dict) else {}

    blocks = [
        "# 🟠 THE DIVISION 2",
        "## SHD FIELD INTEL  /  每日目标掉落",
        f"📅 **情报日期**　{clean_text(payload.get('snapshot_date') or '日期未知')}",
        f"🎯 **目标区域**　{len(rows)} 个",
    ]
    if payload.get("current_playlist") is not None:
        blocks.append(f"🛰️ **行动轮换**　#{clean_text(payload['current_playlist'])}")
    if subscription:
        blocks.append("✅ **订阅成功**　已接入每日自动情报")
    blocks.append("---")

    for index, row in enumerate(rows, 1):
        mission = clean_text(pick(row, "mission", "mission_name", "name", "副本", "副本名称", default="未知行动区域"))
        code = clean_text(pick(row, "mission_code", "code", default=""))
        loot = clean_text(pick(row, "loot", "target_loot", "targetLoot", "item", "装备", "掉落装备", default="未知掉落"))
        category = clean_text(pick(row, "category", "loot_type", "type", "item_type", "装备类型", default="未分类"))

        title = f"**{index:02d}  |  {mission}**"
        if code:
            title += f"　·　{code}"
        blocks.append(title)

        filename = icons.get(loot)
        if isinstance(filename, str) and filename.strip():
            url = ICON_BASE_URL + quote(filename.strip().lstrip("/"), safe="/._-")
            blocks.append(f"![{loot}]({url})")
        else:
            blocks.append("🎁")
        blocks.append(f"🎁 **目标掉落**　{loot}")
        blocks.append(f"🏷️ **装备分类**　{category}")
        blocks.append("---")

    blocks.extend([
        "🟠 **SHD NETWORK**",
        "情报同步完成　·　特工，祝你行动顺利。",
    ])
    return "\n\n".join(blocks)
