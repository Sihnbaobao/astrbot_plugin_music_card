import re
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
from .kugou import parse_kugou_card


@register(
    "astrbot_plugin_music_card",
    "Sihnbaobao",
    "音乐链接转网易云卡片",
    "1.0.1"
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
        message = [{"type": "music", "data": {"type": "163", "id": song_id}}]
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


    @filter.llm_tool(name="search_song")
    async def search_song(self, event: AstrMessageEvent, query: str):
        """搜索一首歌并发送音乐卡片。在聊天中提到某首歌时可调用此工具发送该歌曲的卡片。

        Args:
            query(string): 要搜索的歌曲名称,最好包含歌手名,例如"晴天 周杰伦"
        """
        ne = await search_netease(query)
        if ne:
            await self.send_netease_card(event, str(ne["id"]))
            yield event.plain_result(f"已发送歌曲卡片: {ne['name']}")
        else:
            yield event.plain_result(f"未找到歌曲: {query}")


    @filter.event_message_type(filter.EventMessageType.ALL)
    async def music_card(self, event: AstrMessageEvent):

        text = event.message_str or ""

        # ---- 点歌命令 ----
        if text.strip().startswith("/song ") or text.strip().startswith("/点歌 "):
            query = text.strip().split(" ", 1)[1] if " " in text else ""
            if query:
                ne = await search_netease(query)
                if ne:
                    await self.send_netease_card(event, ne["id"])
                else:
                    await self.send_music(event, [{"type": "text", "data": {"text": f"没找到: {query}"}}])
            event.stop_event()
            return

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
                ne = await search_netease(qq.get("title", ""), qq.get("singer", ""))
                if ne:
                    await self.send_netease_card(event, ne["id"])
                    event.stop_event()
                    return
                await self.send_custom_card(event, qq)
            event.stop_event()
            return

        # ---- 酷狗 ----
        if "kugou.com" in text:
            kg = await parse_kugou_card(text)
            if kg:
                ne = await search_netease(kg["title"], kg["singer"])
                if ne:
                    await self.send_netease_card(event, ne["id"])
                    event.stop_event()
                    return
            event.stop_event()
            return

        if any(k in text for k in ["music.163.com","163cn.tv","y.qq.com","c6.y.qq.com","i.y.qq.com","kugou.com"]):
            event.stop_event()
