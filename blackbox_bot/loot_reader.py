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


def icon_url(icons: dict, loot_name: str) -> str | None:
    """按掉落名称精确匹配 JSON icons，不猜测或错配图标。"""
    filename = icons.get(loot_name)
    if not isinstance(filename, str) or not filename.strip():
        return None
    return ICON_BASE_URL + quote(filename.strip().lstrip("/"), safe="/._-")


def build_card_json(subscription: bool = False) -> str:
    """构建黑盒 msg_type=20 原生聊天卡片，采用紧凑消息布局。"""
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"每日掉落文件不存在：{DATA_PATH}")
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("每日掉落 JSON 根节点格式错误")

    rows = locate_records(payload)
    icons = payload.get("icons") if isinstance(payload.get("icons"), dict) else {}
    snapshot_date = clean_text(payload.get("snapshot_date") or "日期未知")
    playlist = payload.get("current_playlist")

    summary = [
        "**THE DIVISION 2  /  SHD FIELD INTEL**",
        f"📅 **日期**  {snapshot_date}",
        f"🎯 **行动区域**  {len(rows)} 个",
    ]
    if playlist is not None:
        summary.append(f"🛰️ **轮换编号**  #{clean_text(playlist)}")
    if subscription:
        summary.insert(1, "✅ **订阅成功**  ·  每日情报已接入")

    modules = [
        {
            "type": "header",
            "content": {"type": "plain-text", "text": "SHD 情报终端"},
        },
        {
            "type": "section",
            "paragraph": [{"type": "markdown", "text": "\n".join(summary)}],
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
        title = f"**{index:02d}  {mission}**"
        if mission_code:
            title += f"  ·  {mission_code}"

        modules.append({
            "type": "section",
            "paragraph": [{
                "type": "markdown",
                "text": f"{title}\n🎁 **{loot}**\n🏷️ {category}",
            }],
        })

        url = icon_url(icons, loot)
        if url:
            modules.append({
                "type": "images",
                "urls": [{"url": url}],
            })

    footer = "━━━━━━━━━━━━━━\n🟠 **SHD NETWORK**  ·  情报同步完成"
    if subscription:
        footer = "━━━━━━━━━━━━━━\n🟠 **SHD NETWORK**  ·  本频道已开启每日自动情报推送"
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
    """兼容旧接口，返回纯文本版本。"""
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
            f"**{index:02d}  {mission}**\n"
            f"🎁 {loot}\n"
            f"🏷️ {category}"
        )
    return "\n\n".join(blocks)
