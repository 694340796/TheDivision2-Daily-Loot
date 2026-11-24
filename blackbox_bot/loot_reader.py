# -*- coding: utf-8 -*-
"""构建黑盒原生卡片：服务器维护与 SHD 每日目标掉落分开展示。"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import quote

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "全境封锁2恶化掉落" / "每日掉落.json"
MAINTENANCE_PATH = PROJECT_ROOT / "data" / "server_maintenance.json"
ICON_BASE_URL = "https://agenthub.fans/assets/db/img/"
BEIJING = ZoneInfo("Asia/Shanghai")


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
    """计算北京时间下一个 16:00 的 Unix 时间戳。"""
    now = datetime.now(BEIJING)
    target = now.replace(hour=16, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return int(target.timestamp())


def load_maintenance() -> dict:
    if not MAINTENANCE_PATH.is_file():
        return {}
    try:
        data = json.loads(MAINTENANCE_PATH.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def build_maintenance_card(maintenance: dict, now_ts: int) -> dict:
    modules = [
        {"type": "header", "content": {"type": "plain-text", "text": "🛠️ SHD  |  服务器维护"}},
    ]
    start_ts = maintenance.get("maintenance_start_timestamp")
    end_ts = maintenance.get("countdown_end_time")
    duration = maintenance.get("duration_text") or "未知"
    post_date = maintenance.get("post_date_beijing") or "未知"
    start_text = maintenance.get("maintenance_start_beijing") or "未公布"

    # 只有明确存在且已过期的结束时间，才显示无维护。
    if isinstance(end_ts, int) and end_ts <= now_ts:
        modules.append({"type": "section", "paragraph": [{"type": "markdown", "text": "🟢 **当前状态：无维护**"}]})
    elif isinstance(start_ts, int):
        if start_ts > now_ts:
            status = "🟠 **当前状态：即将维护**"
            details = (
                f"{status}\n\n"
                f"🗓️ **发帖日期：** {post_date}（北京时间）\n\n"
                f"⏰ **预计维护开始：** {start_text}（北京时间）\n\n"
                f"⌛ **预计维护时长：** {duration}"
            )
            modules.append({"type": "section", "paragraph": [{"type": "markdown", "text": details}]})
            modules.append({"type": "section", "paragraph": [{"type": "markdown", "text": "**距离维护开始**"}]})
            modules.append({"type": "countdown", "mode": "default", "end_time": start_ts})
        else:
            status = "🔴 **当前状态：维护进行中**"
            details = (
                f"{status}\n\n"
                f"🗓️ **发帖日期：** {post_date}（北京时间）\n\n"
                f"⏰ **维护开始时间：** {start_text}（北京时间）\n\n"
                f"⌛ **预计维护时长：** {duration}"
            )
            modules.append({"type": "section", "paragraph": [{"type": "markdown", "text": details}]})

        # 只有推文明确提供维护时长并计算出结束时间，才展示结束倒计时。
        if isinstance(end_ts, int) and end_ts > now_ts:
            modules.append({"type": "section", "paragraph": [{"type": "markdown", "text": "**距离预计维护结束**"}]})
            modules.append({"type": "countdown", "mode": "default", "end_time": end_ts})
    else:
        modules.append({"type": "section", "paragraph": [{"type": "markdown", "text": (
            "⚪ **当前状态：暂无可确认的维护安排**\n\n"
            "尚未获取到有效的维护开始时间，暂不判断服务器状态。"
        )}]})

    return {
        "type": "card",
        "border_color": "#F36B21",
        "size": "medium",
        "modules": modules,
    }

def build_loot_card(payload: dict, rows: list[dict], icons: dict, subscription: bool) -> dict:
    summary = [
        "**THE DIVISION 2  /  SHD FIELD INTEL**",
        f"📅 **情报日期：** {clean_text(payload.get('snapshot_date') or '日期未知')}",
    ]
    if subscription:
        summary.append("✅ **订阅状态：** 已开启每日自动情报")

    modules = [
        {"type": "header", "content": {"type": "plain-text", "text": "🟠 SHD  |  每日目标掉落"}},
        {"type": "section", "paragraph": [{"type": "markdown", "text": "\n\n".join(summary)}]},
        {"type": "countdown", "mode": "calendar", "end_time": next_beijing_16_timestamp()},
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

    # 原型贮藏箱：只展示 vendor 数组中日期等于当前快照日期的记录。
    snapshot_date = str(payload.get("snapshot_date") or "")
    vendor_rows = payload.get("vendor") if isinstance(payload.get("vendor"), list) else []
    today_vendor = []
    for vendor_row in vendor_rows:
        if isinstance(vendor_row, (list, tuple)) and len(vendor_row) >= 3:
            vendor_date, crate_name, item_name = vendor_row[0], vendor_row[1], vendor_row[2]
        elif isinstance(vendor_row, dict):
            vendor_date = vendor_row.get("date") or vendor_row.get("day")
            crate_name = vendor_row.get("type") or vendor_row.get("vendor") or vendor_row.get("name")
            item_name = vendor_row.get("item") or vendor_row.get("loot") or vendor_row.get("category")
        else:
            continue
        if str(vendor_date) == snapshot_date and crate_name and item_name:
            today_vendor.append((clean_text(crate_name), clean_text(item_name)))

    modules.append({
        "type": "section",
        "paragraph": [{"type": "markdown", "text": "🧰 **原型贮藏箱**"}],
    })
    if today_vendor:
        for crate_name, item_name in today_vendor:
            detail = f"📦 **{crate_name}：** {item_name}"
            image_url = resolve_icon_url(icons, item_name)
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
    else:
        modules.append({
            "type": "section",
            "paragraph": [{"type": "markdown", "text": "今日暂无原型贮藏箱数据。"}],
        })

    modules.append({
        "type": "section",
        "paragraph": [{"type": "markdown", "text": "🟠 **SHD NETWORK**\n\n情报同步完成 · 特工，祝你行动顺利。"}],
    })
    return {
        "type": "card",
        "border_color": "#F36B21",
        "size": "medium",
        "modules": modules,
    }


def build_card_json(subscription: bool = False) -> str:
    """生成黑盒 msg_type 20 原生卡片；维护和掉落拆成独立卡片分栏展示。"""
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"每日掉落文件不存在：{DATA_PATH}")
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("每日掉落 JSON 根节点格式错误")
    rows = locate_records(payload)
    icons = payload.get("icons") if isinstance(payload.get("icons"), dict) else {}
    now_ts = int(datetime.now(BEIJING).timestamp())

    maintenance = load_maintenance()
    maintenance_card = build_maintenance_card(maintenance, now_ts)
    loot_card = build_loot_card(payload, rows, icons, subscription)
    card = {"data": [maintenance_card, loot_card]}
    return json.dumps(card, ensure_ascii=False, separators=(",", ":"))


def build_markdown(subscription: bool = False) -> str:
    """保留旧接口兼容性。"""
    card = json.loads(build_card_json(subscription))
    lines = []
    for item in card["data"]:
        for module in item.get("modules", []):
            for paragraph in module.get("paragraph", []):
                if paragraph.get("type") == "markdown":
                    lines.append(paragraph.get("text", ""))
    return "\n\n".join(lines)
