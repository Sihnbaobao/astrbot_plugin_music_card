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
        """\u641c\u7d22\u4e00\u9996\u786e\u5b9e\u5b58\u5728\u7684\u6b4c\u66f2\u5e76\u53d1\u9001\u97f3\u4e50\u5361\u7247\u3002
        \u4ec5\u5728\u4f60\u786e\u4fe1\u6b4c\u66f2\u540d\u548c\u6b4c\u624b\u540d\u90fd\u51c6\u786e\u65f6\u624d\u8c03\u7528\uff0c\u4e0d\u8981\u7528\u6a21\u7cca\u6216\u731c\u6d4b\u7684\u5173\u952e\u8bcd\u3002
        \u53ea\u4f20\u4f60\u786e\u5b9a\u7684\u6b4c\u540d+\u6b4c\u624b\uff0c\u4e0d\u786e\u5b9a\u5c31\u4e0d\u8981\u8c03\u7528\u3002

        Args:
            query(string): \u7cbe\u786e\u7684\u6b4c\u66f2\u540d\u79f0+\u6b4c\u624b\u540d\uff0c\u5982\"\u6674\u5929 \u5468\u6770\u4f26\"\u3002\u4e0d\u786e\u5b9a\u65f6\u4e0d\u8981\u8c03\u7528\u3002
        """
        ne = await search_netease(query)
        if ne:
            q = query.lower()
            name = ne["name"].lower()
            if any(w in name for w in q.split()):
                await self.send_netease_card(event, str(ne["id"]))
                return f"\u5df2\u53d1\u9001: {ne['name']}"
            return f"\u672a\u627e\u5230\u7b26\u5408\"{query}\"\u7684\u6b4c\u66f2\uff0c\u641c\u5230\u7684\u662f: {ne['name']}"
        return f"\u672a\u627e\u5230: {query}"


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
