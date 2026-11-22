# -*- coding: utf-8 -*-
"""从仓库固定 JSON 文件读取每日掉落，并生成中文 Markdown 表格。"""
from __future__ import annotations

import json
from pathlib import Path

DATA_PATH = Path("data/daily_loot.json")


def locate_records(payload: dict) -> list:
    candidates = [payload]
    if isinstance(payload.get("data"), dict):
        candidates.append(payload["data"])
    for item in candidates:
        rows = item.get("current")
        if isinstance(rows, list) and rows:
            return rows
    raise ValueError("data/daily_loot.json 中没有非空 current 数组")


def markdown_escape(value: object) -> str:
    text = str(value or "未知").strip()
    return text.replace("|", r"\|").replace("\r", " ").replace("\n", " ")


def build_markdown() -> str:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"每日掉落文件不存在：{DATA_PATH}")
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8-sig"))
    rows = locate_records(payload)
    lines = [
        "| 副本名称 | 掉落装备名称 | 装备类型 |",
        "|---|---|---|",
    ]
    for item in rows:
        if not isinstance(item, dict):
            continue
        mission = item.get("mission") or "未知副本"
        loot = item.get("loot") or "未知掉落"
        category = item.get("category") or item.get("loot_type") or item.get("type") or "未分类"
        lines.append(
            f"| {markdown_escape(mission)} | {markdown_escape(loot)} | {markdown_escape(category)} |"
        )
    if len(lines) == 2:
        raise ValueError("每日掉落 JSON 中没有可展示的记录")
    return "\n".join(lines)
