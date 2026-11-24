# -*- coding: utf-8 -*-
"""读取每日掉落数据，并构建适合黑盒聊天窗口的 SHD 原生卡片。"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "全境封锁2恶化掉落" / "每日掉落.json"
ICON_BASE_URL = "https://agenthub.fans/assets/db/img/"


def locate_records(payload: dict) -> list[dict]:
    """读取每日目标数组；兼容根节点及常见 data/result 包装。"""
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


def clean_text(value: object) -> str:
    return " ".join(str(value).replace("\\r", " ").replace("\\n", " ").split())


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


def _image_module(filename: str) -> dict:
    """黑盒原生卡片 images 模块；每条掉落单独放图，避免图标错位。"""
    safe_path = quote(str(filename).lstrip("/"), safe="/._-")
    return {
        "type": "images",
        "urls": [{"url": ICON_BASE_URL + safe_path}],
    }


def build_card_json(subscription: bool = False) -> str:
    """构建 msg_type=20 原生卡片；图标由每日 JSON 的 icons 字典动态匹配。"""
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"每日掉落文件不存在：{DATA_PATH}")

    payload = json.loads(DATA_PATH.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("每日掉落 JSON 根节点格式错误")

    rows = locate_records(payload)
    icons = payload.get("icons") if isinstance(payload.get("icons"), dict) else {}
    snapshot_date = clean_text(payload.get("snapshot_date") or "日期未知")
    playlist = payload.get("current_playlist")

    intro = [
        "**THE DIVISION 2  /  SHD FIELD INTEL**",
        f"📅 **情报日期**  {snapshot_date}",
        f"🎯 **目标区域**  {len(rows)} 个",
    ]
    if playlist is not None:
        intro.append(f"🛰️ **行动轮换**  #{clean_text(playlist)}")
    if subscription:
        intro.insert(1, "✅ **订阅成功 · 每日情报已接入**")

    modules = [
        {
            "type": "header",
            "content": {"type": "plain-text", "text": "SHD  |  每日目标掉落"},
        },
        {
            "type": "section",
            "paragraph": [{"type": "markdown", "text": "\\n\\n".join(intro)}],
        },
    ]

    for index, row in enumerate(rows, 1):
        mission = clean_text(pick(
            row, "mission", "mission_name", "name", "副本", "副本名称",
            default="未知行动区域",
        ))
        mission_code = clean_text(pick(row, "mission_code", "code", default=""))
        loot = clean_text(pick(
            row, "loot", "target_loot", "targetLoot", "item", "装备", "掉落装备",
            default="未知掉落",
        ))
        category = clean_text(pick(
            row, "category", "loot_type", "type", "item_type", "装备类型",
            default="未分类",
        ))

        mission_label = f"**{index:02d}  {mission}**"
        if mission_code:
            mission_label += f"  `{mission_code}`"
        paragraph = (
            f"{mission_label}\\n"
            f"▸ **目标掉落：** {loot}\\n"
            f"▸ **装备分类：** {category}"
        )
        modules.append({
            "type": "section",
            "paragraph": [{"type": "markdown", "text": paragraph}],
        })

        # 只使用 JSON icons 中与本条掉落名称完全匹配的图标，自动适配品牌、
        # 装备组及装备部位；没有映射时不显示错误或猜测图标。
        icon_filename = icons.get(loot)
        if isinstance(icon_filename, str) and icon_filename.strip():
            modules.append(_image_module(icon_filename))

    footer = "🟠 **SHD NETWORK**  ·  情报同步完成\\n特工，祝你行动顺利。"
    if subscription:
        footer = "🟠 **SHD NETWORK**  ·  本频道已开启每日自动情报推送"
    modules.append({
        "type": "section",
        "paragraph": [{"type": "markdown", "text": footer}],
    })

    card = {
        "data": [{
            "type": "card",
            "border_color": "#F36B21",
            "size": "medium",
            "modules": modules,
        }]
    }
    return json.dumps(card, ensure_ascii=False, separators=(",", ":"))


def build_markdown() -> str:
    """兼容旧接口：返回纯文本版本。"""
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"每日掉落文件不存在：{DATA_PATH}")
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8-sig"))
    rows = locate_records(payload)
    icons = payload.get("icons") if isinstance(payload.get("icons"), dict) else {}
    blocks = []
    for index, row in enumerate(rows, 1):
        mission = clean_text(pick(row, "mission", "mission_name", "name", default="未知副本"))
        loot = clean_text(pick(row, "loot", "target_loot", "item", default="未知掉落"))
        category = clean_text(pick(row, "category", "loot_type", "type", default="未分类"))
        icon = icons.get(loot)
        icon_line = f"🖼️ 图标：{ICON_BASE_URL}{quote(str(icon), safe='/._-')}" if icon else ""
        blocks.append(
            f"**{index:02d}  {mission}**\\n"
            f"🎯 目标掉落：{loot}\\n"
            f"🏷️ 装备分类：{category}"
            + (f"\\n{icon_line}" if icon_line else "")
        )
    return "\\n\\n".join(blocks)
