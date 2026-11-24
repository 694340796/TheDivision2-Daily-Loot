# -*- coding: utf-8 -*-
"""构建黑盒原生 SHD 每日掉落卡片。"""
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


def build_card_json(subscription: bool = False) -> str:
    """生成稳定的 msg_type=20 卡片。暂不混入未经验证的图片模块。"""
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"每日掉落文件不存在：{DATA_PATH}")
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("每日掉落 JSON 根节点格式错误")

    rows = locate_records(payload)
    snapshot_date = clean_text(payload.get("snapshot_date") or "日期未知")
    playlist = payload.get("current_playlist")
    summary = [
        "**THE DIVISION 2  /  SHD FIELD INTEL**",
        f"📅 **情报日期：** {snapshot_date}",
        f"🎯 **目标区域：** {len(rows)} 个",
    ]
    if playlist is not None:
        summary.append(f"🛰️ **行动轮换：** #{clean_text(playlist)}")
    if subscription:
        summary.append("✅ **订阅成功：** 已接入每日自动情报")

    modules = [
        {"type": "header", "content": {"type": "plain-text", "text": "SHD  |  每日目标掉落"}},
        {"type": "section", "paragraph": [{"type": "markdown", "text": "\n".join(summary)}]},
    ]

    for index, row in enumerate(rows, 1):
        mission = clean_text(pick(row, "mission", "mission_name", "name", "副本", "副本名称", default="未知行动区域"))
        code = clean_text(pick(row, "mission_code", "code", default=""))
        loot = clean_text(pick(row, "loot", "target_loot", "targetLoot", "item", "装备", "掉落装备", default="未知掉落"))
        category = clean_text(pick(row, "category", "loot_type", "type", "item_type", "装备类型", default="未分类"))
        title = f"**{index:02d}  {mission}**"
        if code:
            title += f"  ·  {code}"
        text = f"{title}\n🎁 **目标掉落：** {loot}\n🏷️ **装备分类：** {category}"
        modules.append({"type": "section", "paragraph": [{"type": "markdown", "text": text}]})

    footer = "🟠 **SHD NETWORK**  ·  情报同步完成"
    modules.append({"type": "section", "paragraph": [{"type": "markdown", "text": footer}]})
    return json.dumps({
        "data": [{
            "type": "card",
            "border_color": "#F36B21",
            "size": "medium",
            "modules": modules,
        }]
    }, ensure_ascii=False, separators=(",", ":"))


def build_markdown() -> str:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"每日掉落文件不存在：{DATA_PATH}")
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8-sig"))
    rows = locate_records(payload)
    result = []
    for i, row in enumerate(rows, 1):
        mission = clean_text(pick(row, "mission", "mission_name", "name", default="未知副本"))
        loot = clean_text(pick(row, "loot", "target_loot", "item", default="未知掉落"))
        category = clean_text(pick(row, "category", "loot_type", "type", default="未分类"))
        result.append(f"**{i:02d}  {mission}**\n🎁 {loot}\n🏷️ {category}")
    return "\n\n".join(result)
