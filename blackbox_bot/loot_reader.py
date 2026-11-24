# -*- coding: utf-8 -*-
"""读取仓库每日掉落数据，并构建黑盒原生卡片消息。"""
from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "全境封锁2恶化掉落" / "每日掉落.json"


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
    raise ValueError(f"{DATA_PATH} 中没有非空掉落记录数组")


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


def clean_text(value: object) -> str:
    return " ".join(str(value).replace("\r", " ").replace("\n", " ").split())


def build_card_json(subscription: bool = False) -> str:
    """构建黑盒 msg_type=20 原生卡片 JSON 字符串，不包含任何外链或数据来源。"""
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"每日掉落文件不存在：{DATA_PATH}")

    payload = json.loads(DATA_PATH.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("每日掉落 JSON 根节点格式错误")

    rows = locate_records(payload)
    snapshot_date = clean_text(payload.get("snapshot_date") or "日期未知")
    playlist = payload.get("current_playlist")
    modules = [
        {
            "type": "header",
            "content": {
                "type": "plain-text",
                "text": "SHD 情报终端  |  每日目标掉落"
            }
        },
        {
            "type": "section",
            "paragraph": [{
                "type": "markdown",
                "text": (
                    "**THE DIVISION 2 · STRATEGIC INTEL**\n\n"
                    + ("✅ **订阅成功！特工已接入每日情报频道。**\n\n" if subscription else "")
                    + f"📅 **情报日期：** {snapshot_date}\n\n"
                    + f"📦 **今日区域：** {len(rows)} 个行动区域"
                    + (f"\n\n🛰️ **行动轮换：** 第 {playlist} 轮" if playlist else "")
                )
            }]
        }
    ]

    for index, row in enumerate(rows, 1):
        mission = clean_text(pick(
            row, "mission", "mission_name", "name", "副本", "副本名称",
            default="未知副本"
        ))
        mission_en = clean_text(pick(row, "mission_en", default=""))
        loot = clean_text(pick(
            row, "loot", "target_loot", "targetLoot", "item", "装备", "掉落装备",
            default="未知掉落"
        ))
        loot_en = clean_text(pick(row, "loot_en", default=""))
        category = clean_text(pick(
            row, "category", "loot_type", "type", "item_type", "装备类型",
            default="未分类"
        ))

        heading = f"**{index:02d}  /  {mission}**"
        if mission_en:
            heading += f"  ·  *{mission_en}*"
        detail = f"🎯 **目标掉落：** {loot}"
        if loot_en:
            detail += f"  (*{loot_en}*)"
        detail += f"\n\n🏷️ **装备类型：** {category}"

        modules.append({
            "type": "section",
            "paragraph": [{
                "type": "markdown",
                "text": heading + "\n\n" + detail
            }]
        })

    modules.append({
        "type": "section",
        "paragraph": [{
            "type": "markdown",
            "text": (
                "🟠 **特工，祝你行动顺利。**\n\n"
                + ("此频道已开启每日自动情报推送。" if subscription
                   else "每日目标掉落情报已更新。")
            )
        }]
    })

    card = {
        "data": [{
            "type": "card",
            "border_color": "#F36B21",
            "size": "medium",
            "modules": modules
        }]
    }
    return json.dumps(card, ensure_ascii=False, separators=(",", ":"))


# 保留旧函数名，避免仓库其他脚本或外部调用因导入名称变化而中断。
def build_markdown() -> str:
    """兼容旧接口：返回可读文本版本。"""
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"每日掉落文件不存在：{DATA_PATH}")
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8-sig"))
    rows = locate_records(payload)
    blocks = []
    for index, row in enumerate(rows, 1):
        mission = clean_text(pick(row, "mission", "mission_name", "name", default="未知副本"))
        loot = clean_text(pick(row, "loot", "target_loot", "item", default="未知掉落"))
        category = clean_text(pick(row, "category", "loot_type", "type", default="未分类"))
        blocks.append(
            f"【{index:02d}】{mission}\n"
            f"🎁 掉落装备：{loot}\n"
            f"🏷️ 装备类型：{category}"
        )
    return "\n\n".join(blocks)
