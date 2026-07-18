import re
import time as _time
import httpx

from astrbot.core import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Star, register

from .qqcard import parse_qq_card
from .netease import search_netease, search_netease_multi
from .kugou import parse_kugou_card


MUSIC_DOMAINS = (
    "music.163.com", "163cn.tv",
    "y.qq.com", "c6.y.qq.com", "i.y.qq.com",
    "kugou.com",
)


@register("astrbot_plugin_music_card", "Sihnbaobao", "音乐链接转网易云卡片", "1.1.0")
class MusicCardPlugin(Star):

    def __init__(self, context, config=None):
        super().__init__(context)
        self._card_sent = False
        self._search_count = 0
        self._last_call = 0

    # ── 消息发送 ──

    async def _send(self, event, message):
        try:
            gid = event.message_obj.group_id
            if gid:
                await event.bot.api.call_action(
                    "send_group_msg", group_id=gid, message=message)
            else:
                await event.bot.api.call_action(
                    "send_private_msg", user_id=event.get_sender_id(), message=message)
        except Exception as e:
            logger.error(f"发送失败:{e}")
            raise

    async def _netease_card(self, event, song_id):
        msg = [{"type": "music", "data": {"type": "163", "id": song_id}}]
        await self._send(event, msg)
        logger.info(f"163卡:id={song_id}")

    # ── 链接处理 ──

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def music_card(self, event: AstrMessageEvent):
        self._card_sent = False
        self._search_count = 0
        text = event.message_str or ""

        # 网易云
        if "music.163.com" in text or "163cn.tv" in text:
            m = re.search(r"https?://[^\s]+", text)
            if m:
                url = m.group(0)
                if "163cn.tv" in url:
                    try:
                        async with httpx.AsyncClient(
                            follow_redirects=True, timeout=10
                        ) as c:
                            url = str((await c.get(url)).url)
                    except Exception:
                        pass
                m2 = re.search(r"id=(\d+)", url)
                if m2:
                    await self._netease_card(event, m2.group(1))
                    event.stop_event()
                    return

        # QQ音乐
        if "y.qq.com" in text or "c6.y.qq.com" in text or "i.y.qq.com" in text:
            info = await parse_qq_card(text)
            if info:
                ne = await search_netease(info.get("title", ""), info.get("singer", ""))
                if ne:
                    await self._netease_card(event, ne["id"])
                else:
                    await self._custom_card(event, info)
            event.stop_event()
            return

        # 酷狗
        if "kugou.com" in text:
            info = await parse_kugou_card(text)
            if info:
                ne = await search_netease(info["title"], info["singer"])
                if ne:
                    await self._netease_card(event, ne["id"])
            event.stop_event()
            return

        if any(k in text for k in MUSIC_DOMAINS):
            event.stop_event()

    async def _custom_card(self, event, qq):
        await self._send(event, [{
            "type": "music",
            "data": {
                "type": "custom",
                "url": qq.get("url", ""),
                "audio": qq.get("audio", ""),
                "image": qq.get("pic", ""),
                "title": qq.get("title", "QQ音乐"),
                "content": qq.get("singer", ""),
                "app": "QQ音乐",
            }
        }])

    # ── LLM 工具 ──

    def _check_reset(self):
        now = _time.time()
        if now - self._last_call > 5:
            self._card_sent = False
            self._search_count = 0
        self._last_call = now

    @filter.llm_tool(name="search_songs")
    async def search_songs(self, event: AstrMessageEvent, song_name: str, artist: str = ""):
        """搜索歌曲(仅搜索一次,不发送卡片)。搜不到就放弃。

        Args:
            song_name(string): 歌曲名
            artist(string): 歌手名,知道就填
        """
        self._check_reset()
        self._search_count += 1
        if self._search_count > 3:
            return "不想搜了。"
        q = f"{song_name} {artist}".strip()
        results = await search_netease_multi(q, limit=3)
        if not results:
            return "没找到。"
        lines = [f'歌名:{s["name"]} 歌手:{s["artist"]} ID:{s["id"]}' for s in results]
        return "\n".join(lines) + "\n\n(中文歌名可能以日语显示,如'魔法'='まほう')"

    @filter.llm_tool(name="send_song_card")
    async def send_song_card(self, event: AstrMessageEvent, song_id: str):
        """发送指定歌曲ID的网易云音乐卡片。先调用search_songs确认歌曲后再用。

        Args:
            song_id(string): 网易云歌曲ID
        """
        self._check_reset()
        if self._card_sent:
            return "不想发了。"
        self._card_sent = True
        await self._netease_card(event, song_id)
        return "已发送"
