# -*- coding: utf-8 -*-
"""从 GitHub 仓库读取每日掉落 Python 文件，并生成中文 Markdown 表格。"""

from __future__ import annotations

import ast
import logging
import os
import urllib.request
from urllib.parse import quote

logger = logging.getLogger(__name__)

REPOSITORY = os.getenv("LOOT_REPOSITORY", "694340796/TheDivision2-Daily-Loot")
BRANCH = os.getenv("LOOT_BRANCH", "main")
DATA_PATH = os.getenv(
    "LOOT_DATA_PATH",
    "history/全境封锁2每日掉落.py",
)


def fetch_python_text() -> str:
    """读取仓库当前分支上的原始 Python 文件。"""
    path = quote(DATA_PATH, safe="/")
    url = (
        f"https://raw.githubusercontent.com/{REPOSITORY}/"
        f"{BRANCH}/{path}"
    )
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "TheDivision2-BlackboxBot/1.0",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8-sig")


def read_assignments(source: str) -> dict:
    """只解析字面量赋值，不执行仓库中的 Python 代码。"""
    tree = ast.parse(source)
    wanted = {"CURRENT", "SNAPSHOT_DATE", "TOTAL"}
    values = {}

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in wanted:
                    values[target.id] = ast.literal_eval(node.value)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id in wanted:
                values[node.target.id] = ast.literal_eval(node.value)

    if not isinstance(values.get("CURRENT"), list):
        raise ValueError("掉落数据文件中没有有效的 CURRENT 列表")
    return values


def markdown_escape(value: object) -> str:
    text = str(value or "未知").strip()
    return (
        text.replace("|", r"\|")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def build_markdown() -> str:
    source = fetch_python_text()
    data = read_assignments(source)
    rows = data["CURRENT"]

    lines = [
        "| 副本名称 | 掉落装备名称 | 装备类型 |",
        "|---|---|---|",
    ]

    for item in rows:
        if not isinstance(item, dict):
            continue

        # 只读取中文字段，绝不显示 mission_en / loot_en 等英文字段。
        mission = item.get("mission") or "未知副本"
        loot = item.get("loot") or "未知掉落"
        category = (
            item.get("category")
            or item.get("loot_type")
            or item.get("type")
            or "未分类"
        )

        lines.append(
            f"| {markdown_escape(mission)} "
            f"| {markdown_escape(loot)} "
            f"| {markdown_escape(category)} |"
        )

    if len(lines) == 2:
        raise ValueError("CURRENT 中没有可展示的掉落记录")

    return "\n".join(lines)
