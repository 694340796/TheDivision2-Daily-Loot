# -*- coding: utf-8 -*-
"""读取固定每日掉落文件，并生成适合黑盒聊天窗口阅读的纯文本列表。"""
from __future__ import annotations

import json
from pathlib import Path

DATA_PATH = Path("全境封锁2恶化掉落/每日掉落.json")


def locate_records(payload: dict) -> list:
    candidates = [payload]
    for key in ("data", "result"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            candidates.append(nested)
    for item in candidates:
        for key in ("current", "missions", "items"):
            rows = item.get(key)
            if isinstance(rows, list) and rows:
                return rows
    raise ValueError(f"{DATA_PATH} 中没有非空掉落记录数组")


def pick(record: dict, *keys: str, default: str = "未知") -> str:
    for key in keys:
        value = record.get(key)
        if value not in (None, "", [], {}):
            if isinstance(value, list):
                return "、".join(str(x) for x in value)
            if isinstance(value, dict):
                return str(value.get("name") or value.get("zh") or value)
            return str(value)
    return default


def clean_text(value: object) -> str:
    """避免数据中的换行破坏每条副本的视觉分组。"""
    return " ".join(str(value).replace("\r", " ").replace("\n", " ").split())


def build_markdown() -> str:
    """
    输出纯文本分组列表，而不是 Markdown 表格。
    黑盒客户端对表格的渲染可能压缩列间距，纯文本分组在手机端更易读。
    """
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"每日掉落文件不存在：{DATA_PATH}")
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("每日掉落 JSON 根节点格式错误")

    rows = locate_records(payload)
    entries = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        mission = clean_text(pick(
            row, "mission", "mission_name", "name", "副本", "副本名称",
            default="未知副本",
        ))
        loot = clean_text(pick(
            row, "loot", "target_loot", "targetLoot", "item", "装备", "掉落装备",
            default="未知掉落",
        ))
        category = clean_text(pick(
            row, "category", "loot_type", "type", "item_type", "装备类型",
            default="未分类",
        ))
        entries.append((mission, loot, category))

    if not entries:
        raise ValueError("每日掉落 JSON 中没有可展示的有效记录")

    lines = [
        "🎯 全境封锁2｜今日目标掉落",
        f"📦 今日共 {len(entries)} 个目标副本",
        "━━━━━━━━━━━━━━",
    ]
    for index, (mission, loot, category) in enumerate(entries, 1):
        lines.extend([
            f"【{index:02d}】{mission}",
            f"🎁 掉落装备：{loot}",
            f"🏷️ 装备类型：{category}",
            "──────────────",
        ])

    lines.append("以上为当前仓库保存的每日掉落数据")
    return "\n".join(lines)
