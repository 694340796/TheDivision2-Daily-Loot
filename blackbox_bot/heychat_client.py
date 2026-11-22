# -*- coding: utf-8 -*-
"""黑盒语音官方 Demo 协议的轻量实现。"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import ssl
import urllib.parse
import urllib.request

import websockets

from .loot_reader import build_markdown

logger = logging.getLogger(__name__)

COMMAND_ID = os.getenv("HEYCHAT_COMMAND_ID", "2124398728264114176")

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

    def websocket_url(self) -> str:
        return (
            WSS_URL
            + COMMON_PARAMS
            + "&token="
            + urllib.parse.quote(self.token, safe="")
        )

    def send_message(self, room_id: str, channel_info: dict, message: str) -> None:
        """按官方 Demo 的字段格式发送 Markdown 消息。"""
        channel_id = str(channel_info.get("channel_id", ""))
        if not room_id or not channel_id:
            raise ValueError("命令事件缺少 room_id 或 channel_id")

        payload = {
            "msg": message,
            "msg_type": 4,
            "heychat_ack_id": "",
            "reply_id": "",
            "room_id": str(room_id),
            "addition": "",
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
                raise RuntimeError(
                    f"黑盒消息接口 HTTP {response.status}: {body[:300]}"
                )
            logger.info("黑盒消息接口已接受请求，HTTP %s", response.status)

    async def handle_command(self, event: dict) -> None:
        command_info = event.get("command_info") or {}
        received_id = str(command_info.get("id", ""))

        if received_id != COMMAND_ID:
            return

        room_info = event.get("room_base_info") or {}
        channel_info = event.get("channel_base_info") or {}
        room_id = str(room_info.get("room_id", ""))

        try:
            markdown = await asyncio.to_thread(build_markdown)
            await asyncio.to_thread(
                self.send_message, room_id, channel_info, markdown
            )
            logger.info("已响应掉落查询命令，command_id=%s", received_id)
        except Exception:
            logger.exception("处理每日掉落命令失败")
            error_text = "每日掉落数据读取失败，请稍后再试。"
            try:
                await asyncio.to_thread(
                    self.send_message, room_id, channel_info, error_text
                )
            except Exception:
                logger.exception("发送错误提示也失败")

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
        # 使用系统默认 CA 校验证书，不沿用旧 Demo 中关闭证书验证的做法。
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
                        logger.debug("忽略非 JSON 消息")
                        continue

                    message_type = str(packet.get("type", ""))
                    if message_type != "50":
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

    bot = HeychatBot(token)
    await bot.run_forever()


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(main())
