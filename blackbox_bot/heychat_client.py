# -*- coding: utf-8 -*-
"""黑盒机器人 WebSocket 客户端及一次性订阅持久化。"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request

import websockets

from .loot_reader import build_card_json

logger = logging.getLogger(__name__)

COMMAND_ID = os.getenv("HEYCHAT_COMMAND_ID", "2124398728264114176")
REPOSITORY = os.getenv("LOOT_REPOSITORY", "694340796/TheDivision2-Daily-Loot")
BRANCH = os.getenv("LOOT_BRANCH", "main")
SUBSCRIPTION_PATH = "data/blackbox_subscription.json"

WSS_URL = "wss://chat.xiaoheihe.cn/chatroom/ws/connect?"
COMMON_PARAMS = (
    "chat_os_type=bot&client_type=heybox_chat"
    "&chat_version=999.0.0&chat_version=1.24.5"
)
HTTP_HOST = "https://chat.xiaoheihe.cn"
SEND_MSG_URL = "/chatroom/v2/channel_msg/send?"
PING_INTERVAL = 30


class HeychatBot:
    def __init__(self, token: str):
        self.token = token
        self.websocket = None
        self.stopping = False

    def send_message(self, room_id: str, channel_info: dict, message: str) -> None:
        """兼容文本提示，但统一通过 msg_type=20 原生卡片发送。"""
        card = {
            "data": [{
                "type": "card",
                "border_color": "#F36B21",
                "size": "medium",
                "modules": [{
                    "type": "section",
                    "paragraph": [{"type": "markdown", "text": message}],
                }],
            }]
        }
        self.send_card(room_id, channel_info, json.dumps(card, ensure_ascii=False, separators=(",", ":")))

    def send_card(self, room_id: str, channel_info: dict, card_message: str) -> None:
        """发送黑盒原生卡片（msg_type=20）。"""
        channel_id = str(channel_info.get("channel_id", ""))
        if not room_id or not channel_id:
            raise ValueError("命令事件缺少 room_id 或 channel_id")
        payload = {
            "msg": card_message,
            "msg_type": 20,
            "heychat_ack_id": "",
            "reply_id": "",
            "room_id": str(room_id),
            "addition": "{}",
            "at_user_id": "",
            "at_role_id": "",
            "mention_channel_id": "",
            "channel_id": channel_id,
            "channel_type": int(channel_info.get("channel_type", 0) or 0),
        }
        url = HTTP_HOST + SEND_MSG_URL + COMMON_PARAMS
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json;charset=UTF-8",
                "token": self.token,
                "User-Agent": "TheDivision2-BlackboxBot/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8", errors="replace")
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(f"黑盒卡片接口 HTTP {response.status}: {body[:300]}")
            try:
                result = json.loads(body) if body else {}
            except json.JSONDecodeError:
                result = {}
            if isinstance(result, dict):
                status = result.get("status")
                code = result.get("code", 0)
                if status not in (None, "ok", "success") or code not in (0, 200, "0", "200", None):
                    raise RuntimeError(f"黑盒卡片接口业务失败：{body[:500]}")
            logger.info("黑盒原生卡片请求已接受，HTTP %s，响应=%s", response.status, body[:300])

    def save_subscription(self, room_id: str, channel_info: dict) -> None:
        """用 Actions 的 GITHUB_TOKEN 将订阅频道保存为仓库固定 JSON 文件。"""
        github_token = os.getenv("GITHUB_TOKEN", "").strip()
        if not github_token:
            raise RuntimeError("缺少 GITHUB_TOKEN；请给机器人工作流 contents: write 权限")
        if not room_id or not channel_info.get("channel_id"):
            raise ValueError("订阅事件缺少 room_id 或 channel_id")

        api_url = (
            f"https://api.github.com/repos/{REPOSITORY}/contents/"
            f"{urllib.parse.quote(SUBSCRIPTION_PATH, safe='/')}"
        )
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {github_token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "TheDivision2-BlackboxBot",
        }
        current_sha = None
        get_req = urllib.request.Request(api_url + f"?ref={urllib.parse.quote(BRANCH)}", headers=headers)
        try:
            with urllib.request.urlopen(get_req, timeout=20) as response:
                current = json.loads(response.read().decode("utf-8"))
                current_sha = current.get("sha")
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise

        record = {
            "room_id": str(room_id),
            "channel_info": {
                "channel_id": str(channel_info.get("channel_id")),
                "channel_type": int(channel_info.get("channel_type", 0) or 0),
            },
            "subscribed_at": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
        }
        encoded = base64.b64encode(
            (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        ).decode("ascii")
        body = {
            "message": "chore: save blackbox daily loot subscription",
            "content": encoded,
            "branch": BRANCH,
        }
        if current_sha:
            body["sha"] = current_sha
        put_req = urllib.request.Request(
            api_url,
            data=json.dumps(body).encode("utf-8"),
            headers={**headers, "Content-Type": "application/json"},
            method="PUT",
        )
        with urllib.request.urlopen(put_req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            logger.info("订阅频道已保存，commit=%s", (result.get("commit") or {}).get("sha"))

    async def handle_command(self, event: dict) -> None:
        command_info = event.get("command_info") or {}
        if str(command_info.get("id", "")) != COMMAND_ID:
            return
        room_info = event.get("room_base_info") or {}
        channel_info = event.get("channel_base_info") or {}
        room_id = str(room_info.get("room_id", ""))
        try:
            # 先保存订阅，确保后续每日定时推送使用当前房间。
            await asyncio.to_thread(self.save_subscription, room_id, channel_info)
        except Exception:
            logger.exception("保存订阅失败")
            try:
                await asyncio.to_thread(
                    self.send_message,
                    room_id,
                    channel_info,
                    "订阅设置失败，无法保存房间信息。请检查机器人权限和 GitHub Actions 日志。",
                )
            except Exception:
                logger.exception("发送订阅失败提示也失败")
            return

        try:
            # 订阅成功后，发送当前数据的 SHD 风格 Markdown 情报。
            card_message = await asyncio.to_thread(build_card_json, True)
        except Exception:
            logger.exception("订阅已保存，但构建每日掉落卡片失败")
            try:
                await asyncio.to_thread(
                    self.send_message,
                    room_id,
                    channel_info,
                    "订阅已保存，但当前无法生成每日掉落情报，请稍后重试。",
                )
            except Exception:
                logger.exception("发送卡片生成失败提示也失败")
            return

        try:
            await asyncio.to_thread(self.send_card, room_id, channel_info, card_message)
            logger.info(
                "订阅成功原生卡片已发送，room_id=%s channel_id=%s",
                room_id,
                channel_info.get("channel_id"),
            )
        except Exception:
            logger.exception("订阅已保存，但发送订阅情报失败")

    async def heartbeat(self) -> None:
        while not self.stopping:
            await asyncio.sleep(PING_INTERVAL)
            if self.websocket is not None:
                try:
                    await self.websocket.send("PING")
                except Exception:
                    logger.warning("发送心跳失败，等待连接重建")
                    return

    async def run_once(self) -> None:
        ssl_context = ssl.create_default_context()
        async with websockets.connect(
            self.websocket_url(),
            ssl=ssl_context,
            extra_headers={
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
            ping_interval=None,
            close_timeout=10,
            max_size=2 * 1024 * 1024,
        ) as websocket:
            self.websocket = websocket
            logger.info("黑盒机器人 WebSocket 已连接")
            heartbeat_task = asyncio.create_task(self.heartbeat())
            try:
                async for raw_message in websocket:
                    if raw_message in ("PONG", "pong", "PING"):
                        continue
                    try:
                        packet = json.loads(raw_message)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    if str(packet.get("type", "")) != "50":
                        continue
                    event_data = packet.get("data") or {}
                    if isinstance(event_data, dict):
                        await self.handle_command(event_data)
            finally:
                self.websocket = None
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

    def websocket_url(self) -> str:
        token = urllib.parse.quote(self.token, safe="")
        return WSS_URL + COMMON_PARAMS + "&token=" + token

    async def run_forever(self) -> None:
        delay = 3
        while not self.stopping:
            try:
                await self.run_once()
                delay = 3
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("黑盒连接中断")
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60)


async def main() -> None:
    token = os.getenv("HEYCHAT_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("请设置环境变量 HEYCHAT_BOT_TOKEN")
    await HeychatBot(token).run_forever()


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(main())
