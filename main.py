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
from .netease import search_netease, search_netease_multi
from .kugou import parse_kugou_card


@register(
    "astrbot_plugin_music_card",
    "Sihnbaobao",
    "音乐链接转网易云卡片",
    "1.0.3"
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

    @filter.llm_tool(name="search_songs")
    async def search_songs(self, event: AstrMessageEvent, song_name: str, artist: str):
        """搜索歌曲(仅搜索一次,不发送卡片)。搜不到就放弃,不要反复搜或找替代歌曲。
        如果是你自己提到的歌搜不到说明你记错了歌名,直接承认记错,不要发别的歌糊弄。
        如果是用户要求你发的歌搜不到,直接告诉用户搜不到,让用户确认歌名。

        Args:
            song_name(string): 准确的歌曲名,如"夜明けと蛍"
            artist(string): 歌手名,如"花谱"。知道就填,不确定就留空
        """
        query = f"{song_name} {artist}".strip()
        results = await search_netease_multi(query, limit=3)
        if not results:
            return "搜索结束,未找到匹配的歌曲。如果是你自己提到的歌说明你记错了歌名,直接承认即可。如果是用户让你发的,告诉用户搜不到这个歌名。"

        lines = []
        for s in results:
            lines.append(f'歌名:{s["name"]} 歌手:{s["artist"]} ID:{s["id"]}')
        return "\n".join(lines) + "\n\n注意:核对歌名和歌手是否完全匹配。都不匹配说明歌名或歌手记错了,不要发近似歌曲。"

    @filter.llm_tool(name="send_song_card")
    async def send_song_card(self, event: AstrMessageEvent, song_id: str):
        """发送指定歌曲ID的网易云音乐卡片。必须先调用search_songs确认歌曲后再发送。

        Args:
            song_id(string): 网易云歌曲ID,从search_songs的结果中获取
        """
        await self.send_netease_card(event, song_id)
        return "卡片已发送"

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