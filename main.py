import re
import os
import httpx

from astrbot.core import logger

from astrbot.api.event import (
    filter,
    AstrMessageEvent
)

from astrbot.api.star import (
    Star,
    register
)

from .qqcard import parse_qq_card
from .netease import search_netease


@register(
    "astrbot_plugin_music_card",
    "Sihnbaobao",
    "QQ音乐网易云音乐链接转换音乐卡片",
    "2.0.0"
)
class MusicCardPlugin(Star):

    def __init__(self, context, config=None):
        super().__init__(context)


    async def send_music(self, event, message):
        try:
            if event.message_obj.group_id:
                await event.bot.api.call_action(
                    "send_group_msg",
                    group_id=event.message_obj.group_id,
                    message=message
                )
            else:
                await event.bot.api.call_action(
                    "send_private_msg",
                    user_id=event.get_sender_id(),
                    message=message
                )
        except Exception as e:
            logger.error(f"发送消息失败:{e}")
            raise


    async def send_netease_card(self, event, song_id):
        message = [
            {
                "type": "music",
                "data": {
                    "type": "163",
                    "id": song_id
                }
            }
        ]
        logger.info(f"发送网易云卡片:id={song_id}")
        await self.send_music(event, message)


    async def send_custom_card(self, event, qq):
        message = [
            {
                "type": "music",
                "data": {
                    "type": "custom",
                    "url": qq.get("url", ""),
                    "audio": qq.get("audio", ""),
                    "image": qq.get("pic", ""),
                    "title": qq.get("title", "QQ音乐"),
                    "content": qq.get("singer", ""),
                    "app": "QQ音乐"
                }
            }
        ]
        logger.info("发送custom卡片")
        await self.send_music(event, message)


    @filter.event_message_type(filter.EventMessageType.ALL)
    async def music_card(self, event: AstrMessageEvent):

        text = event.message_str or ""

        # ---- 网易云 ----
        if "music.163.com" in text or "163cn.tv" in text:
            m = re.search(r"https?://[^\s]+", text)
            if not m:
                return
            url = m.group(0)

            if "163cn.tv" in url:
                try:
                    async with httpx.AsyncClient(follow_redirects=True, timeout=10) as c:
                        url = str((await c.get(url)).url)
                except Exception:
                    pass

            m = re.search(r"id=(\d+)", url)
            if m:
                await self.send_netease_card(event, m.group(1))
                event.stop_event()
                return

        # ---- QQ音乐 ----
        if "y.qq.com" in text or "c6.y.qq.com" in text or "i.y.qq.com" in text:
            qq = await parse_qq_card(text)

            if qq:
                title = qq.get("title", "")
                singer = qq.get("singer", "")

                ne = await search_netease(title, singer)

                if ne:
                    logger.info(f"QQ->网易云:{title}-{singer} -> id={ne['id']}")
                    await self.send_netease_card(event, ne["id"])
                    event.stop_event()
                    return

                logger.info(f"网易云未找到,fallback custom:{title}")
                await self.send_custom_card(event, qq)

            event.stop_event()
            return

        # 防止AI处理音乐链接
        if any(k in text for k in ["music.163.com","163cn.tv","y.qq.com","c6.y.qq.com","i.y.qq.com"]):
            event.stop_event()
