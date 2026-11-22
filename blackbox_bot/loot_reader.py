# -*- coding: utf-8 -*-
"""Read the fixed daily loot snapshot and render the bot's Markdown table."""
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


def markdown_escape(value: object) -> str:
    return str(value).strip().replace("|", r"\|").replace("\r", " ").replace("\n", " ")


def build_markdown() -> str:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"每日掉落文件不存在：{DATA_PATH}")
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("每日掉落 JSON 根节点格式错误")
    rows = locate_records(payload)
    lines = [
        "| 副本名称 | 掉落装备名称 | 装备类型 |",
        "|---|---|---|",
    ]
    for row in rows:
        if not isinstance(row, dict):
            continue
        mission = pick(row, "mission", "mission_name", "name", "副本", "副本名称", default="未知副本")
        loot = pick(row, "loot", "target_loot", "targetLoot", "item", "装备", "掉落装备", default="未知掉落")
        category = pick(row, "category", "loot_type", "type", "item_type", "装备类型", default="未分类")
        lines.append(
            f"| {markdown_escape(mission)} | {markdown_escape(loot)} | {markdown_escape(category)} |"
        )
    if len(lines) == 2:
        raise ValueError("每日掉落 JSON 中没有可展示的有效记录")
    return "\n".join(lines)
