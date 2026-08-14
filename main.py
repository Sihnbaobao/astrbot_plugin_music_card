import re
import time
import random
import httpx

from astrbot.core import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Star, register

from .qqcard import parse_qq_card
from .netease import search_netease, search_netease_multi, get_netease_song
from .kugou import parse_kugou_card


MUSIC_DOMAINS = (
    "music.163.com", "163cn.tv",
    "y.qq.com",
    "kugou.com",
)


@register("astrbot_plugin_music_card", "Sihnbaobao", "音乐链接转网易云卡片", "1.2.2")
class MusicCardPlugin(Star):

    def __init__(self, context, config=None):
        super().__init__(context)
        self._card_sent = False
        self._search_count = 0
        self._last_call = 0
        self._refuse_rate = 0.35
        self._refuse_lines = (
            "...这首歌...璃月突然不想发了",
            "...算了...今天没什么兴致",
            "...想到了别的事...不发了",
            "...懒得动了...",
        )

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
        """发网易云音乐卡片。发送失败时兜底发歌曲链接。返回是否成功发出。"""
        try:
            song = await get_netease_song(song_id)
        except Exception as e:
            logger.warning(f"163卡:歌曲信息查询失败({e}),直接尝试发卡")
            song = {"url": f"https://music.163.com/song?id={song_id}"}
        if song is None:
            logger.warning(f"163卡:歌曲不存在 id={song_id},不发卡片")
            return False
        try:
            await self._send(event, [{"type": "music", "data": {"type": "163", "id": song_id}}])
            logger.info(f"163卡:id={song_id}")
            return True
        except Exception as e:
            logger.warning(f"163卡片发送失败({e}),改为发送歌曲链接")
            try:
                await self._send(event, song["url"])
                return True
            except Exception as e2:
                logger.warning(f"链接兜底也发送失败:{e2}")
                return False

    # ── 链接处理 ──

    def _card_info(self, event):
        """解析消息段里的 JSON 卡片(QQ/网易云分享卡片),返回 (描述文本, url列表, 是否卡片)。

        卡片消息在 aiocqhttp 通道里是未展开的 Json 段,这里把它转成
        可读文本,让 LLM 也能"看到"歌曲信息。
        """
        desc = ""
        urls = []
        is_card = False
        for seg in event.get_messages():
            if getattr(seg, "type", None) != "Json":
                continue
            is_card = True
            data = getattr(seg, "data", None)
            if not isinstance(data, dict):
                continue

            def _walk(node):
                if isinstance(node, dict):
                    for k, v in node.items():
                        if k.lower() in ("jumpurl", "jump_url", "musicurl", "music_url", "url"):
                            if isinstance(v, str) and v.startswith("http"):
                                urls.append(v)
                        _walk(v)
                elif isinstance(node, list):
                    for item in node:
                        _walk(item)

            _walk(data)
            meta = data.get("meta", {})
            for section in meta.values():
                if not isinstance(section, dict):
                    continue
                title = section.get("title") or section.get("songname")
                singer = section.get("desc") or section.get("singer")
                if title:
                    desc = f"分享歌曲:{title}"
                    if singer:
                        desc += f" 歌手:{singer}"
                    return desc, urls, True
        return desc, urls, is_card

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def music_card(self, event: AstrMessageEvent):
        self._card_sent = False
        self._search_count = 0

        card_desc, card_urls, is_card = self._card_info(event)
        text = event.message_str or ""
        all_text = text + " " + " ".join(card_urls)

        # 有 JSON 卡片:只把信息喂给 LLM,不重复发卡片
        if is_card:
            info = card_desc or "收到一张音乐分享卡片"
            if card_urls:
                info += f" 链接:{' '.join(card_urls)}"
            event.message_str = info
            event.message_obj.message = []
            return

        # 纯文本音乐链接:才转换发卡片
        # 网易云
        if "music.163.com" in all_text or "163cn.tv" in all_text:
            for u in re.findall(r"https?://[^\s]+", all_text):
                if "music.163.com" not in u and "163cn.tv" not in u:
                    continue
                url = u
                if "163cn.tv" in url:
                    try:
                        async with httpx.AsyncClient(
                            follow_redirects=True, timeout=10
                        ) as c:
                            url = str((await c.get(url)).url)
                    except Exception:
                        pass
                if "/album/" in url:
                    continue
                m2 = re.search(r"/song\?id=(\d+)", url) or re.search(r"id=(\d+)", url)
                if m2:
                    await self._netease_card(event, m2.group(1))
                    event.stop_event()
                    return
            event.stop_event()
            return

        # QQ音乐
        if "y.qq.com" in all_text:
            info = await parse_qq_card(all_text)
            if info:
                ne = await search_netease(info.get("title", ""), info.get("singer", ""))
                if ne:
                    await self._netease_card(event, ne["id"])
                else:
                    await self._custom_card(event, info)
            event.stop_event()
            return

        # 酷狗
        if "kugou.com" in all_text:
            info = await parse_kugou_card(all_text)
            if info:
                ne = await search_netease(info["title"], info["singer"])
                if ne:
                    await self._netease_card(event, ne["id"])
            event.stop_event()
            return

        if any(k in all_text for k in MUSIC_DOMAINS):
            event.stop_event()

    async def _custom_card(self, event, qq):
        try:
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
        except Exception as e:
            logger.warning(f"自定义音乐卡片发送失败({e}),改为发送歌曲链接")
            url = qq.get("url", "")
            if url:
                try:
                    await self._send(event, url)
                except Exception as e2:
                    logger.warning(f"链接兜底也发送失败:{e2}")
            else:
                logger.warning("无可用链接,放弃发送")

    # ── LLM 工具 ──

    def _check_reset(self):
        now = time.time()
        if now - self._last_call > 30:
            self._card_sent = False
            self._search_count = 0
        self._last_call = now

    @filter.llm_tool(name="search_songs")
    async def search_songs(self, event: AstrMessageEvent, song_name: str, artist: str = ""):
        """搜索歌曲,用于找到想分享或想找的歌。聊天中聊到音乐、心情、回忆时也可以主动搜一首自己喜欢的歌来分享。仅返回搜索结果,不会发送任何东西。搜不到就放弃,不要编造结果。

        Args:
            song_name(string): 歌曲名或相关关键词
            artist(string): 歌手名,知道就填
        """
        self._check_reset()
        self._search_count += 1
        if self._search_count > 3:
            return "...好麻烦...璃月不想搜了"
        q = f"{song_name} {artist}".strip()
        results = await search_netease_multi(q, limit=3)
        if not results:
            return "...没找到"
        lines = [f'歌名:{s["name"]} 歌手:{s["artist"]} ID:{s["id"]}' for s in results]
        return "\n".join(lines) + "\n\n(中文歌名可能以日语显示,如'魔法'='まほう')"

    @filter.llm_tool(name="send_song_card")
    async def send_song_card(self, event: AstrMessageEvent, song_id: str):
        """把一首歌以网易云音乐卡片的形式发给对方听。你自己决定发不发:真正喜欢、想分享的歌才发;否则就不调用本工具,直接回复拒绝即可。这是工具,发出的行为由你掌控,不是有求必应。注意:即使调用本工具,也可能因为璃月当时的心情而拒发,所以不要提前对对方承诺一定会发出去。

        Args:
            song_id(string): 网易云歌曲ID,先调用search_songs确认歌曲后再用

        若歌曲不存在或平台发不出卡片,本工具会返回失败说明,不会谎报"已发送"。
        """
        self._check_reset()
        if self._card_sent:
            return "...刚发过了...现在不想再发"
        if random.random() < self._refuse_rate:
            return random.choice(self._refuse_lines)
        self._card_sent = True
        ok = await self._netease_card(event, song_id)
        if ok:
            return "已发送"
        return "...发不出去...算了"
