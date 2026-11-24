# -*- coding: utf-8 -*-
"""构建黑盒原生卡片：SHD 每日目标掉落情报。"""
from __future__ import annotations
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
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


def resolve_icon_url(icons: dict, loot: str) -> str | None:
    """仅使用每日 JSON icons 精确映射，不搜索、不猜测图标。"""
    filename = icons.get(loot)
    if not isinstance(filename, str) or not filename.strip():
        return None
    return ICON_BASE_URL + quote(filename.strip().lstrip("/"), safe="/._-")


def next_beijing_16_timestamp() -> int:
    """计算北京时间明天 16:00 的 Unix 秒级时间戳。"""
    beijing_tz = ZoneInfo("Asia/Shanghai")
    now = datetime.now(beijing_tz)
    target = (now + timedelta(days=1)).replace(
        hour=16, minute=0, second=0, microsecond=0
    )
    return int(target.timestamp())


def build_card_json(subscription: bool = False) -> str:
    """生成黑盒 msg_type 20 原生卡片 JSON。"""
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"每日掉落文件不存在：{DATA_PATH}")
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("每日掉落 JSON 根节点格式错误")
    rows = locate_records(payload)
    icons = payload.get("icons") if isinstance(payload.get("icons"), dict) else {}

    summary = [
        "**THE DIVISION 2  /  SHD FIELD INTEL**",
        f"📅 **情报日期：** {clean_text(payload.get('snapshot_date') or '日期未知')}",
    ]
    if subscription:
        summary.append("✅ **订阅状态：** 已开启每日自动情报")

    modules = [
        {"type": "header", "content": {"type": "plain-text", "text": "🟠 SHD  |  每日目标掉落"}},
        {"type": "section", "paragraph": [{"type": "markdown", "text": "\n\n".join(summary)}]},
        {
            "type": "countdown",
            "mode": "calendar",
            "end_time": next_beijing_16_timestamp(),
        },
    ]

    for index, row in enumerate(rows, 1):
        mission = clean_text(pick(row, "mission", "mission_name", "name", "副本", "副本名称", default="未知行动区域"))
        code = clean_text(pick(row, "mission_code", "code", default=""))
        loot = clean_text(pick(row, "loot", "target_loot", "targetLoot", "item", "装备", "掉落装备", default="未知掉落"))
        category = clean_text(pick(row, "category", "loot_type", "type", "item_type", "装备类型", default="未分类"))

        title = f"**{index:02d}  {mission}**"
        if code:
            title += f"  ·  {code}"
        modules.append({"type": "section", "paragraph": [{"type": "markdown", "text": title}]})

        detail = f"🎁 **目标掉落：** {loot}\n\n🏷️ **装备分类：** {category}"
        image_url = resolve_icon_url(icons, loot)
        if image_url:
            modules.append({
                "type": "section",
                "paragraph": [
                    {"type": "markdown", "text": detail},
                    {"type": "image", "url": image_url, "size": "small"},
                ],
            })
        else:
            modules.append({"type": "section", "paragraph": [{"type": "markdown", "text": detail}]})

    modules.append({
        "type": "section",
        "paragraph": [{"type": "markdown", "text": "🟠 **SHD NETWORK**\n\n情报同步完成 · 特工，祝你行动顺利。"}],
    })
    card = {"data": [{
        "type": "card",
        "border_color": "#F36B21",
        "size": "medium",
        "modules": modules,
    }]}
    return json.dumps(card, ensure_ascii=False, separators=(",", ":"))


def build_markdown(subscription: bool = False) -> str:
    """保留旧接口兼容性。"""
    card = json.loads(build_card_json(subscription))
    lines = []
    for module in card["data"][0]["modules"]:
        for paragraph in module.get("paragraph", []):
            if paragraph.get("type") == "markdown":
                lines.append(paragraph.get("text", ""))
    return "\n\n".join(lines)
